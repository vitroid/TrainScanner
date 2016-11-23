#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import cv2
import numpy as np
import math
import trainscanner
import sys
import re
import argparse
import itertools

def diffImage(frame1,frame2,dx,dy,focus=None,slitpos=None):
    affine = np.matrix(((1.0,0.0,dx),(0.0,1.0,dy)))
    h,w = frame1.shape[0:2]
    frame1 = cv2.warpAffine(frame1, affine, (w,h))
    diff = 255 - cv2.absdiff(frame1,frame2)
    if focus is not None:
        trainscanner.draw_focus_area(diff, focus, delta=dx)
    if slitpos is not None:
        trainscanner.draw_slit_position(diff, slitpos, dx)
    return diff


#Automatically extensible canvas.
def canvas_size(canvas_dimen, image, x, y):
    if canvas_dimen is None:
        h,w = image.shape[:2]
        return w,h,x,y
    absx, absy = canvas_dimen[2:4]   #absolute coordinate of the top left of the canvas
    cxmin = absx
    cymin = absy
    cxmax = canvas_dimen[0]+ absx
    cymax = canvas_dimen[1]+ absy
    ixmin = x
    iymin = y
    ixmax = image.shape[1] + x
    iymax = image.shape[0] + y

    xmin = min(cxmin,ixmin)
    xmax = max(cxmax,ixmax)
    ymin = min(cymin,iymin)
    ymax = max(cymax,iymax)
    if (xmax-xmin, ymax-ymin) != (canvas_dimen[0], canvas_dimen[1]):
        canvas_dimen = [xmax-xmin,ymax-ymin,xmin,ymin]
    return canvas_dimen



def prepare_parser():
    parser = argparse.ArgumentParser(description='TrainScanner matcher', fromfile_prefix_chars='@',)
    parser.add_argument('-z', '--zero', action='store_true',
                        dest='zero',
                        help="Suppress drift.")
    parser.add_argument('-S', '--skip', type=int, metavar='N',
                        default=0,
                        dest="skip",
                        help="Skip first N frames.")
    parser.add_argument('-p', '--pers', '--perspective',
                        type=int,
                        nargs=4, default=None,
                        dest="pers",
                        help="Specity perspective warp.")
    parser.add_argument('-f', '--focus', type=int,
                        nargs=4, default=[333,666,333,666],
                        dest="focus", 
                        help="Motion detection area relative to the image size.")
    parser.add_argument('-a', '--antishake', type=int,
                        default=5, metavar="x",
                        dest="antishake",
                        help="Antishake.  Ignore motion smaller than x pixels.")
    parser.add_argument('-t', '--trail', type=int,
                        default=10,
                        dest="trailing",
                        help="Trailing frames after the train runs away.")
    parser.add_argument('-r', '--rotate', type=int,
                        default=0,
                        dest="angle",
                        help="Image rotation.")
    parser.add_argument('-e', '--every', type=int,
                        default=1,
                        dest="every", metavar="N",
                        help="Load every N frames.")
    parser.add_argument('-i', '--identity', type=float,
                        default=1.0,
                        dest="identity", metavar="x",
                        help="Decide the identity of two successive frames with the threshold.")
    parser.add_argument('-c', '--crop', type=int,
                        nargs=2, default=[0,1000],
                        dest="crop", metavar="t,b",
                        help="Crop the image (top and bottom).")
    parser.add_argument('-x', '--stall', action='store_true',
                        dest="stall", default=False,
                        help="Train is initially stopping inside the motion detection area.")
    parser.add_argument('-m', '--maxaccel', type=int,
                        default=1,
                        dest="maxaccel", metavar="N",
                        help="Interframe acceleration in pixels.")
    parser.add_argument('-2', '--option2', type=str,
                        action='append',
                        dest="option2",
                        help="Additional option (just ignored in this program).")
    parser.add_argument('-l', '--log', type=str,
                        dest='log', default=None,
                        help="TrainScanner settings (.tsconf) file name.")
    parser.add_argument('filename', type=str,
                        help="Movie file name.")
    return parser


                
            
