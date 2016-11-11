#!/usr/bin/env python
# -*- coding: utf-8 -*-


import cv2
import numpy as np
import math

def draw_focus_area(f, focus):
    pos = [int(i) for i in w*focus[0],w*focus[1],h*focus[2],h*focus[3]]
    cv2.rectangle(f, (pos[0],pos[2]),(pos[1],pos[3]), (0, 255, 0), 1)

def draw_slit(f, slit):
    dx,dy,pos,width = slit
    dx = int(dx*f.shape[1])
    dy = int(dy*f.shape[0])
    r = math.sqrt(f.shape[0]**2 + f.shape[1]**2)
    pos = int(r*pos)
    if abs(dx) > abs(dy):
        if dx > 0:
            pos = -pos
        width *= dx
        x0 = f.shape[1]/2 + pos + dx
        y0 = 0
        x1 = f.shape[1]/2 + pos
        y1 = f.shape[0]
    else:
        if dy > 0:
            pos = -pos
        width *= dy
        x0 = 0
        y0 = f.shape[0]/2 + pos + dy
        x1 = f.shape[1]
        y1 = f.shape[0]/2 + pos
    cv2.rectangle(f, (x0,y0),(x1,y1), (0, 0, 255), 1)

    


def Usage(argv):
    print "usage: {0} [-a x][-d][-f xmin,xmax,ymin,ymax][-p tl,bl,tr,br][-s r][-w x] movie".format(argv[0])
    print "\t-a x\tAntishake.  Ignore motion smaller than x pixels (5)."
    print "\t-d\tDebug mode."
    print "\t-f xmin,xmax,ymin,ymax\tMotion detection area relative to the image size. (0.333,0.666,0.333,0.666)"
    print "\t-p a,b,c,d\tSet perspective points. Note that perspective correction works for the vertically scrolling picture only."
    print "\t-s r\tSet slit position to r (1)."
    print "\t-w r\tSet slit width (1=same as the length of the interframe motion vector)."
    sys.exit(1)



def preview(frame, name, focus=None, size=700., slit=None):
    h,w,d = frame.shape
    ratio = size/max(w,h)
    scaled = cv2.resize(frame,None,fx=ratio, fy=ratio, interpolation = cv2.INTER_CUBIC)
    if focus is not None:
        draw_focus_area(scaled, focus*ratio)
    if slit is not None:
        draw_slit(scaled, slit)
    cv2.imshow("Original", scaled)
    cv2.waitKey(1)



if __name__ == "__main__":
    import sys

    debug = False #True
    gpts = None #np.float32([380, 350, 1680, 1715])
    slitpos = 1
    slitwidth = 1
    angle = 0
    focus = np.array((0.3333, 0.6666, 0.3333, 0.6666))
    while len(sys.argv) > 2:
        if sys.argv[1] in ("-a", "--antishake"):
            antishake = int(sys.argv.pop(2))
        elif sys.argv[1] in ("-d", "--debug"):
            debug = True
        elif sys.argv[1] in ("-f", "--focus", "--frame"):
            param = sys.argv.pop(2)
            focus = np.float32([float(x) for x in param.split(",")])
        elif sys.argv[1] in ("-p", "--pers", "--perspective"):
            #followed by four numbers separated by comma.
            #left top, bottom, right top, bottom
            param = sys.argv.pop(2)
            gpts  = np.float32([float(x) for x in param.split(",")])
        elif sys.argv[1] in ("-r", "--rotate"):
            angle = float(sys.argv.pop(2)) * math.pi / 180
        elif sys.argv[1] in ("-s", "--slit"):
            slitpos = float(sys.argv.pop(2))
        elif sys.argv[1] in ("-w", "--width"):
            slitwidth = float(sys.argv.pop(2))
        elif sys.argv[1][0] == "-":
            print "Unknown option: ", sys.argv[1]
            Usage(sys.argv)
        sys.argv.pop(1)

    if len(sys.argv) != 2:
        Usage(sys.argv)


    movie = sys.argv[1]
    LOG = open("{0}.log".format(movie))
    frame0, absx,absy,idx,idy = [int(x) for x in LOG.readline().split()]
    cap = cv2.VideoCapture(movie)
    frames = 0  #1 is the first frame
    R = None
    M = None
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        h,w = frame.shape[0:2]
            
        frames += 1
        if R is None and angle:
            #Apply rotation
            a = math.cos(angle)
            b = math.sin(angle)
            R = np.matrix(((a,b,(1-a)*w/2 - b*h/2),(-b,a,b*w/2+(1-a)*h/2)))
        if M is None and gpts is not None:
            #Warp.  Save the perspective matrix to the file for future use.
            p1 = np.float32([(gpts[0],h/4), (gpts[1],h*3/4), (gpts[2],h/4), (gpts[3],h*3/4)])
                #Unskew
            p2 = np.float32([((gpts[0]*gpts[1])**0.5, h/4), ((gpts[0]*gpts[1])**0.5, h*3/4),
                        ((gpts[2]*gpts[3])**0.5, h/4), ((gpts[2]*gpts[3])**0.5, h*3/4)])
            M = cv2.getPerspectiveTransform(p1,p2)
        if frames == frame0:
            if angle:
                frame = cv2.warpAffine(frame, R, (w,h))
            if gpts is not None:
                frame = cv2.warpPerspective(frame,M,(w,h))
            preview(frame, "Snapshot", focus=focus, slit=(float(idx)/w,float(idy)/h,slitpos*0.1,slitwidth))
            line = LOG.readline()
            if len(line) == 0:
                break
            frame0, absx,absy,idx,idy = [int(x) for x in line.split()]


