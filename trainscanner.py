#!/usr/bin/env python
# -*- coding: utf-8 -*-

#Now only the horizontal scroll is allowed
from __future__ import print_function
import cv2
import numpy as np
import math



#fit image in a square
def fit_to_square(image, size):
    h,w = image.shape[0:2]
    modified = False
    if h > w:
        if h > size:
            w = w*size/h
            h = size
            modified = True
    else:
        if w > size:
            h = h*size/w
            w = size
            modified = True
    if not modified:
        return image
    return cv2.resize(image,(w,h),interpolation = cv2.INTER_CUBIC)


class transformation():
    def __init__(self, angle=0, pers=None, crop=None):
        self.angle = -angle * math.pi / 180.0
        self.pers = pers
        self.crop = crop
        self.R    = None
        self.M    = None
    def rotation_affine(self,w,h):
        a = math.cos(self.angle)
        b = math.sin(self.angle)
        rh = max(abs(h*a), abs(w*b))
        rw = max(abs(h*b), abs(w*a))
        self.rh, self.rw = int(rh), int(rw)
        self.R = np.matrix(((a,b,(1-a)*w/2 - b*h/2 +(rw-w)/2),(-b,a,b*w/2+(1-a)*h/2+(rh-h)/2)))
    def rotated_image(self, image):
        return cv2.warpAffine(image, self.R, (self.rw,self.rh))
    def warp_affine(self):
        """
        Warp.  Save the perspective matrix to the file for future use.
        """
        if self.pers is None:
            return
        w = self.rw
        h = self.rh
        L = (self.pers[2]-self.pers[0])*h/1000
        S = (self.pers[3]-self.pers[1])*h/1000
        if L < S:
            L,S  = S,L
        LS = (L*S)**0.5
        fdist = float(L)/S
        ndist = LS/S
        sratio = ((fdist - 1.0)**2 + 1)**0.5
        neww = int(w*sratio/ndist)
        woffset = (neww - w)/2
        p1 = np.float32([(0,self.pers[0]*h/1000),
                         (w,self.pers[1]*h/1000),
                         (0,self.pers[2]*h/1000),
                         (w,self.pers[3]*h/1000)])
        #Unskew
        p2 = np.float32([(0, (self.pers[0]*self.pers[1])**0.5*h/1000),
                         (neww,(self.pers[0]*self.pers[1])**0.5*h/1000),
                         (0,(self.pers[2]*self.pers[3])**0.5*h/1000),
                         (neww,(self.pers[2]*self.pers[3])**0.5*h/1000)])
        self.M = cv2.getPerspectiveTransform(p1,p2)
        self.ww = neww
    def warped_image(self, image):
        if self.pers is None:
            return image
        h = image.shape[0]
        return cv2.warpPerspective(image,self.M,(self.ww,h))
    def cropped_image(self, image):
        if self.crop is None:
            return image
        h,w = image.shape[:2]
        return image[self.crop[0]*h/1000:self.crop[1]*h/1000, :, :]
    def process_first_image(self, image):
        h,w = image.shape[:2]
        self.rotation_affine(w,h)
        self.warp_affine()
        return self.process_next_image(image)
    def process_next_image(self, image):
        rotated = self.rotated_image(image)
        warped  = self.warped_image(rotated)
        cropped = self.cropped_image(warped)
        return rotated, warped, cropped
    def process_image(self, image):
        if self.R is None:
            return self.process_first_image(image)
        else:
            return self.process_next_image(image)
    def process_images(self, images):
        h,w = images[0].shape[:2]
        self.rotation_affine(w,h)
        self.warp_affine()
        rs = []
        ws = []
        cs = []
        for image in images:
            rotated, warped, cropped = self.process_next_image(image)
            rs.append(rotated)
            ws.append(warped)
            cs.append(cropped)
        return rs,ws,cs
        
        
    

def draw_focus_area(f, focus, delta=0):
    h, w = f.shape[0:2]
    pos = [w*focus[0]/1000,w*focus[1]/1000,h*focus[2]/1000,h*focus[3]/1000]
    cv2.rectangle(f, (pos[0],pos[2]),(pos[1],pos[3]), (0, 255, 0), 1)
    if delta != 0:
        pos = [w*focus[0]/1000+delta,w*focus[1]/1000+delta,h*focus[2]/1000,h*focus[3]/1000]
        cv2.rectangle(f, (pos[0],pos[2]),(pos[1],pos[3]), (255, 255, 0), 1)
        


