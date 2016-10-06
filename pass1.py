#!/usr/bin/env python
# -*- coding: utf-8 -*-


import cv2
import numpy as np
import math


    
def motion(ref, img, focus=(0.3333, 0.6666, 0.3333, 0.6666), margin=0, delta=(0,0)):
    hi,wi = img.shape[0:2]
    wmin = int(wi*focus[0])
    wmax = int(wi*focus[1])
    hmin = int(hi*focus[2])
    hmax = int(hi*focus[3])
    template = img[hmin:hmax,wmin:wmax,:]
    h,w = template.shape[0:2]

    # Apply template Matching
    if margin == 0:
        res = cv2.matchTemplate(ref,template,cv2.TM_SQDIFF_NORMED)
        #loc is given by x,y
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        return min_loc[0] - wmin, min_loc[1] - hmin
    else:
        #use delta here
        roix0 = wmin + delta[0] - margin
        roiy0 = hmin + delta[1] - margin
        roix1 = wmax + delta[0] + margin
        roiy1 = hmax + delta[1] + margin
        crop = ref[roiy0:roiy1, roix0:roix1, :]
        res = cv2.matchTemplate(crop,template,cv2.TM_SQDIFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        #loc is given by x,y
        return (min_loc[0] + roix0 - wmin, min_loc[1] + roiy0 - hmin)


canvases = []

#Automatically extensible canvas.
def abs_merge(canvas, image, x, y, alpha=None, split=0, name="" ):
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
    if split:
        if debug:
            print np.product(canvas[0].shape),np.product(image.shape)
        if np.product(canvas[0].shape) > np.product(image.shape) * split:
            # if name is given, purge the fragment to the disk
            if name == "":
                canvases.append((newcanvas, (xmin,ymin)))
            else:
                cv2.imwrite("{0}.{1:+d}{2:+d}.png".format(name,xmin,ymin), newcanvas)
                canvases.append((xmin,ymin))
            newcanvas = newcanvas[iymin-ymin:iymax-ymin,ixmin-xmin:ixmax-xmin,:]
            xmin = ixmin
            ymin = iymin
    if debug:
        print "newcanvas:  {0}x{1} {2:+d}{3:+d}".format(newcanvas.shape[1],newcanvas.shape[0],xmin,ymin)
    return newcanvas, (xmin,ymin)


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
    print "usage: {0} [-2][-a x][-d][-f xmin,xmax,ymin,ymax][-g n][-p tl,bl,tr,br][-q][-s r][-t x][-w x][-z] movie".format(argv[0])
    print "\t-2\tTwo pass.  Store the intermediate image fragments on the disk and do not merge them."
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
    gpts = None #np.float32([380, 350, 1680, 1715])
    slitpos = 1
    slitwidth = 1
    antishake = 5
    trailing = 10
    commandline = " ".join(sys.argv)
    dumping = 0
    angle = 0
    every = 1
    identity = 2.0
    margin = 0 # pixels, work in progress.
    #It may be able to unify with antishake.
    focus = np.array((0.3333, 0.6666, 0.3333, 0.6666))
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
            focus = np.float32([float(x) for x in param.split(",")])
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
            gpts  = np.float32([float(x) for x in param.split(",")])
        elif sys.argv[1] in ("-r", "--rotate"):
            angle = float(sys.argv.pop(2)) * math.pi / 180
        elif sys.argv[1] in ("-s", "--slit"):
            slitpos = float(sys.argv.pop(2))
        elif sys.argv[1] in ("-S", "--seek"):
            seek = int(sys.argv.pop(2))
        elif sys.argv[1] in ("-t", "--trail"):
            trailing = int(sys.argv.pop(2))
        elif sys.argv[1] in ("-w", "--width"):
            slitwidth = float(sys.argv.pop(2))
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
        a = math.cos(angle)
        b = math.sin(angle)
        R = np.matrix(((a,b,(1-a)*w/2 - b*h/2),(-b,a,b*w/2+(1-a)*h/2)))
        frame = cv2.warpAffine(frame, R, (w,h))
    
    if guide:
        #Show the perspective guides and quit.
        fontFace = cv2.FONT_HERSHEY_SCRIPT_SIMPLEX
        for i in range(0,w,5):
            cv2.line(frame, (i,h/4),(i,h/4+5), (0, 255, 0), 1)
            cv2.line(frame, (i,h*3/4),(i,h*3/4-5), (0, 255, 0), 1)
        for i in range(0,w,50):
            cv2.line(frame, (i,h/4),(i,h/4+10), (0, 0, 255), 1)
            cv2.line(frame, (i,h*3/4),(i,h*3/4-10), (0, 0, 255), 1)
            cv2.putText(frame, "{0}".format(i), (i,h/4), fontFace, 0.3, (0,0,255))
            cv2.putText(frame, "{0}".format(i), (i,h*3/4+10), fontFace, 0.3, (0,0,255))
        if gpts is not None:
            cv2.line(frame, (gpts[0],h/4), (gpts[1],h*3/4), (255, 0, 0), 1)
            cv2.line(frame, (gpts[2],h/4), (gpts[3],h*3/4), (255, 0, 0), 1)
        draw_focus_area(frame, focus)
        cv2.imshow("Guide lines", frame)
        cv2.waitKey()
        sys.exit(0)

    if gpts is not None:
        #Warp.  Save the perspective matrix to the file for future use.
        p1 = np.float32([(gpts[0],h/4), (gpts[1],h*3/4), (gpts[2],h/4), (gpts[3],h*3/4)])
        #Unskew
        p2 = np.float32([((gpts[0]*gpts[1])**0.5, h/4), ((gpts[0]*gpts[1])**0.5, h*3/4),
                        ((gpts[2]*gpts[3])**0.5, h/4), ((gpts[2]*gpts[3])**0.5, h*3/4)])
        M = cv2.getPerspectiveTransform(p1,p2)
        frame = cv2.warpPerspective(frame,M,(w,h))
        print M
        np.save("{0}.perspective.npy".format(movie), M) #Required to recover the perspective


    #Prepare a scalable canvas with the origin.
    canvas = [100,100,0,0]

    #prepare the previewer process
    #import pipes
    #t = pipes.Template()
    #t.append("./preview.py -f ", "--")
    LOG = open("{0}.log".format(movie),"w")
    
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
            a = math.cos(angle)
            b = math.sin(angle)
            R = np.matrix(((a,b,(1-a)*w/2 - b*h/2),(-b,a,b*w/2+(1-a)*h/2)))
            nextframe = cv2.warpAffine(nextframe, R, (w,h))
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
            dx0,dy0 = motion(frame, nextframe, focus=focus, margin=margin, delta=(lastdx,lastdy) )
        else:
            dx0,dy0 = motion(frame, nextframe, focus=focus)
            
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

