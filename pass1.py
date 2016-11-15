#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import cv2
import numpy as np
import math
import trainscanner
import sys
import re
    

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


def Usage(argv):
    print("usage: {0} [-a x][-d][-f xmin,xmax,ymin,ymax][-g n][-p tl,bl,tr,br][-q][-s r][-t x][-w x][-z] filename".format(argv[0]))
    print("\t-a x\tAntishake.  Ignore motion smaller than x pixels (5).")
    print("\t-f xmin,xmax,ymin,ymax\tMotion detection area relative to the image size. (0.333,0.666,0.333,0.666)")
    print("\t-p a,b,c,d\tSet perspective points. Note that perspective correction works for the vertically scrolling picture only.")
    print("\t-q\tDo not show the snapshots.")
    print("\t-s r\tSet slit position to r (1).")
    print("\t-S n\tSkip the nth frame (0).")
    print("\t-t x\tAdd trailing frames after the motion is not detected. (5).")
    print("\t-w r\tSet slit width (1=same as the length of the interframe motion vector).")
    print("\t-z\tSuppress drift.")
    sys.exit(1)


def options_parser(argv, options):
    #assume the first arg is removed
    while len(argv) > 0 and argv[0][0] =="-":
        arg1 = argv.pop(0)
        if arg1 in ("-a", "--antishake"):
            options["antishake"] = int(argv.pop(0))
        elif arg1 in ("-c", "--crop"):
            param = argv.pop(0)
            options["crop"] = [int(x) for x in param.split(",")]
        elif arg1 in ("-e", "--every"):
            options["every"] = int(argv.pop(0))
        elif arg1 in ("-f", "--focus", "--frame"):
            param = argv.pop(0)
            options["focus"] = [int(x) for x in param.split(",")]
        elif arg1 in ("-i", "--identity"):
            options["identity"] = float(argv.pop(0))
        elif arg1 in ("-m", "--margin"):
            options["margin"] = int(argv.pop(0))
        elif arg1 in ("-p", "--pers", "--perspective"):
            #followed by four numbers separated by comma.
            #left top, bottom, right top, bottom
            param = argv.pop(0)
            options["pers"]  = [int(x) for x in param.split(",")]
        elif arg1 in ("-r", "--rotate"):
            options["angle"] = float(argv.pop(0))
        elif arg1 in ("-S", "--skip"):
            options["skip"] = int(argv.pop(0))
        elif arg1 in ("-t", "--trail"):
            options["trailing"] = int(argv.pop(0))
        elif arg1 in ("-z", "--zero"):
            options["zero"]  = True
        elif arg1 in ("-x", "--stall"):
            options["runin"] = False
        elif arg1 in ("-L", "--log"):
            options["ostream"] = open(argv.pop(0),"w")
        elif arg1 in ("-2",):
            #Options for the second pass == stitch
            options["option2"].append(argv.pop(0))
        elif arg1[0] == "-":
            print("Unknown option: ", arg1)
            Usage(argv)