def draw_slit_position(f, slitpos, dx):
    h, w = f.shape[0:2]
    if dx > 0:
        x1 = w/2 + slitpos*w/1000
        x2 = x1 - dx
    else:
        x1 = w/2 - slitpos*w/1000
        x2 = x1 - dx
    cv2.line(f, (x1,0),(x1,h), (0,255,0), 1)
    cv2.line(f, (x2,0),(x2,h), (0,255,0), 1)


def draw_guide(frame, pers, gauge=True):
    h,w = frame.shape[0:2]
    fontFace = cv2.FONT_HERSHEY_SCRIPT_SIMPLEX
    if gauge:
        for i in range(0,10):
            cv2.line(frame, (i*w/10,0),(i*w/10,h), (255, 255, 0), 1)
        for i in range(0,10):
            cv2.line(frame, (0,i*h/10),(w,i*h/10), (255, 255, 0), 1)
        ticks = 1000
        while h < ticks*2:
            ticks /= 2
            lticks = ticks / 5
            if h < ticks*2:
                ticks /= 5
                lticks = ticks / 10
        tickw = h / ticks
        for i in range(0,ticks):
            y = h*i/ticks
            cv2.line(frame, (0,y),(tickw,y), (0, 255, 0), 1)
            cv2.line(frame, (w-tickw,y),(w,y), (0, 255, 0), 1)
        for i in range(0,lticks):
            y = h*i/lticks
            cv2.line(frame, (0,y),(2*tickw,y), (0, 0, 255), 1)
            cv2.line(frame, (w-tickw*2,y),(w,y), (0, 0, 255), 1)
            cv2.putText(frame, "{0}".format(1000*i/lticks), (tickw*3,y), fontFace, 0.3, (0,0,255))
            cv2.putText(frame, "{0}".format(1000*i/lticks), (w-tickw*3-30,y), fontFace, 0.3, (0,0,255))
    if pers is not None:
        cv2.line(frame, (0,pers[0]*h/1000), (w,pers[1]*h/1000), (255, 0, 0), 1)
        cv2.line(frame, (0,pers[2]*h/1000), (w,pers[3]*h/1000), (255, 0, 0), 1)

