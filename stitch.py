#!/usr/bin/env python
# -*- coding: utf-8 -*-


import cv2
import numpy as np
import math

alphas = dict()

def make_orth_alpha( d, img_size, slit=0.0, width=1 ):
    """
    Make an orthogonal mask
    """
    if abs(d[0]) > abs(d[1]):
        d = d[0],0
    else:
        d = 0,d[1]
    if (d[0], d[1], img_size[1], img_size[0], slit) in alphas:
        return alphas[(d[0], d[1], img_size[1], img_size[0], slit)]
    r = (d[0]**2 + d[1]**2)**0.5
    if r == 0:
        return None
    dx = d[0] / r
    dy = d[1] / r
    ih, iw = img_size
    diag = (ih**2 + iw**2)**0.5
    centerx = iw/2 - dx * diag * slit
    centery = ih/2 - dy * diag * slit
    alpha = np.fromfunction(lambda y, x, v: (dx*(x-centerx)+dy*(y-centery))/(r*width), (ih, iw, 3))
    np.clip(alpha,-1,1,out=alpha)  # float 0..1 values
    alpha = (alpha+1) / 2
    alphas[(d[0], d[1], img_size[1], img_size[0], slit)] = alpha
    if debug:
        cv2.imshow("alpha",np.array(alpha*255, np.uint8))
    return alpha


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
            scaled = cv2.resize(frame,None,fx=ratio, fy=ratio, interpolation = cv2.INTER_CUBIC)
            if canvas == None:
                canvas = (scaled.copy(), (0, 0))
                scaledh, scaledw = scaled.shape[0:2]
            alpha = make_orth_alpha( (int(idx*ratio),int(idy*ratio)), (scaledh,scaledw), slitpos*0.1, slitwidth )
            canvas = abs_merge(canvas, scaled, int(absx*ratio), int(absy*ratio), alpha=alpha)
            line = LOG.readline()
            if len(line) == 0:
                break
            frame0, absx,absy,idx,idy = [int(x) for x in line.split()]