class Pass1():
    def __init__(self,argv=None,filename="",skip=0,angle=0,pers=None,crop=[0,1000],every=1, identity=1.0, margin=0, focus=[333,666,333,666], zero=False, trailing=10, antishake=5, ):
        if argv is not None:
            self.initWithArgv(argv)
        else:
            self.initWithParams(filename=filename, skip=skip, angle=angle, pers=pers, crop=crop, every=every, identity=identity, margin=margin, focus=focus, zero=zero, trailing=trailing, antishake=antishake)
            
    def initWithArgv(self, argv):
        options = dict()
        options["skip"]  = 0
        options["zero"]  = False
        options["pers"] = None 
        options["antishake"] = 5
        options["trailing"] = 10
        options["angle"] = 0   #angle in degree
        options["every"] = 1
        options["identity"] = 1.0
        options["crop"] = 0,1000
        options["runin"] = True
        options["ostream"] = sys.stdout
        options["option2"] = []
        options["margin"] = 0 # pixels, work in progress.
        #It may be able to unify with antishake.
        options["focus"] = [333, 666, 333, 666]

        #last arg
        options["filename"] = argv.pop(-1)
        options_parser(argv[1:], options)
        
        #call it as a normal method instead of a constructor.
        self.initWithParams(**options)
        
    def initWithParams(self,filename="",skip=0,angle=0,pers=None,crop=[0,1000],every=1, identity=1.0, margin=0, focus=[333,666,333,666], zero=False, trailing=10, antishake=5, runin=True, ostream=sys.stdout, option2=[] ):
        self.filename    = filename
        self.cap      = cv2.VideoCapture(filename)
        self.skip = skip
        self.angle    = angle
        self.pers     = pers
        self.crop     = crop
        self.every    = every
        self.identity = identity
        self.margin   = margin
        self.focus    = focus
        self.zero     = zero
        self.trailing = trailing
        self.antishake= antishake
        #self.crop     = crop
        self.runin    = runin
        self.head     = []
        self.body     = []
        self.ostream   = ostream
        self.option2  = option2
        
    def before(self):
        """
        prepare for the loop
        """
        self.nframes  = 0  #1 is the first frame

        ret = True
        #This does not work with some kind of MOV. (really?)
        #self.cap.set(cv2.CAP_PROP_POS_FRAMES, skip)
        #self.nframes = skip
        #ret, frame = self.cap.read()
        #if not ret:
        self.nframes = 0
        #print("skip:",skip)
        for i in range(self.skip):  #skip frames
            ret = self.cap.grab()
            if not ret:
                break
            self.nframes += 1
        #print("get:",self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        ret, frame = self.cap.read()
        if not ret:
            sys.exit(0)
        self.nframes += 1    #first frame is 1
        if not ret:
            sys.exit(0)
        self.rawframe = frame.copy()
        self.transform = trainscanner.transformation(angle=self.angle, pers=self.pers, crop=self.crop)
        rotated, warped, cropped = self.transform.process_first_image(frame)
        self.frame = cropped
        #Prepare a scalable canvas with the origin.
        self.canvas = None
        #sys.stderr.write("canvas size{0} {1} {2} {3}\n".format(self.canvas[0],self.canvas[1],*self.crop))
        #sys.exit(1)
        self.head.append("{0}\n".format(self.filename))
        self.head.append("--rotate\t{0}\n".format(self.angle))
        if self.pers is not None:
            self.head.append("--perspective\t{0},{1},{2},{3}\n".format(*self.pers))
        self.head.append("--crop\t{0},{1}\n".format(*self.crop))
        for op in self.option2:
            self.head.append(re.sub(r"%09","\t",op)+"\n")
        #end of the header
        
        self.absx,self.absy = 0, 0
        self.velx, self.vely = 0.0, 0.0
        self.tr = 0
        if self.runin:
            #we cannot predict the run-in velocity
            #so the prediction is off by default.
            self.predict = False
        else:
            #runin=False means the train is stalling.
            #prediction must be on by default.
            self.predict = True
            self.tr = 1
        self.precount = 0
        self.preview_size = 500
        self.preview = trainscanner.fit_to_square(self.frame, self.preview_size)
        self.preview_ratio = float(self.preview.shape[0]) / self.frame.shape[0]


    def after(self):
        self.head.append("--canvas\t{0},{1},{2},{3}\n".format(*self.canvas))
        self.head.append("\n")
        for line in self.head+self.body:
            self.ostream.write(line)
        self.ostream.close()

    def onestep(self):
        ret = True
        ##### Pick up every x frame
        for i in range(self.every-1):
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
        if diff < self.identity:
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
        #if margin is set, motion detection area becomes very narrow
        #assuming that the train is running at constant speed.
        #This mode is activated after the 10th frames.

        #Now I do care only magrin case.
        if self.margin > 0 and self.predict:
            #do not apply margin for the first 10 frames
            #because the velocity uncertainty.
            delta = trainscanner.motion(self.frame, nextframe, focus=self.focus, margin=int(self.margin*self.tr), delta=(int(self.velx*self.tr),int(self.vely*self.tr)) )
            if delta is None:
                return None
            dx,dy = delta
        else:
            dx,dy = trainscanner.motion(self.frame, nextframe, focus=self.focus)
            
        ##### Suppress drifting.
        if self.zero:
            if abs(dx) < abs(dy):
                dx = 0
            else:
                dy = 0
        diff_img = diffImage(nextpreview,self.preview,int(dx*self.preview_ratio),int(dy*self.preview_ratio),focus=self.focus)
        ##### if the motion is very small
        if self.predict and (abs(dx) < self.antishake and abs(dy) < self.antishake):
            ##### accumulate the motion
            ##### wait until motion becomes enough.
            if self.tr <= self.trailing:
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
        elif (abs(dx) >= self.antishake or abs(dy) >= self.antishake):
            self.precount += 1
            if self.precount == 5:
                self.predict = True
                self.velx = dx
                self.vely = dy
            
        self.tr = 1
        sys.stderr.write(" {0} {1} {2} {4} {5} #{3}\n".format(self.nframes,dx,dy,np.amax(diff), self.velx, self.vely))
        if (abs(dx) >= self.antishake or abs(dy) >= self.antishake):
            self.absx += dx
            self.absy += dy
            self.canvas = canvas_size(self.canvas, nextframe, self.absx, self.absy)
            self.body.append("{0} {1} {2} {3} {4}\n".format(self.nframes,self.absx,self.absy,dx,dy))
        self.frame   = nextframe
        self.preview = nextpreview
        return diff_img


if __name__ == "__main__":
    pass1 = Pass1(argv=sys.argv)
    pass1.before()
    while True:
        ret = pass1.onestep()
        if ret is None:
            break
        if ret is not True: #True means skipping
            cv2.imshow("pass1", ret)
            cv2.waitKey(1)
            
    pass1.after()
