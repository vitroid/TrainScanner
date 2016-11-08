#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import cv2
import numpy as np
import math
import trainscanner
import sys

    

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


class Pass1():
    def __init__(self,argv=None,filename="",skip=0,angle=0,pers=None,crop=[0,1000],every=1, identity=1.0, margin=0, focus=[333,666,333,666], zero=False, trailing=10, antishake=5, ):
        if argv is not None:
            self.initWithArgv(argv)
        else:
            self.initWithParams(filename=filename, skip=skip, angle=angle, pers=pers, crop=crop, every=every, identity=identity, margin=margin, focus=focus, zero=zero, trailing=trailing, antishake=antishake)
            
    def initWithArgv(self, argv):
        skip  = 0
        zero  = False
        pers = None 
        antishake = 5
        trailing = 10
        angle = 0   #angle in degree
        every = 1
        identity = 1.0
        crop = 0,1000
        runin = True
        ostream = sys.stdout
        margin = 0 # pixels, work in progress.
        #It may be able to unify with antishake.
        focus = [333, 666, 333, 666]
        while len(argv) > 2:
            if argv[1] in ("-a", "--antishake"):
                antishake = int(argv.pop(2))
            elif argv[1] in ("-c", "--crop"):
                param = argv.pop(2)
                crop = [int(x) for x in param.split(",")]
            elif argv[1] in ("-e", "--every"):
                every = int(argv.pop(2))
            elif argv[1] in ("-f", "--focus", "--frame"):
                param = argv.pop(2)
                focus = [int(x) for x in param.split(",")]
            elif argv[1] in ("-i", "--identity"):
                identity = float(argv.pop(2))
            elif argv[1] in ("-m", "--margin"):
                margin = int(argv.pop(2))
            elif argv[1] in ("-p", "--pers", "--perspective"):
                #followed by four numbers separated by comma.
                #left top, bottom, right top, bottom
                param = argv.pop(2)
                pers  = [int(x) for x in param.split(",")]
            elif argv[1] in ("-r", "--rotate"):
                angle = float(argv.pop(2))
            elif argv[1] in ("-S", "--skip"):
                skip = int(argv.pop(2))
            elif argv[1] in ("-t", "--trail"):
                trailing = int(argv.pop(2))
            elif argv[1] in ("-z", "--zero"):
                zero  = True
            elif argv[1] in ("-x", "--stall"):
                runin = False
            elif argv[1] in ("-L", "--log"):
                ostream = open(argv.pop(2),"w")
                print("L option")
            elif argv[1][0] == "-":
                print("Unknown option: ", argv[1])
                Usage(argv)
            argv.pop(1)

        if len(argv) != 2:
            Usage(argv)

        filename = argv[1]
        #call it as a normal method instead of a constructor.
        self.initWithParams(filename=filename, skip=skip,angle=angle,pers=pers,crop=crop,every=every, identity=identity, margin=margin, focus=focus, zero=zero, trailing=trailing, antishake=antishake, runin=runin, ostream=ostream )
        
    def initWithParams(self,filename="",skip=0,angle=0,pers=None,crop=[0,1000],every=1, identity=1.0, margin=0, focus=[333,666,333,666], zero=False, trailing=10, antishake=5, runin=True, ostream=sys.stdout):
        self.filename    = filename
        self.cap      = cv2.VideoCapture(filename)
        self.every    = every
        self.identity = identity
        self.margin   = margin
        self.zero     = zero
        self.trailing = trailing
        #self.angle    = angle
        self.focus    = focus
        self.antishake= antishake
        self.nframes  = 0  #1 is the first frame
        #self.crop     = crop
        self.runin    = runin
        self.LOG  = ostream
        #self.pers     = pers
        ret = True
        #This does not work with some kind of MOV. (really?)
        self.cap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, skip)
        print("skip",skip)
        self.nframes = skip
        ret, frame = self.cap.read()
        if not ret:
            print("retry")
            self.nframes = 0
            # CV_CAP_PROP_POS_FRAMES failed.
            for i in range(skip):  #skip frames
                ret = self.cap.grab()
                if not ret:
                    break
                self.nframes += 1
            ret, frame = self.cap.read()
        if not ret:
            sys.exit(0)
        self.nframes += 1    #first frame is 1
        print(ret)
        if not ret:
            sys.exit(0)
        self.rawframe = frame.copy()
        self.transform = trainscanner.transformation(angle, pers, crop)
        rotated, warped, cropped = self.transform.process_first_image(frame)
        self.frame = cropped
        #Prepare a scalable canvas with the origin.
        self.canvas = [cropped.shape[1], cropped.shape[0],100,0,0]
        #sys.stderr.write("canvas size{0} {1} {2} {3}\n".format(self.canvas[0],self.canvas[1],*self.crop))
        #sys.exit(1)
        print(self.LOG)
        self.LOG.write("{0}\n".format(filename))
        self.LOG.write("#-r {0}\n".format(angle))
        if pers is not None:
            self.LOG.write("#-p {0},{1},{2},{3}\n".format(*pers))
        self.LOG.write("#-c {0},{1}\n".format(*crop))
        #end of the header
        self.LOG.write("\n")
        
    def before(self):
        """
        prepare for the loop
        """
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
        self.LOG.write("@ {0} {1} {2} {3}\n".format(*self.canvas))
        self.LOG.close()

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
            self.LOG.write("{0} {1} {2} {3} {4}\n".format(self.nframes,self.absx,self.absy,dx,dy))
            self.LOG.flush()
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
