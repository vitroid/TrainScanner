#!/usr/bin/env python
# -*- coding: utf-8 -*-


import cv2
import numpy as np
import math
import trainscanner



canvases = []

#Automatically extensible canvas.
def abs_merge(canvas, image, x, y, alpha=None ):
    absx, absy = canvas[1]   #absolute coordinate of the top left of the canvas
    if debug:
        print canvas
        print image
        print "canvas:  {0}x{1} {2:+d}{3:+d}".format(canvas[0].shape[1],canvas[0].shape[0],absx,absy)
        print "overlay: {0}x{1} {2:+d}{3:+d}".format(image.shape[1], image.shape[0],x,y)
    cxmin = absx
    cymin = absy
    cxmax = canvas[0].shape[1] + absx
    cymax = canvas[0].shape[0] + absy
    ixmin = x
    iymin = y
    ixmax = image.shape[1] + x
    iymax = image.shape[0] + y

    xmin = min(cxmin,ixmin)
    xmax = max(cxmax,ixmax)
    ymin = min(cymin,iymin)
    ymax = max(cymax,iymax)
    if (xmax-xmin, ymax-ymin) != (canvas[0].shape[1], canvas[0].shape[0]):
        newcanvas = np.zeros((ymax-ymin, xmax-xmin,3), np.uint8)
        newcanvas[cymin-ymin:cymax-ymin, cxmin-xmin:cxmax-xmin, :] = canvas[0][:,:,:]
    else:
        newcanvas = canvas[0]
    if alpha is None:
        newcanvas[iymin-ymin:iymax-ymin,ixmin-xmin:ixmax-xmin,:] = image[:,:,:]
    else:
        newcanvas[iymin-ymin:iymax-ymin,ixmin-xmin:ixmax-xmin,:] = image[:,:,:]*alpha[:,:,:] + newcanvas[iymin-ymin:iymax-ymin,ixmin-xmin:ixmax-xmin,:]*(1-alpha[:,:,:])
    cv2.imshow("canvas", newcanvas)
    cv2.waitKey(1)
    return newcanvas, (xmin,ymin)


def Usage(argv):
    print "usage: {0} [-a x][-d][-f xmin,xmax,ymin,ymax][-p tl,bl,tr,br][-s r][-w x] movie".format(argv[0])
    print "\t-a x\tAntishake.  Ignore motion smaller than x pixels (5)."
    print "\t-d\tDebug mode."
    print "\t-f xmin,xmax,ymin,ymax\tMotion detection area relative to the image size. (0.333,0.666,0.333,0.666)"
    print "\t-p a,b,c,d\tSet perspective points. Note that perspective correction works for the vertically scrolling picture only."
    print "\t-s r\tSet slit position to r (1)."
    print "\t-w r\tSet slit width (1=same as the length of the interframe motion vector)."
    sys.exit(1)






if __name__ == "__main__":
    import sys

    debug = False #True
    gpts = None #np.float32([380, 350, 1680, 1715])
    slitpos = 250
    slitwidth = 1
    angle = 0
    # -r and -p option must be identical to pass1.py
    #(or they may be given in the input file)
    while len(sys.argv) > 2:
        if sys.argv[1] in ("-d", "--debug"):
            debug = True
        elif sys.argv[1] in ("-s", "--slit"):
            slitpos = int(sys.argv.pop(2))
        elif sys.argv[1] in ("-w", "--width"):
            slitwidth = float(sys.argv.pop(2))
        elif sys.argv[1][0] == "-":
            print "Unknown option: ", sys.argv[1]
            Usage(sys.argv)
        sys.argv.pop(1)

    if len(sys.argv) != 2:
        Usage(sys.argv)


    movie = sys.argv[1]
    LOG = open("{0}.pass1.log".format(movie))
    while True:
        line = LOG.readline()
        if line[0:3] == "#-r":
            angle = -float(line.split()[1]) * math.pi / 180
        elif line[0:3] == "#-p":
            gpts  = [int(x) for x in line.split()[1].split(",")]
        else:
            break
    frame0, absx,absy,idx,idy = [int(x) for x in line.split()]
    cap = cv2.VideoCapture(movie)
    frames = 0  #1 is the first frame
    R = None
    M = None
    canvas = None
    ratio = 0.4
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        h,w = frame.shape[0:2]
            
        frames += 1
        if R is None and angle:
            #Apply rotation
            R, rw, rh = trainscanner.rotate_matrix(angle, w,h)
            h,w = rh,rw
        if M is None and gpts is not None:
            M = trainscanner.warp_matrix(gpts, w,h)
        if frames == frame0:
            if angle:
                frame = cv2.warpAffine(frame, R, (rw,rh))
                h,w = rh,rw
            if gpts is not None:
                frame = cv2.warpPerspective(frame,M,(w,h))
            scaled = cv2.resize(frame,None,fx=ratio, fy=ratio, interpolation = cv2.INTER_CUBIC)
            if canvas == None:
                canvas = (scaled.copy(), (0, 0))
                scaledh, scaledw = scaled.shape[0:2]
            alpha = trainscanner.make_vert_alpha( int(idx*ratio), scaledw, scaledh, slitpos, slitwidth )
            canvas = abs_merge(canvas, scaled, int(absx*ratio), int(absy*ratio), alpha=alpha)
            line = LOG.readline()
            if len(line) == 0:
                break
            frame0, absx,absy,idx,idy = [int(x) for x in line.split()]


