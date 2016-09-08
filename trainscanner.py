#!/usr/bin/env python
# -*- coding: utf-8 -*-


import cv2
import numpy as np


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

canvases = []

#Absolute merger
#x,y is the absolute position of the image
#The canvas may often become huge, then the merging takes very long time.
#So the canvas will be split automatically and the fragments will be stored in canvases on demand.
#Later the fragments are stitched together to recover the full canvas.
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
            # if name is given, do not store in memory
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
    guide = 0
    zero  = False
    gpts = None #np.float32([380, 350, 1680, 1715])
    slitpos = 0.1
    slitwidth = 1
    visual = True
    antishake = 5
    trailing = 10
    skip_identical = False
    commandline = " ".join(sys.argv)
    onMemory = True

    focus = np.array((0.3333, 0.6666, 0.3333, 0.6666))
    while len(sys.argv) > 2:
        if sys.argv[1] in ("-d", "--debug"):
            debug = True
        if sys.argv[1] in ("-q", "--quiet"):
            visual = False
        if sys.argv[1] in ("-g", "--guide"):
            guide = int(sys.argv.pop(2))
        if sys.argv[1] in ("-a", "--antishake"):
            antishake = int(sys.argv.pop(2))
        if sys.argv[1] in ("-t", "--trail"):
            trailing = int(sys.argv.pop(2))
        if sys.argv[1] in ("-s", "--slit"):
            slitpos = float(sys.argv.pop(2))
        if sys.argv[1] in ("-w", "--width"):
            slitwidth = float(sys.argv.pop(2))
        if sys.argv[1] in ("-z", "--zero"):
            zero  = True
        if sys.argv[1] in ("--skip_identical"):
            skip_identical = True #hidden option
        if sys.argv[1] in ("-2", "--twopass"):
            onMemory  = False
        if sys.argv[1] in ("-p", "--pers", "--perspective"):
            #followed by four numbers separated by comma.
            #left top, bottom, right top, bottom
            param = sys.argv.pop(2)
            gpts  = np.float32([float(x) for x in param.split(",")])
        if sys.argv[1] in ("-f", "--focus", "--frame"):
            param = sys.argv.pop(2)
            focus = np.float32([float(x) for x in param.split(",")])
        sys.argv.pop(1)

    if len(sys.argv) != 2:
        print "usage: {0} [-2][-a x][-d][-f xmin,xmax,ymin,ymax][-g n][-p tl,bl,tr,br][-q][-s r][-t x][-w x][-z] movie".format(sys.argv[0])
        print "\t-2\t\tTwo pass.  Store the intermediate image fragments on the disk and do not merge them."
        print "\t-a x\tAntishake.  Ignore motion smaller than x pixels (5)."
        print "\t-d\t\tDebug mode."
        print "\t-f xmin,xmax,ymin,ymax\tMotion detection area relative to the image size. (0.333,0.666,0.333,0.666)"
        print "\t-g n\tShow guide for perspective correction at the nth frame instead of stitching the movie."
        print "\t-p a,b,c,d\tSet perspective points. Note that perspective correction works for the vertically scrolling picture only."
        print "\t-q\t\tnDo not show the snapshots."
        print "\t-s r\tSet slit position to r (0.2)."
        print "\t-t x\tAdd trailing frames after the motion is not detected. (5)."
        print "\t-w r\tSet slit width (1=same as the length of the interframe motion vector)."
        print "\t-z\t\tSuppress drift."
        sys.exit(1)

    movie = sys.argv[1]
    cap = cv2.VideoCapture(movie)

    ret, frame = cap.read()
    h, w, d = frame.shape

    if guide:
        #Show the perspective guides and quit.
        for i in range(guide-1):  #skip frames
            ret, frame = cap.read()
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
    lastdx, lastdy = 0, 0
    tr = trailing
    while True:
        ret, nextframe = cap.read()
        if not ret:
            break
        if gpts is not None:
            nextframe = cv2.warpPerspective(nextframe,M,(w,h))
        if debug:
            preview(nextframe, "Debug", focus=focus)
            
        dx,dy = motion(frame, nextframe, focus=focus)
        if skip_identical and dx == 0 and dy == 0 and onWork:
            print "skip"
            continue
            #In Youtube videos uploaded from Europe (PAL)
            #identical frames are inserted for every 6 frames.
            #(Perhaps they use 25 fps instead of 30 fps)
            #This causes ghosting when trailing option is active.
            #skip_identical option just ignore the identical frames
            #during working on.
        print dx,dy
        if zero:
            if abs(dx) < abs(dy):
                dx = 0
            else:
                dy = 0
        if (abs(dx) > antishake or abs(dy) > antishake):
            if not onWork:
                onWork = True
            tr = trailing
        else:
            if onWork:
                if tr > 0:
                    tr -= 1
                    dx = lastdx
                    dy = lastdy
                    print ">>({2}) {0} {1}".format(dx,dy,tr)
                else:
                    #end of work
                    break
        absx += dx
        absy += dy
        if onWork:
            lastdx, lastdy = dx,dy
            alpha = make_alpha( (dx,dy), (h,w), slitpos, slitwidth )
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
    
