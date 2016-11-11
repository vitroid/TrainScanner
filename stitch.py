#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import cv2
import numpy as np
import math
import trainscanner
import sys


#Automatically extensible canvas.
class Canvas():
    def __init__(self,initial_canvas, origin=(0,0)):
        #self.canvases = []
        self.canvas = (initial_canvas, origin)
    def abs_merge(self, image, x, y, alpha=None ):
        absx, absy = self.canvas[1]   #absolute coordinate of the top left of the canvas
        cxmin = absx
        cymin = absy
        cxmax = self.canvas[0].shape[1] + absx
        cymax = self.canvas[0].shape[0] + absy
        ixmin = x
        iymin = y
        ixmax = image.shape[1] + x
        iymax = image.shape[0] + y

        xmin = min(cxmin,ixmin)
        xmax = max(cxmax,ixmax)
        ymin = min(cymin,iymin)
        ymax = max(cymax,iymax)
        if (xmax-xmin, ymax-ymin) != (self.canvas[0].shape[1], self.canvas[0].shape[0]):
            newcanvas = np.zeros((ymax-ymin, xmax-xmin,3), np.uint8)
            newcanvas[cymin-ymin:cymax-ymin, cxmin-xmin:cxmax-xmin, :] = self.canvas[0][:,:,:]
        else:
            newcanvas = self.canvas[0]
        if alpha is None:
            newcanvas[iymin-ymin:iymax-ymin,ixmin-xmin:ixmax-xmin,:] = image[:,:,:]
        else:
            newcanvas[iymin-ymin:iymax-ymin,ixmin-xmin:ixmax-xmin,:] = image[:,:,:]*alpha[:,:,:] + newcanvas[iymin-ymin:iymax-ymin,ixmin-xmin:ixmax-xmin,:]*(1-alpha[:,:,:])
        self.canvas = (newcanvas, (xmin,ymin))
        

def Usage(argv):
    print("usage: {0} [-d][-s r][-w x][-F][-H][-l label][-C w,h,x,y] < output_of_pass1_py.log".format(argv[0]))
    print("usage: {0} [-d][-s r][-w x][-F][-H][-l label][-C w,h,x,y] output_of_pass1_py.log".format(argv[0]))
    print("\t-d\tDebug mode.")
    print("\t-s r\tSet slit position to r (1).")
    print("\t-w r\tSet slit width (1=same as the length of the interframe motion vector).")
    sys.exit(1)



class Stitcher(Canvas):
    """
    exclude video handling
    """
    def __init__(self, argv=None, filename="", istream=None, angle=0, pers=None, slitpos=250, slitwidth=1.0, visual=False, scale=1.0, crop=(0,1000), dimen=None):
        if argv is None:
            self.initWithParams(filename=filename, istream=istream, angle=angle, pers=pers, slitpos=slitpos, slitwidth=slitwidth, visual=visual, scale=scale, crop=crop, dimen=dimen)
        else:
            self.initWithArgv(argv)

    def initWithArgv(self,argv):

        debug = False #True
        slitpos = 250
        slitwidth = 1
        film = False
        helix = False
        dimen = (10,10,0,0)
        scale = 1.0
        # -r and -p option must be identical to pass1.py
        #(or they may be given in the input file)
        while len(argv) > 1 and argv[1][0] =="-":
            if argv[1] in ("-d", "--debug"):
                debug = True
            elif argv[1] in ("-C", "--canvas"):
                dimen = [int(x) for x in argv.pop(2).split(",")]
            elif argv[1] in ("-s", "--slit"):
                slitpos = int(argv.pop(2))
            elif argv[1] in ("-y", "--scale"):
                scale = float(argv.pop(2))
            elif argv[1] in ("-w", "--width"):
                slitwidth = float(argv.pop(2))
            elif argv[1][0] == "-":
                print("Unknown option: ", argv[1])
                Usage(argv)
            argv.pop(1)
        if len(argv) == 2:
            LOG = open(argv[1])
        elif len(argv) != 1:
            Usage(argv)
        else:
            LOG = sys.stdin
        line = LOG.readline()
        filename = line.splitlines()[0] #chomp
        angle = 0
        pers = None #np.float32([380, 350, 1680, 1715])
        crop = 0,1000
        while True:
            line = LOG.readline()
            if line[0:3] == "#-r":
                angle = float(line.split()[1])
            elif line[0:3] == "#-p":
                pers  = [int(x) for x in line.split()[1].split(",")]
            elif line[0:3] == "#-c":
                crop  = [int(x) for x in line.split()[1].split(",")]
            else:
                break
        self.initWithParams(filename=filename, istream=LOG, angle=angle, pers=pers, slitpos=slitpos, slitwidth=slitwidth, scale=scale, crop=crop, dimen=dimen)

    def initWithParams(self, filename="", istream=None, angle=0, pers=None, slitpos=250, slitwidth=1.0, visual=False, scale=1.0, crop=(0,1000), dimen=(10,10,0,0)):
        self.filename = filename

        self.slitpos = slitpos
        self.slitwidth = slitwidth
        self.visual = visual
        self.R = None
        self.M = None
        self.scale = scale
        #print("scale=",scale)
        self.transform = trainscanner.transformation(angle, pers, crop)
        self.dimen = [int(x*scale) for x in dimen]
        Canvas.__init__(self,np.zeros((self.dimen[1],self.dimen[0],3),np.uint8), self.dimen[2:4]) #python2 style
        locations = [] #(1,0,0,0,0)] #frame,absx, absy,dx,dy
        for line in istream.readlines():
            if len(line) > 0 and line[0] != '@':
                cols = [int(x) for x in line.split()]
                if len(cols) > 0:
                    cols[1:] = [int(x*self.scale) for x in cols[1:]]
                    locations.append(cols)
        self.locations = locations
        self.total_frames = len(locations)
        self.outfilename = filename+"+{0}.png".format(self.locations[0][0])

    def getProgress(self):
        den = self.total_frames
        num = den - len(self.locations)
        return (num, den)
    
    def add_image(self, frame, absx,absy,idx,idy):
        rotated,warped,cropped = self.transform.process_image(frame)
        alpha = trainscanner.make_vert_alpha( int(idx), cropped.shape[1], cropped.shape[0], self.slitpos, self.slitwidth )
        #cv2.imshow("", alpha)
        self.abs_merge(cropped, absx, absy, alpha=alpha)
        if self.visual:
            cv2.imshow("canvas", self.canvas[0])
            cv2.waitKey(1)  #This causes ERROR


    def stitch(self):
        self.before()
        result = None
        while result is None:
            result = self.onestep()
        self.after()
                


    def before(self):
        self.cap = cv2.VideoCapture(self.filename)

    def onestep(self):
        nextframe = self.locations[0][0]  #in locations, 1 is the first frame.
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, nextframe)
        ## while self.frames + 1 < nextframe:
        ##     ret = self.cap.grab()
        ##     if not ret:
        ##         return self.canvas[0]
        ##     self.frames += 1
        ret,frame = self.cap.read()
        if not ret:
            return self.canvas[0]
        frame = cv2.resize(frame, None, fx=self.scale, fy=self.scale)
        self.add_image(frame, *self.locations[0][1:])
        self.locations.pop(0)
        if len(self.locations) == 0:
            return self.canvas[0]
        return None  #not end

    def after(self):
        cv2.imwrite(self.outfilename, self.canvas[0])
        

if __name__ == "__main__":
    st = Stitcher(argv=sys.argv)
    st.stitch()
