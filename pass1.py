#!/usr/bin/env python
# -*- coding: utf-8 -*-


import cv2
import numpy as np
import math
import trainscanner

    


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
    print "usage: {0} [-a x][-d][-f xmin,xmax,ymin,ymax][-g n][-p tl,bl,tr,br][-q][-s r][-t x][-w x][-z] movie".format(argv[0])
    print "\t-a x\tAntishake.  Ignore motion smaller than x pixels (5)."
    print "\t-d\tDebug mode."
    print "\t-f xmin,xmax,ymin,ymax\tMotion detection area relative to the image size. (0.333,0.666,0.333,0.666)"
    print "\t-g\tShow guide for perspective correction at the nth frame instead of stitching the movie."
    print "\t-p a,b,c,d\tSet perspective points. Note that perspective correction works for the vertically scrolling picture only."
    print "\t-q\tDo not show the snapshots."
    print "\t-s r\tSet slit position to r (1)."
    print "\t-S n\tSeek the nth frame (0)."
    print "\t-t x\tAdd trailing frames after the motion is not detected. (5)."
    print "\t-w r\tSet slit width (1=same as the length of the interframe motion vector)."
    print "\t-z\tSuppress drift."
    sys.exit(1)




if __name__ == "__main__":
    import sys

    debug = False #True
    guide = False
    seek  = 0
    zero  = False
    gpts = None 
    antishake = 5
    trailing = 10
    commandline = " ".join(sys.argv)
    dumping = 0
    angle = 0
    degree = 0
    every = 1
    identity = 2.0
    margin = 0 # pixels, work in progress.
    #It may be able to unify with antishake.
    focus = [333, 666, 333, 666]
    while len(sys.argv) > 2:
        if sys.argv[1] in ("-a", "--antishake"):
            antishake = int(sys.argv.pop(2))
        elif sys.argv[1] in ("-d", "--debug"):
            debug = True
        elif sys.argv[1] in ("-D", "--dumping"):
            dumping = float(sys.argv.pop(2))
        elif sys.argv[1] in ("-e", "--every"):
            every = int(sys.argv.pop(2))
        elif sys.argv[1] in ("-f", "--focus", "--frame"):
            param = sys.argv.pop(2)
            focus = [int(x) for x in param.split(",")]
        elif sys.argv[1] in ("-g", "--guide"):
            guide = True
        elif sys.argv[1] in ("-i", "--identity"):
            identity = float(sys.argv.pop(2))
        elif sys.argv[1] in ("-m", "--margin"):
            margin = int(sys.argv.pop(2))
        elif sys.argv[1] in ("-p", "--pers", "--perspective"):
            #followed by four numbers separated by comma.
            #left top, bottom, right top, bottom
            param = sys.argv.pop(2)
            gpts  = [int(x) for x in param.split(",")]
        elif sys.argv[1] in ("-r", "--rotate"):
            degree = float(sys.argv.pop(2))
            angle = -degree * math.pi / 180
        elif sys.argv[1] in ("-S", "--seek"):
            seek = int(sys.argv.pop(2))
        elif sys.argv[1] in ("-t", "--trail"):
            trailing = int(sys.argv.pop(2))
        elif sys.argv[1] in ("-z", "--zero"):
            zero  = True
        elif sys.argv[1][0] == "-":
            print "Unknown option: ", sys.argv[1]
            Usage(sys.argv)
        sys.argv.pop(1)

    if len(sys.argv) != 2:
        Usage(sys.argv)

    movie = sys.argv[1]
    cap = cv2.VideoCapture(movie)
    frames = 0  #1 is the first frame
    ret = True
    for i in range(seek):  #skip frames
        ret = cap.grab()
        if not ret:
            break
        #ret, frame = cap.read()
        frames += 1
    if not ret:
        sys.exit(0)
    ret, frame = cap.read()
    frames += 1
    if not ret:
        sys.exit(0)
    h, w, d = frame.shape
    if angle:
        #Apply rotation
        h, w, d = frame.shape
        R, rw,rh = trainscanner.rotate_matrix(angle, w, h)
        frame = cv2.warpAffine(frame, R, (rw,rh))
    h, w, d = frame.shape

    if gpts is not None:
        M = trainscanner.warp_matrix(gpts,w,h)
        frame = cv2.warpPerspective(frame,M,(w,h))
        #print M
        #np.save("{0}.perspective.npy".format(movie), M) #Required to recover the perspective
        #These settings should be stored in the gui.

    #Prepare a scalable canvas with the origin.
    canvas = [100,100,0,0]

    #prepare the previewer process
    #import pipes
    #t = pipes.Template()
    #t.append("./preview.py -f ", "--")
    LOG = open("{0}.pass1.log".format(movie),"w")
    if angle != 0:
        LOG.write("#-r {0}\n".format(degree))
    if gpts is not None:
        LOG.write("#-p {0},{1},{2},{3}\n".format(*gpts))
    onWork = False
    absx,absy = 0,0
    lastdx, lastdy = 0.0, 0.0
    dx = 0.0
    dy = 0.0
    idx = idy = 0
    tr = 0
    while True:
        ret = True
        for i in range(every-1):  #skip frames
            ret = cap.grab()
            if not ret:
                break
            frames += 1
        if not ret:
            break
        ret, nextframe = cap.read()
        if not ret:
            break
        if angle:
            nextframe = cv2.warpAffine(nextframe, R, (w,h))
            #w and h are sizes after rotation
        frames += 1
        if gpts is not None:
            nextframe = cv2.warpPerspective(nextframe,M,(w,h))
        diff = cv2.absdiff(nextframe,frame)
        diff = np.sum(diff) / (h*w*3)
        if diff < identity:
            print "skip identical frame #",diff
            #They are identical frames
            #This happens when the frame rate difference is compensated.
            continue
            
        if margin > 0 and onWork:
            dx0,dy0 = trainscanner.motion(frame, nextframe, focus=focus, margin=margin, delta=(lastdx,lastdy) )
        else:
            dx0,dy0 = trainscanner.motion(frame, nextframe, focus=focus)
            
        if dumping and onWork:
            dx += (dx0 - lastdx)/dumping + lastdx
            dy += (dy0 - lastdy)/dumping + lastdy
            print frames,dx,dy,dx0,dy0,"#",np.amax(diff)
        else:
            dx += dx0
            dy += dy0
            print frames,dx0,dy0,"#",np.amax(diff)

        if zero:
            if abs(dx) < abs(dy):
                dx = 0
            else:
                dy = 0
        idx = int(dx)
        idy = int(dy)
        #Error dispersion
        dx -= int(dx)
        dy -= int(dy)
        if (abs(idx) > antishake or abs(idy) > antishake):
            if not onWork:
                onWork = True
            tr = 0
        else:
            if onWork:
                if tr <= trailing:
                    tr += 1
                    idx = lastdx
                    idy = lastdy
                    print ">>({2}) {0} {1} #{3}".format(idx,idy,tr,np.amax(diff))
                else:
                    #end of work
                    break
        absx += idx
        absy += idy
        if onWork:
            lastdx, lastdy = idx,idy
            canvas = canvas_size(canvas, nextframe, absx, absy)
            LOG.write("{0} {1} {2} {3} {4}\n".format(frames,absx,absy,idx,idy))
        frame = nextframe