class Pass1():
        
    def __init__(self,argv):
        self.parser = prepare_parser()
        self.params, unknown = self.parser.parse_known_args(argv[1:])
        print(vars(self.params))
        
    def before(self):
        """
        prepare for the loop
        note that it is a generator.
        """
        ####prepare tsconf file#############################
        self.head   = ""
        args = trainscanner.deparse(self.parser,self.params)
        self.head += "{0}\n".format(args["__UNNAMED__"])
        for option in args:
            value = args[option]
            if value is None or option in ("__UNNAMED__"):
                continue
            if option == '--option2':
                #Expand "key=value" to "--key\tvalue\n"
                for v in value:
                    equal = v.find("=")
                    if equal >= 0:
                        self.head += "--{0}\n{1}\n".format(v[:equal],v[equal+1:])
                    else:
                        self.head += "--{0}\n".format(v)
            else:
                if option in ("--perspective", "--focus", "--crop", ):  #multiple values
                    self.head += "{0}\n".format(option)
                    for v in value:
                        self.head += "{0}\n".format(v)
                elif option in ("--zero", "--stall", "--helix", "--film"):
                    if value is True:
                        self.head += option+"\n"
                else:
                    self.head += "{0}\n{1}\n".format(option,value)
        #print(self.head)
        #end of the header

        #############Open the video file #############################
        self.cap    = cv2.VideoCapture(self.params.filename)
        self.body   = ""

        self.nframes  = 0  #1 is the first frame

        #This does not work with some kind of MOV. (really?)
        #self.cap.set(cv2.CAP_PROP_POS_FRAMES, skip)
        #self.nframes = skip
        #ret, frame = self.cap.read()
        #if not ret:
        self.nframes = 0
        #print("skip:",skip)
    
        for i in range(self.params.skip):  #skip frames
            ret = self.cap.grab()
            if not ret:
                break
            self.nframes += 1
            yield self.nframes, self.params.skip #report progress
        ret, frame = self.cap.read()
        if not ret:
            sys.exit(0)
        self.nframes += 1    #first frame is 1
        self.rawframe = frame
        
        self.transform = trainscanner.transformation(angle=self.params.angle, pers=self.params.pers, crop=self.params.crop)
        rotated, warped, cropped = self.transform.process_first_image(self.rawframe)
        self.frame = cropped
        #Prepare a scalable canvas with the origin.
        self.canvas = None
        
        self.absx,self.absy = 0, 0
        self.velx, self.vely = 0.0, 0.0
        self.tr = 0
        if self.params.stall:
            #prediction must be on by default.
            self.predict = True
            self.tr = 1
        else:
            #we cannot predict the run-in velocity
            #so the prediction is off by default.
            self.predict = False
        self.precount = 0
        self.preview_size = 500
        self.preview = trainscanner.fit_to_square(self.frame, self.preview_size)
        self.preview_ratio = float(self.preview.shape[0]) / self.frame.shape[0]
        yield self.nframes, self.params.skip

        
    def after(self):
        self.head += "--canvas\n{0}\n{1}\n{2}\n{3}\n".format(*self.canvas)
        if self.params.log is None:
            ostream = sys.stdout
        else:
            ostream = open(self.params.log+".tsconf", "w")
        ostream.write(self.head)
        if self.params.log is not None:
            ostream = open(self.params.log+".tspos", "w")
        ostream.write(self.body)
        ostream.close()

    def onestep(self):
        ret = True
        ##### Pick up every x frame
        for i in range(self.params.every-1):
            ret = self.cap.grab()
            self.nframes += 1
            if not ret:
                return None
        ret, nextframe = self.cap.read()
        self.nframes += 1
        ##### return None if the frame is empty
        if not ret:
            return None
        ##### compare with the previous raw frame
        diff = cv2.absdiff(nextframe,self.rawframe)
        ##### preserve the raw frame for next comparison.
        self.rawframe = nextframe.copy()
        diff = np.sum(diff) / np.product(diff.shape)
        if diff < self.params.identity:
            sys.stderr.write("skip identical frame #{0}\n".format(diff))
            #They are identical frames
            #This happens when the frame rate difference is compensated.
            return True
        ##### Warping the frame
        rotated, warped, cropped = self.transform.process_next_image(nextframe)
        nextframe = cropped
        ##### Make the preview image
        nextpreview = trainscanner.fit_to_square(nextframe,self.preview_size)
        ##### motion detection.
        #if maxaccel is set, motion detection area becomes very narrow
        #assuming that the train is running at constant speed.
        #This mode is activated after the 10th frames.

        #Now I do care only magrin case.
        if self.params.maxaccel > 0 and self.predict:
            #do not apply maxaccel for the first 10 frames
            #because the velocity uncertainty.
            delta = trainscanner.motion(self.frame, nextframe, focus=self.params.focus, maxaccel=int(self.params.maxaccel*self.tr), delta=(int(self.velx*self.tr),int(self.vely*self.tr)) )
            if delta is None:
                return None
            dx,dy = delta
        else:
            dx,dy = trainscanner.motion(self.frame, nextframe, focus=self.params.focus)
            
        ##### Suppress drifting.
        if self.params.zero:
            if abs(dx) < abs(dy):
                dx = 0
            else:
                dy = 0
        diff_img = diffImage(nextpreview,self.preview,int(dx*self.preview_ratio),int(dy*self.preview_ratio),focus=self.params.focus)
        ##### if the motion is very small
        if self.predict and (abs(dx) < self.params.antishake and abs(dy) < self.params.antishake):
            ##### accumulate the motion
            ##### wait until motion becomes enough.
            if self.tr <= self.params.trailing:
                self.tr += 1
                sys.stderr.write("({0} {1} {2})\n".format(self.nframes,dx,dy))
                ####Do not update the original frame and preview.
                ####That is, accumulate the changes.
                ####tr is the number of accumulation.
                return diff_img
            else:
                #end of work
                return None
        if self.predict:
            self.velx = dx / self.tr
            self.vely = dy / self.tr
        elif (abs(dx) >= self.params.antishake or abs(dy) >= self.params.antishake):
            self.precount += 1
            if self.precount == 5:
                self.predict = True
                self.velx = dx
                self.vely = dy
            
        self.tr = 1
        sys.stderr.write(" {0} {1} {2} {4} {5} #{3}\n".format(self.nframes,dx,dy,np.amax(diff), self.velx, self.vely))
        if (abs(dx) >= self.params.antishake or abs(dy) >= self.params.antishake):
            self.absx += dx
            self.absy += dy
            self.canvas = canvas_size(self.canvas, nextframe, self.absx, self.absy)
            self.body += "{0} {3} {4}\n".format(self.nframes,self.absx,self.absy,dx,dy)
        self.frame   = nextframe
        self.preview = nextpreview
        return diff_img


if __name__ == "__main__":
    pass1 = Pass1(argv=sys.argv)
    for num, den in pass1.before():
        pass
    while True:
        ret = pass1.onestep()
        if ret is None:
            break
        if ret is not True: #True means skipping
            cv2.imshow("pass1", ret)
            cv2.waitKey(1)
            
    pass1.after()
