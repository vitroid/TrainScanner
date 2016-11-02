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
            print("Resize canvas to ",xmax-xmin, ymax-ymin)
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
    print("\t-d\tDebug mode.")
    print("\t-s r\tSet slit position to r (1).")
    print("\t-w r\tSet slit width (1=same as the length of the interframe motion vector).")
    sys.exit(1)



class Stitcher(Canvas):
    """
    exclude video handling
    """
    def __init__(self, angle=0, pers=None, slitpos=250, slitwidth=1.0, visual=False, scale=1.0, crop=(0,1000), dimen=None):
        self.angle = angle
        self.pers  = pers
        self.slitpos = slitpos
        self.slitwidth = slitwidth
        self.visual = visual
        self.R = None
        self.M = None
        self.ratio = scale
        self.crop  = crop
        if dimen is None:
            dimen = (10,10,0,0)
        Canvas.__init__(self,np.zeros((dimen[1],dimen[0],3),np.uint8), dimen[2:4]) #python2 style
    def add_image(self, frame, absx,absy,idx,idy):
        imgh, imgw = frame.shape[0:2]
        #self.h, self.w = imgh,imgw  #transformed size
        if self.R is None:
            #Apply rotation
            self.R, self.rotated_w, self.rotated_h = trainscanner.rotate_matrix(self.angle, imgw,imgh)
            #print(self.w,self.h,"*"
            self.R *= self.ratio
            self.rotated_w *= self.ratio
            self.rotated_h *= self.ratio
            self.rotated_w = int(self.rotated_w)
            self.rotated_h = int(self.rotated_h)
        if self.M is None and self.pers is not None:
            self.M = trainscanner.warp_matrix(self.pers, self.rotated_w, self.rotated_h)

        #rotate andd scale
        frame = cv2.warpAffine(frame, self.R, (self.rotated_w,self.rotated_h))
        if self.M is not None:
            frame = cv2.warpPerspective(frame,self.M,(self.rotated_w,self.rotated_h))
        frame = frame[self.crop[0]*self.rotated_h/1000:self.crop[1]*self.rotated_h/1000, :, :]
        cropped_h,cropped_w = frame.shape[0:2]
        
        alpha = trainscanner.make_vert_alpha( int(idx*self.ratio), cropped_w, cropped_h, self.slitpos, self.slitwidth )
        #cv2.imshow("", alpha)
        self.abs_merge(frame, int(absx*self.ratio), int(absy*self.ratio), alpha=alpha)
        if self.visual:
            cv2.imshow("canvas", self.canvas[0])
            cv2.waitKey(1)  #This causes ERROR


    def stitch(self, movie, istream):
        self.before(movie, istream)
        while True:
            result = self.onestep()
            if result is not None:
                return result


    def before(self, movie, istream):
        self.movie = movie
        self.istream = istream
        line = self.istream.readline()
        self.frame0, self.absx, self.absy, self.idx, self.idy = 1,0,0,0,0
        self.cap = cv2.VideoCapture(movie)
        self.frames = 0  #1 is the first frame

    def onestep(self):
        ret, frame = self.cap.read()
        if not ret:
            return self.canvas[0]
        self.frames += 1
        if self.frames == self.frame0:
            self.add_image(frame, self.absx, self.absy, self.idx, self.idy) #ugly
            line = self.istream.readline()
            if len(line) == 0 or line[0] == "@":
                return self.canvas[0]
            self.frame0, self.absx,self.absy,self.idx,self.idy = [int(x) for x in line.split()]
        return None  #not end



if __name__ == "__main__":
    import sys

    debug = False #True
    slitpos = 250
    slitwidth = 1
    film = False
    helix = False
    label= ""
    dimen = None
    # -r and -p option must be identical to pass1.py
    #(or they may be given in the input file)
    while len(sys.argv) > 1:
        if sys.argv[1] in ("-d", "--debug"):
            debug = True
        elif sys.argv[1] in ("-C", "--canvas"):
            dimen = [int(x) for x in sys.argv.pop(2).split(",")]
        elif sys.argv[1] in ("-s", "--slit"):
            slitpos = int(sys.argv.pop(2))
        elif sys.argv[1] in ("-w", "--width"):
            slitwidth = float(sys.argv.pop(2))
        elif sys.argv[1] in ("-l", "--label"):
            label = sys.argv.pop(2)
        elif sys.argv[1] in ("-F", "--film"):
            film = True
        elif sys.argv[1] in ("-H", "--helix"):
            helix = True
        elif sys.argv[1][0] == "-":
            print("Unknown option: ", sys.argv[1])
            Usage(sys.argv)
        sys.argv.pop(1)

    #if len(sys.argv) != 2:
    if len(sys.argv) != 1:
        Usage(sys.argv)
    #movie = sys.argv[1]
    #LOG = open("{0}.pass1.log".format(movie))
    LOG = sys.stdin
    line = LOG.readline()
    movie = line.splitlines()[0] #chomp
    angle = 0
    gpts = None #np.float32([380, 350, 1680, 1715])
    crop = 0,1000
    while True:
        line = LOG.readline()
        if line[0:3] == "#-r":
            angle = -float(line.split()[1]) * math.pi / 180
        elif line[0:3] == "#-p":
            gpts  = [int(x) for x in line.split()[1].split(",")]
        elif line[0:3] == "#-c":
            crop  = [int(x) for x in line.split()[1].split(",")]
        else:
            break
    st = Stitcher(angle=angle, pers=gpts, slitpos=slitpos, slitwidth=slitwidth, scale=1, crop=crop, dimen=dimen)
    canvas = st.stitch(movie, LOG)
    cv2.imwrite("{0}.png".format(movie), canvas)
    if film:
        import film
        canvas = film.filmify(canvas, label=label)
        movie += ".film"
        cv2.imwrite("{0}.jpg".format(movie), canvas)
    if helix:
        import helix
        canvas = helix.helicify(canvas)
        movie += ".helix"
        cv2.imwrite("{0}.jpg".format(movie), canvas)
