#!/usr/bin/env python
# -*- coding: utf-8 -*-


import cv2
import numpy as np
import math
import trainscanner



#Automatically extensible canvas.
class Canvas():
    def __init__(self,initial_canvas):
        #self.canvases = []
        self.canvas = (initial_canvas, (0,0))
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
    print "usage: {0} [-d][-s r][-w x][-F][-H][-l label] < output_of_pass1_py.log".format(argv[0])
    print "\t-d\tDebug mode."
    print "\t-s r\tSet slit position to r (1)."
    print "\t-w r\tSet slit width (1=same as the length of the interframe motion vector)."
    sys.exit(1)



class Stitcher(Canvas):
    """
    exclude video handling
    """
    def __init__(self, angle=0, pers=None, slitpos=250, slitwidth=1.0, visual=True, scale=0.4):
        self.angle = angle
        self.pers  = pers
        self.slitpos = slitpos
        self.slitwidth = slitwidth
        self.visual = visual
        self.R = None
        self.M = None
        self.ratio = scale
        Canvas.__init__(self,np.zeros((10,10,3),np.uint8)) #python2 style
    def add_image(self, frame, absx,absy,idx,idy):
        imgh, imgw = frame.shape[0:2]
        #self.h, self.w = imgh,imgw  #transformed size
        if self.R is None:
            #Apply rotation
            self.R, self.w, self.h = trainscanner.rotate_matrix(angle, imgw,imgh)
            print self.w,self.h,"*"
            self.R *= self.ratio
            self.w *= self.ratio
            self.h *= self.ratio
            self.w = int(self.w)
            self.h = int(self.h)
        if self.M is None and self.pers is not None:
            self.M = trainscanner.warp_matrix(self.pers, self.w, self.h)

        #rotate andd scale
        frame = cv2.warpAffine(frame, self.R, (self.w,self.h))
        if self.M is not None:
            frame = cv2.warpPerspective(frame,self.M,(self.w,self.h))
        alpha = trainscanner.make_vert_alpha( int(idx*self.ratio), self.w, self.h, self.slitpos, self.slitwidth )
        cv2.imshow("", alpha)
        self.abs_merge(frame, int(absx*self.ratio), int(absy*self.ratio), alpha=alpha)
        if self.visual:
            cv2.imshow("canvas", self.canvas[0])
            cv2.waitKey(1)


def stitch(movie, istream, angle=0, pers=None, slitpos=250, slitwidth=1.0, visual=True, scale=1.0):
    st = Stitcher(angle, pers, slitpos, slitwidth, visual, scale)

    line = istream.readline()
    frame0, absx,absy,idx,idy = 1,0,0,0,0
    cap = cv2.VideoCapture(movie)
    frames = 0  #1 is the first frame
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames += 1
        if frames == frame0:
            st.add_image(frame, absx,absy, idx, idy)
            line = istream.readline()
            if len(line) == 0:
                break
            frame0, absx,absy,idx,idy = [int(x) for x in line.split()]
    return st.canvas[0]



if __name__ == "__main__":
    import sys

    debug = False #True
    slitpos = 250
    slitwidth = 1
    film = False
    helix = False
    label= ""
    # -r and -p option must be identical to pass1.py
    #(or they may be given in the input file)
    while len(sys.argv) > 1:
        if sys.argv[1] in ("-d", "--debug"):
            debug = True
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
            print "Unknown option: ", sys.argv[1]
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
    while True:
        line = LOG.readline()
        if line[0:3] == "#-r":
            angle = -float(line.split()[1]) * math.pi / 180
        elif line[0:3] == "#-p":
            gpts  = [int(x) for x in line.split()[1].split(",")]
        else:
            break
    canvas = stitch(movie, LOG, angle=angle, pers=gpts, slitpos=slitpos, slitwidth=slitwidth, scale=0.5)
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
