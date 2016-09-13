#!/usr/bin/env python
# -*- coding: utf-8 -*-


import cv2
import numpy as np
import math

def draw_focus_area(f, focus):
    pos = [int(i) for i in w*focus[0],w*focus[1],h*focus[2],h*focus[3]]
    cv2.rectangle(f, (pos[0],pos[2]),(pos[1],pos[3]), (0, 255, 0), 1)


def motion(ref, img, focus=(0.3333, 0.6666, 0.3333, 0.6666)):
    hi,wi = img.shape[0:2]
    wmin = int(wi*focus[0])
    wmax = int(wi*focus[1])
    hmin = int(hi*focus[2])
    hmax = int(hi*focus[3])
    template = img[hmin:hmax,wmin:wmax,:]
    h,w = template.shape[0:2]

    # Apply template Matching
    res = cv2.matchTemplate(ref,template,cv2.TM_SQDIFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    #loc is given by x,y
    top_left = min_loc
    return top_left[0] - wmin, top_left[1] - hmin


alphas = dict()

def make_alpha( d, img_size, slit=0.0, width=1 ):
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


def make_orth_alpha( d, img_size, slit=0.0, width=1 ):
    """
    Make an orthogonal mask
    """
    if (d[0], d[1], img_size[1], img_size[0], slit) in alphas:
        return alphas[(d[0], d[1], img_size[1], img_size[0], slit)]
    if abs(d[0]) > abs(d[1]):
        d = d[0],0
    else:
        d = 0,d[1]
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

def Usage(argv):
    print "usage: {0} [-2][-a x][-d][-f xmin,xmax,ymin,ymax][-g n][-p tl,bl,tr,br][-q][-s r][-t x][-w x][-z] movie".format(argv[0])
    print "\t-2\tTwo pass.  Store the intermediate image fragments on the disk and do not merge them."
    print "\t-a x\tAntishake.  Ignore motion smaller than x pixels (5)."
    print "\t-d\tDebug mode."
    print "\t-f xmin,xmax,ymin,ymax\tMotion detection area relative to the image size. (0.333,0.666,0.333,0.666)"
    print "\t-g\tShow guide for perspective correction at the nth frame instead of stitching the movie."
    print "\t-p a,b,c,d\tSet perspective points. Note that perspective correction works for the vertically scrolling picture only."
    print "\t-q\tDo not show the snapshots."
    print "\t-s r\tSet slit position to r (0.2)."
    print "\t-S n\tSeek the nth frame (0)."
    print "\t-t x\tAdd trailing frames after the motion is not detected. (5)."
    print "\t-w r\tSet slit width (1=same as the length of the interframe motion vector)."
    print "\t-z\tSuppress drift."
    sys.exit(1)



def preview(frame, name, focus=None, size=700.):
    h,w,d = frame.shape
    ratio = size/max(w,h)
    scaled = cv2.resize(frame,None,fx=ratio, fy=ratio, interpolation = cv2.INTER_CUBIC)
    if focus is not None:
        draw_focus_area(scaled, focus*ratio)
    cv2.imshow("First frame", scaled)
    cv2.waitKey(1)

if __name__ == "__main__":
    import sys

    debug = False #True
    guide = False
    seek  = 0
    zero  = False
    gpts = None #np.float32([380, 350, 1680, 1715])
    slitpos = 0.1
    slitwidth = 1
    visual = True
    antishake = 5
    trailing = 10
    commandline = " ".join(sys.argv)
    onMemory = True
    dumping = 0
    angle = 0
    
    focus = np.array((0.3333, 0.6666, 0.3333, 0.6666))
    while len(sys.argv) > 2:
        if sys.argv[1] in ("-d", "--debug"):
            debug = True
        elif sys.argv[1] in ("-q", "--quiet"):
            visual = False
        elif sys.argv[1] in ("-S", "--seek"):
            seek = int(sys.argv.pop(2))
        elif sys.argv[1] in ("-D", "--dumping"):
            dumping = float(sys.argv.pop(2))
        elif sys.argv[1] in ("-r", "--rotate"):
            angle = float(sys.argv.pop(2)) * math.pi / 180
        elif sys.argv[1] in ("-g", "--guide"):
            guide = True
        elif sys.argv[1] in ("-a", "--antishake"):
            antishake = int(sys.argv.pop(2))
        elif sys.argv[1] in ("-t", "--trail"):
            trailing = int(sys.argv.pop(2))
        elif sys.argv[1] in ("-s", "--slit"):
            slitpos = float(sys.argv.pop(2))
        elif sys.argv[1] in ("-w", "--width"):
            slitwidth = float(sys.argv.pop(2))
        elif sys.argv[1] in ("-z", "--zero"):
            zero  = True
        elif sys.argv[1] in ("-2", "--twopass"):
            onMemory  = False
        elif sys.argv[1] in ("-p", "--pers", "--perspective"):
            #followed by four numbers separated by comma.
            #left top, bottom, right top, bottom
            param = sys.argv.pop(2)
            gpts  = np.float32([float(x) for x in param.split(",")])
        elif sys.argv[1] in ("-f", "--focus", "--frame"):
            param = sys.argv.pop(2)
            focus = np.float32([float(x) for x in param.split(",")])
        elif sys.argv[1][0] == "-":
            print "Unknown option: ", sys.argv[1]
            Usage(sys.argv)
        sys.argv.pop(1)

    if len(sys.argv) != 2:
        Usage(sys.argv)

    movie = sys.argv[1]
    cap = cv2.VideoCapture(movie)
    frames = 0
    for i in range(seek):  #skip frames
        cap.grab()
        #ret, frame = cap.read()
        frames += 1
    ret, frame = cap.read()
    frames += 1
    h, w, d = frame.shape
    if angle:
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
    canvas = (frame.copy(), (0, 0))

    if not debug:
        preview(frame, "First frame", focus=focus)
    
    onWork = False
    absx,absy = 0,0
    lastdx, lastdy = 0.0, 0.0
    dx = 0.0
    dy = 0.0
    idx = idy = 0
    tr = 0
    while True:
        ret, nextframe = cap.read()
        if angle:
            a = math.cos(angle)
            b = math.sin(angle)
            R = np.matrix(((a,b,(1-a)*w/2 - b*h/2),(-b,a,b*w/2+(1-a)*h/2)))
            nextframe = cv2.warpAffine(nextframe, R, (w,h))
        frames += 1
        if not ret:
            break
        if gpts is not None:
            nextframe = cv2.warpPerspective(nextframe,M,(w,h))
        diff = cv2.absdiff(nextframe,frame)
        if np.amax(diff) < 80:
            print "skip adjustment frame"
            #They are identical frames
            #This happens when the frame rate difference is compensated.
            continue
        if debug:
            preview(nextframe, "Debug", focus=focus)
            
        dx0,dy0 = motion(frame, nextframe, focus=focus)
        if dumping and onWork:
            dx += (dx0 - lastdx)/dumping + lastdx
            dy += (dy0 - lastdy)/dumping + lastdy
            print frames,dx,dy,dx0,dy0
        else:
            dx += dx0
            dy += dy0
            print frames,dx0,dy0
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
                    print ">>({2}) {0} {1}".format(idx,idy,tr)
                else:
                    #end of work
                    break
        absx += idx
        absy += idy
        if onWork:
            lastdx, lastdy = idx,idy
            alpha = make_orth_alpha( (idx,idy), (h,w), slitpos, slitwidth )
            if onMemory:
                canvas = abs_merge(canvas, nextframe, absx, absy, alpha=alpha, split=2)
            else:
                canvas = abs_merge(canvas, nextframe, absx, absy, alpha=alpha, split=2, name=movie)
            if debug:
                cv2.imshow("canvas", canvas[0])
                cv2.waitKey()
            if visual:
                f = nextframe.copy()
                #Red mask indicates the overlay alpha
                f[:,:,0:2] = np.uint8(f[:,:,0:2] * alpha[:,:,0:2])
                preview(f, "Snapshot", focus=focus)
        frame = nextframe

    #Store the residue canvas.
    if onMemory:
        canvases.append(canvas)
    else:
        frame = canvas[0]
        location = canvas[1]
        cv2.imwrite("{0}.{1:+d}{2:+d}.png".format(movie,*location), frame)    
        canvases.append(location)

    #Store the fragments
    #for c in canvases:
    #    cv2.imwrite("{0}.{1:+d}{2:+d}.png".format(movie,c[1][0],c[1][1]), c[0])

    if gpts is not None:
        print M

    #Store the command line for convenience.
    logfile = open("{0}.log".format(movie), "w")
    logfile.write("{0}\n\n".format(commandline))
    if onMemory:
        #Stitch all the fragments to make a huge canvas.
        merged = (np.zeros((100,100,3),np.uint8), (0,0))
        for c in canvases:
            frame = c[0]
            location = c[1]
            merged = abs_merge(merged, frame, *location)

        # save the full frame
        cv2.imwrite("{0}.full.png".format(movie), merged[0])
    else:
        logfile.write("[Canvas fragments]\n")
        for c in canvases:
            location = c
            fragname = "{0}.{1:+d}{2:+d}.png".format(movie,*location)
            frame = cv2.imread(fragname)
            logfile.write("@{1:+d} {2:+d} {0}\n".format(fragname, *location))
    