def motion(ref, img, focus=(333, 666, 333, 666), margin=0, delta=(0,0), antishake=2):
    hi,wi = img.shape[0:2]
    wmin = wi*focus[0]/1000
    wmax = wi*focus[1]/1000
    hmin = hi*focus[2]/1000
    hmax = hi*focus[3]/1000
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
        refh,refw = ref.shape[0:2]
        if roix0 < 0 or roix1 >= refw or roiy0 < 0 or roiy1 >= refh:
            #print(roix0,roix1,roiy0,roiy1,refw,refh)
            return None
        crop = ref[roiy0:roiy1, roix0:roix1, :]
        res = cv2.matchTemplate(crop,template,cv2.TM_SQDIFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        #loc is given by x,y

        #Test: isn't it just a background?
        roix02 = wmin - antishake
        roiy02 = hmin - antishake
        roix12 = wmax + antishake
        roiy12 = hmax + antishake
        crop = ref[roiy02:roiy12, roix02:roix12, :]
        res = cv2.matchTemplate(crop,template,cv2.TM_SQDIFF_NORMED)
        min_val2, max_val2, min_loc2, max_loc2 = cv2.minMaxLoc(res)
        #loc is given by x,y
        if min_val <= min_val2:
            return (min_loc[0] + roix0 - wmin, min_loc[1] + roiy0 - hmin)
        else:
            return (min_loc2[0] + roix02 - wmin, min_loc2[1] + roiy02 - hmin)
        

#global


def make_vert_alpha( alphas, displace, img_width, img_height, slit=0, width=1.0 ):
    """
    Make an orthogonal mask
    slit position is -500 to 500
    slit width=1 is standard, width<1 is narrow (sharp) and width>1 is diffuse alpha
    """
    if (displace, width, slit) in alphas:
        return alphas[(displace, width, slit)]
    if displace == 0:
        return np.zeros((img_height,img_width,3))+1
    if displace > 0:
        centerx = img_width/2 - slit*img_width/1000
    else:
        centerx = img_width/2 + slit*img_width/1000
    alpha = np.fromfunction(lambda y, x, v: (x-centerx)/(displace*width), (img_height, img_width, 3))
    np.clip(alpha,0,1,out=alpha)  # float 0..1 values
    #alpha += 1
    alphas[(displace, width, slit)] = alpha
    return alpha

#global
canvases = []

#Automatically extensible canvas.
def abs_merge(canvas, image, x, y, alpha=None, split=0, name="" ):
    absx, absy = canvas[1]   #absolute coordinate of the top left of the canvas
    if debug:
        print(canvas)
        print(image)
        print("canvas:  {0}x{1} {2:+d}{3:+d}".format(canvas[0].shape[1],canvas[0].shape[0],absx,absy))
        print("overlay: {0}x{1} {2:+d}{3:+d}".format(image.shape[1], image.shape[0],x,y))
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
            print(np.product(canvas[0].shape),np.product(image.shape))
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
        print("newcanvas:  {0}x{1} {2:+d}{3:+d}".format(newcanvas.shape[1],newcanvas.shape[0],xmin,ymin))
    return newcanvas, (xmin,ymin)

def Usage(argv):
    print("usage: {0} [-2][-a x][-d][-f xmin,xmax,ymin,ymax][-g n][-p tl,bl,tr,br][-q][-s r][-t x][-w x][-z] movie".format(argv[0]))
    print("\t-2\tTwo pass.  Store the intermediate image fragments on the disk and do not merge them.")
    print("\t-a x\tAntishake.  Ignore motion smaller than x pixels (5).")
    print("\t-d\tDebug mode.")
    print("\t-f xmin,xmax,ymin,ymax\tMotion detection area relative to the image size. (333,666,333,666)")
    print("\t-g\tShow guide for perspective correction at the nth frame instead of stitching the movie.")
    print("\t-p a,b,c,d\tSet perspective points. Note that perspective correction works for the vertically scrolling picture only.")
    print("\t-q\tDo not show the snapshots.")
    print("\t-s r\tSet slit position to r (1).")
    print("\t-S n\tSeek the nth frame (0).")
    print("\t-t x\tAdd trailing frames after the motion is not detected. (5).")
    print("\t-w r\tSet slit width (1=same as the length of the interframe motion vector).")
    print("\t-z\tSuppress drift.")
    sys.exit(1)



def preview(frame, name="Preview", focus=None, size=700.):
    h,w,d = frame.shape
    ratio = size/max(w,h)
    scaled = cv2.resize(frame,None,fx=ratio, fy=ratio, interpolation = cv2.INTER_CUBIC)
    if focus is not None:
        draw_focus_area(scaled, [int(x*ratio) for x in focus])
    cv2.imshow(name, scaled)
    cv2.waitKey(1)


def warp_matrix0(pers, w,h):
    """
    Warp.  Save the perspective matrix to the file for future use.
     """
    p1 = np.float32([(0,pers[0]*h/1000), (w,pers[1]*h/1000), (0,pers[2]*h/1000), (w,pers[3]*h/1000)])
    #Unskew
    p2 = np.float32([(0, (pers[0]*pers[1])**0.5*h/1000), (w,(pers[0]*pers[1])**0.5*h/1000),
                        (0,(pers[2]*pers[3])**0.5*h/1000), (w,(pers[2]*pers[3])**0.5*h/1000)])
    return cv2.getPerspectiveTransform(p1,p2)






if __name__ == "__main__":
    import sys
    print("It is now useless for a command line tool. Use GUI or pass1.py.")
    sys.exit(1)
    debug = False #True
    guide = False
    seek  = 0
    zero  = False
    pers = None #np.float32([380, 350, 1680, 1715])
    slitpos = 250 # forward; 250/500 of the image width
    slitwidth = 1
    visual = True
    antishake = 5
    trailing = 10
    commandline = " ".join(sys.argv)
    onMemory = True
    dumping = 0
    angle = 0
    every = 1
    identity = 2.0
    assume = None
    margin = 0 # pixels, work in progress.
    #It may be able to unify with antishake.
    focus = np.array((333, 666, 333, 666))
    while len(sys.argv) > 2:
        if sys.argv[1] in ("-2", "--twopass"):
            onMemory  = False
        elif sys.argv[1] in ("-a", "--antishake"):
            antishake = int(sys.argv.pop(2))
        elif sys.argv[1] in ("-A", "--assume"):
            param = sys.argv.pop(2)
            assume = np.float32([float(x) for x in param.split(",")])
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
            pers  = [int(x) for x in param.split(",")]
        elif sys.argv[1] in ("-q", "--quiet"):
            visual = False
        elif sys.argv[1] in ("-r", "--rotate"):
            angle = -float(sys.argv.pop(2)) * math.pi / 180
        elif sys.argv[1] in ("-s", "--slit"):
            slitpos = int(sys.argv.pop(2))
        elif sys.argv[1] in ("-S", "--seek"):
            seek = int(sys.argv.pop(2))
        elif sys.argv[1] in ("-t", "--trail"):
            trailing = int(sys.argv.pop(2))
        elif sys.argv[1] in ("-w", "--width"):
            slitwidth = float(sys.argv.pop(2))
        elif sys.argv[1] in ("-z", "--zero"):
            zero  = True
        elif sys.argv[1][0] == "-":
            print("Unknown option: ", sys.argv[1])
            Usage(sys.argv)
        sys.argv.pop(1)

    if len(sys.argv) != 2:
        Usage(sys.argv)

    movie = sys.argv[1]
    cap = cv2.VideoCapture(movie)
    frames = 0
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
    if not ret:
        sys.exit(0)
    frames += 1
    if angle:
        #Apply rotation
        h, w, d = frame.shape
        R, rw,rh = rotate_matrix(angle, w, h)
        frame = cv2.warpAffine(frame, R, (rw,rh))
    h, w, d = frame.shape
    
    if guide:
        draw_guide(frame, pers)
        draw_focus_area(frame, focus)
        cv2.imshow("Guide lines", frame)
        cv2.waitKey()
        sys.exit(0)

    if pers is not None:
        M = warp_matrix0(pers,w,h)
        frame = cv2.warpPerspective(frame,M,(w,h))
        print(M)
        np.save("{0}.perspective.npy".format(movie), M) #Required to recover the perspective


    #Prepare a scalable canvas with the origin.
    canvas = (frame.copy(), (0, 0))

    if not debug and visual:
        preview(frame, "First frame", focus=focus)
    
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
        if pers is not None:
            nextframe = cv2.warpPerspective(nextframe,M,(w,h))
        diff = cv2.absdiff(nextframe,frame)
        diff = np.sum(diff) / (h*w*3)
        if diff < identity:
            print("skip identical frame #",diff)
            #They are identical frames
            #This happens when the frame rate difference is compensated.
            continue
        if debug:
            preview(nextframe, "Debug", focus=focus)
            
        if margin > 0 and onWork:
            dx0,dy0 = motion(frame, nextframe, focus=focus, margin=margin, delta=(lastdx,lastdy), antishake=antishake )
        else:
            dx0,dy0 = motion(frame, nextframe, focus=focus)
            
        if dumping and onWork:
            dx += (dx0 - lastdx)/dumping + lastdx
            dy += (dy0 - lastdy)/dumping + lastdy
            print(frames,dx,dy,dx0,dy0,"#",np.amax(diff))
        else:
            dx += dx0
            dy += dy0
            print(frames,dx0,dy0,"#",np.amax(diff))

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
                if assume is not None:
                    dx, dy = assume #initial velocity assumption
                    idx,idy = int(dx),int(dy)
                    dx -= idx
                    dy -= idy
            tr = 0
        else:
            if onWork:
                if tr <= trailing:
                    tr += 1
                    idx = lastdx
                    idy = lastdy
                    print(">>({2}) {0} {1} #{3}".format(idx,idy,tr,np.amax(diff)))
                else:
                    #end of work
                    break
        absx += idx
        absy += idy
        if onWork:
            lastdx, lastdy = idx,idy
            alpha = make_vert_alpha( idx, w, h, slitpos, slitwidth )
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

    if pers is not None:
        print(M)

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
    

        
