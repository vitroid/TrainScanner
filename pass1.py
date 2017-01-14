#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import math
import trainscanner
import sys
import os
import re
import myargparse
import itertools
import logging

def draw_focus_area(f, focus, delta=0):
    """
    cv2形式の画像の中に四角を描く．
    """
    h, w = f.shape[0:2]
    pos = [w*focus[0]//1000,w*focus[1]//1000,h*focus[2]//1000,h*focus[3]//1000]
    cv2.rectangle(f, (pos[0],pos[2]),(pos[1],pos[3]), (0, 255, 0), 1)
    if delta != 0:
        pos = [w*focus[0]//1000+delta,w*focus[1]//1000+delta,h*focus[2]//1000,h*focus[3]//1000]
        cv2.rectangle(f, (pos[0],pos[2]),(pos[1],pos[3]), (255, 255, 0), 1)
        


def draw_slit_position(f, slitpos, dx):
    """
    cv2形式の画像の中にスリットマーカーを描く．
    """
    h, w = f.shape[0:2]
    if dx > 0:
        x1 = w//2 + slitpos*w//1000
        x2 = x1 - dx
    else:
        x1 = w//2 - slitpos*w//1000
        x2 = x1 - dx
    cv2.line(f, (x1,0),(x1,h), (0,255,0), 1)
    cv2.line(f, (x2,0),(x2,h), (0,255,0), 1)



def motion(image, ref, focus=(333, 666, 333, 666), maxaccel=0, delta=(0,0), antishake=2):
    """
    ref画像の，focusで指定された領域内の画像と同じ画像を，image内でさがして，その変位を返す．
    maxaccelとdeltaが指定されている場合は，探索範囲を絞り高速にマッチングできる．
    """
    hi,wi = ref.shape[0:2]
    wmin = wi*focus[0]//1000
    wmax = wi*focus[1]//1000
    hmin = hi*focus[2]//1000
    hmax = hi*focus[3]//1000
    template = ref[hmin:hmax,wmin:wmax,:]
    h,w = template.shape[0:2]

    # Apply template Matching
    if maxaccel == 0:
        res = cv2.matchTemplate(image,template,cv2.TM_SQDIFF_NORMED)
        #loc is given by x,y
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        return min_loc[0] - wmin, min_loc[1] - hmin
    else:
        #use delta here
        roix0 = wmin + delta[0] - maxaccel
        roiy0 = hmin + delta[1] - maxaccel
        roix1 = wmax + delta[0] + maxaccel
        roiy1 = hmax + delta[1] + maxaccel
        affine = np.matrix(((1.0,0.0,-roix0),(0.0,1.0,-roiy0)))
        crop = cv2.warpAffine(image, affine, (roix1-roix0,roiy1-roiy0))
        #imageh,imagew = image.shape[0:2]
        #if roix0 < 0 or roix1 >= imagew or roiy0 < 0 or roiy1 >= imageh:
        #    print(roix0,roix1,roiy0,roiy1,imagew,imageh)
        #    return None
        #crop = image[roiy0:roiy1, roix0:roix1, :]
        res = cv2.matchTemplate(crop,template,cv2.TM_SQDIFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        #loc is given by x,y

        #Test: isn't it just a background?
        roix02 = wmin - antishake
        roiy02 = hmin - antishake
        roix12 = wmax + antishake
        roiy12 = hmax + antishake
        crop = image[roiy02:roiy12, roix02:roix12, :]
        res = cv2.matchTemplate(crop,template,cv2.TM_SQDIFF_NORMED)
        min_val2, max_val2, min_loc2, max_loc2 = cv2.minMaxLoc(res)
        #loc is given by x,y
        if min_val <= min_val2:
            return (min_loc[0] + roix0 - wmin, min_loc[1] + roiy0 - hmin)
        else:
            return (min_loc2[0] + roix02 - wmin, min_loc2[1] + roiy02 - hmin)


def diffImage(frame1,frame2,dx,dy,focus=None,slitpos=None):
    """
    2枚のcv2画像の差を返す．
    """
    affine = np.matrix(((1.0,0.0,dx),(0.0,1.0,dy)))
    h,w = frame1.shape[0:2]
    frame1 = cv2.warpAffine(frame1, affine, (w,h))
    diff = 255 - cv2.absdiff(frame1,frame2)
    if focus is not None:
        draw_focus_area(diff, focus, delta=dx)
    if slitpos is not None:
        draw_slit_position(diff, slitpos, dx)
    return diff


#Automatically extensible canvas.
def canvas_size(canvas_dimen, image, x, y):
    """
    canvas_dimenで定義されるcanvasの，位置(x,y)にimageを貼りつけた場合の，拡張後のcanvasの大きさを返す．
    canvas_dimenはcanvasの左上角の絶対座標と，canvasの幅高さの4因子でできている．
    """
    if canvas_dimen is None:
        h,w = image.shape[:2]
        return w,h,x,y
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



def prepare_parser():
    """
    pass1のコマンドラインオプションのパーザ
    """
    parser = myargparse.MyArgumentParser(description='TrainScanner matcher', fromfile_prefix_chars='@',)
    parser.add_argument('-z', '--zero', action='store_true',
                        dest='zero',
                        help="Suppress drift.")
    parser.add_argument('-S', '--skip', '--start', type=int, metavar='N',
                        default=0,
                        dest="skip",
                        help="Skip first N frames.")
    parser.add_argument('-L', '--last', type=int, metavar='N',
                        default=0,
                        dest="last",
                        help="Specify the last frame.")
    parser.add_argument('-E', '--estimate', type=int, metavar='N',
                        default=10,
                        dest="estimate",
                        help="Use first N frames for velocity estimation.")
    parser.add_argument('-p', '--perspective',  #do not allow "--pers"
                        type=int,
                        nargs=4, default=None,
                        dest="perspective",
                        help="Specity perspective warp.")
    parser.add_argument('-f', '--focus', type=int,
                        nargs=4, default=[333,666,333,666],
                        dest="focus", 
                        help="Motion detection area relative to the image size.")
    parser.add_argument('-a', '--antishake', type=int,
                        default=5, metavar="x",
                        dest="antishake",
                        help="Antishake.  Ignore motion smaller than x pixels.")
    parser.add_argument('-t', '--trail', type=int,
                        default=10,
                        dest="trailing",
                        help="Trailing frames after the train runs away.")
    parser.add_argument('-r', '--rotate', type=int,
                        default=0,
                        dest="rotate",
                        help="Image rotation.")
    parser.add_argument('-e', '--every', type=int,
                        default=1,
                        dest="every", metavar="N",
                        help="Load every N frames.")
    parser.add_argument('-i', '--identity', type=float,
                        default=1.0,
                        dest="identity", metavar="x",
                        help="Decide the identity of two successive frames with the threshold.")
    parser.add_argument('-c', '--crop', type=int,
                        nargs=2, default=[0,1000],
                        dest="crop", metavar="t,b",
                        help="Crop the image (top and bottom).")
    parser.add_argument('-x', '--stall', action='store_true',
                        dest="stall", default=False,
                        help="Train is initially stopping inside the motion detection area.")
    parser.add_argument('-m', '--maxaccel', type=int,
                        default=1,
                        dest="maxaccel", metavar="N",
                        help="Interframe acceleration in pixels.")
    parser.add_argument('-2', '--option2', type=str,
                        action='append',
                        dest="option2",
                        help="Additional option (just ignored in this program).")
    parser.add_argument('-l', '--log', type=str,
                        dest='log', default=None,
                        help="TrainScanner settings (.tsconf) file name.")
    parser.add_argument('filename', type=str,
                        help="Movie file name.")
    return parser


                
            
class Pass1():
    """
    ムービーを前から読んで，最終的なキャンバスの大きさと，各フレームを貼りつける位置を調べて，tsposファイルに書きだす．
    実際に大きな画像を作る作業はstitch.pyにまかせる．
    """
    def __init__(self,argv):
        logger = logging.getLogger()
        self.parser = prepare_parser()
        self.params, unknown = self.parser.parse_known_args(argv[1:])
        #Assume the video is in the same dir.
        self.dirnames = []
        if self.parser.fromfile_name is not None:
            logger.debug("Conf filename {0}".format(self.parser.fromfile_name))
            self.dirnames.append(os.path.dirname(self.parser.fromfile_name))
        self.dirnames.append(os.path.dirname(self.params.filename))
        #remove the dirname from the filename
        self.params.filename = os.path.basename(self.params.filename)
        logger.debug("Directory candidates: {0}".format(self.dirnames))
        
        
        
    def before(self):
        """
        prepare for the loop
        note that it is a generator.
        """
        logger = logging.getLogger()
        ####Determine the movie file########################
        found = None
        logger.debug("Basename {0}".format(self.params.filename))
        # First we assume that the movie is in the same directory as tsconf if tsconf is specified.
        # Otherwise we look at the absolute path given in the command line or in the tsconf.
        for dirname in self.dirnames:
            filename = dirname+"/"+self.params.filename
            if os.path.exists(filename):
                found = filename
                break
        if not found:
            logger.error("File not found.")
        #update the file path
        self.params.filename = found
        logger.debug("Found filename {0}".format(found))
        ####prepare tsconf file#############################
        self.tsconf   = ""
        args = trainscanner.deparse(self.parser,self.params)
        self.tsconf += "{0}\n".format(args["__UNNAMED__"])
        for option in args:
            value = args[option]
            if value is None or option in ("__UNNAMED__"):
                continue
            if option == '--option2':
                #Expand "key=value" to "--key\tvalue\n"
                for v in value:
                    equal = v.find("=")
                    if equal >= 0:
                        self.tsconf += "--{0}\n{1}\n".format(v[:equal],v[equal+1:])
                    else:
                        self.tsconf += "--{0}\n".format(v)
            else:
                if option in ("--perspective", "--focus", "--crop", ):  #multiple values
                    self.tsconf += "{0}\n".format(option)
                    for v in value:
                        self.tsconf += "{0}\n".format(v)
                elif option in ("--zero", "--stall", "--helix", "--film", "--rect"):
                    if value is True:
                        self.tsconf += option+"\n"
                else:
                    self.tsconf += "{0}\n{1}\n".format(option,value)
        #print(self.tsconf)
        #end of the header

        #############Open the video file #############################
        self.cap    = cv2.VideoCapture(found)
        self.tspos   = ""

        self.nframes = 0  #1 is the first frame
        self.cache   = [] #save only "active" frames.
        self.deltax  = [] #store displacements
        self.deltay  = [] #store displacements
        #This does not work with some kind of MOV. (really?)
        #self.cap.set(cv2.CAP_PROP_POS_FRAMES, skip)
        #self.nframes = skip
        #ret, frame = self.cap.read()
        #if not ret:
        self.nframes = 0
    
        for i in range(self.params.skip):  #skip frames
            ret = self.cap.grab()
            if not ret:
                break
            self.nframes += 1
            yield self.nframes, self.params.skip #report progress
        ret, frame = self.cap.read()
        if not ret:
            sys.exit(0)
        self.nframes += 1    #first frame is 1
        self.rawframe = frame
        
        self.transform = trainscanner.transformation(angle=self.params.rotate, pers=self.params.perspective, crop=self.params.crop)
        rotated, warped, cropped = self.transform.process_first_image(self.rawframe)
        self.frame = cropped
        #Prepare a scalable canvas with the origin.
        self.canvas = None
        
        self.absx,self.absy = 0, 0
        self.velx, self.vely = 0.0, 0.0
        self.match_fail = 0
        if self.params.stall:
            #estimation must be on by default.
            self.guess_mode = True
        else:
            #we cannot estimate the run-in velocity
            #so the estimateion is off by default.
            self.guess_mode = False
        self.precount = 0
        self.preview_size = 500
        self.preview = trainscanner.fit_to_square(self.frame, self.preview_size)
        self.preview_ratio = self.preview.shape[0] / self.frame.shape[0]
        yield self.nframes, self.params.skip

        
    def after(self):
        """
        Action after the loop
        """
        if self.canvas is None:
            return
        self.tsconf += "--canvas\n{0}\n{1}\n{2}\n{3}\n".format(*self.canvas)
        if self.params.log is None:
            ostream = sys.stdout
        else:
            ostream = open(self.params.log+".tsconf", "w")
        ostream.write(self.tsconf)
        if self.params.log is not None:
            ostream = open(self.params.log+".tspos", "w")
        ostream.write(self.tspos)
        ostream.close()

        self.rawframe = None
        self.frame    = None
        self.canvas   = None
        

    def backward_match(self, velx,vely):
        """
        using cached images,
        "postdict" the displacements
        Do not break the cache. It will be used again.
        """
        logger = logging.getLogger()
        curFrameNum, curFrameImg = self.cache.pop(-1)
        prevFrameNum = -1 
        curFrameAbsX = self.absx
        curFrameAbsY = self.absy
        newDeltas = []
        for i in range(self.precount + self.params.trailing):
            logger.debug("Rewinding {0} {1} {2}".format(i,self.precount+self.params.trailing,len(self.cache)))
            if len(self.cache) == 0:
                break
            prevFrameNum,prevFrameImg = self.cache.pop(-1)
            d = motion(prevFrameImg, curFrameImg, focus=self.params.focus, maxaccel=self.params.maxaccel, delta=(velx, vely))
            if d is None:
                dx = 0
                dy = 0
            else:
                dx,dy = d
            if self.params.zero:
                dy = 0
            if abs(dx) > self.params.antishake or abs(dy) > self.params.antishake:
                velx = dx
                vely = dy
            newDeltas = [[prevFrameNum, velx, vely]] + newDeltas
            curFrameAbsX -= velx
            curFrameAbsY -= vely
            self.canvas = canvas_size(self.canvas, curFrameImg, curFrameAbsX, curFrameAbsY)
            logger.info("Rewind {0} {1} {2}".format(prevFrameNum,velx, vely))
            curFrameImg = prevFrameImg
            curFrameNum = prevFrameNum
        #dispose cache
        self.cache = None #Dispose image cache.
        logger.debug("Disposed the image cache.")
        
        #trick; by the backward matching, the first frame may not be located at the origin
        #So the first frame is specified by the abs coord.
        if prevFrameNum < 0:
            return ""
        newDeltas = [[prevFrameNum, curFrameAbsX, curFrameAbsY]] + newDeltas
        s = ""
        for delta in newDeltas:
            s += "{0} {1} {2}\n".format(*delta)
        return s
                  
    def onestep(self):
        logger = logging.getLogger()
        ret = True
        ##### Pick up every x frame
        if self.params.skip < self.params.last < self.nframes + self.params.every:
            return None
        for i in range(self.params.every-1):
            ret = self.cap.grab()
            self.nframes += 1
            if not ret:
                logger.debug("Video ended (1).")
                return None
        ret, nextframe = self.cap.read()
        self.nframes += 1
        ##### return None if the frame is empty
        if not ret:
            logger.debug("Video ended (2).")
            return None
        ##### compare with the previous raw frame
        diff = cv2.absdiff(nextframe,self.rawframe)
        ##### preserve the raw frame for next comparison.
        self.rawframe = nextframe.copy()
        diff = np.sum(diff) / np.product(diff.shape)
        if diff < self.params.identity:
            logger.info("skip identical frame #{0}".format(diff))
            #They are identical frames
            #This happens when the frame rate difference is compensated.
            return True
        ##### Warping the frame
        rotated, warped, cropped = self.transform.process_next_image(nextframe)
        nextframe = cropped
        ##### Make the preview image
        nextpreview = trainscanner.fit_to_square(nextframe,self.preview_size)
        ##### motion detection.
        #if maxaccel is set, motion detection area becomes very narrow
        #assuming that the train is running at constant speed.
        #This mode is activated after the 10th frames.

        #Now I do care only magrin case.
        if self.guess_mode:
            #do not apply maxaccel for the first 10 frames
            #because the velocity uncertainty.
            delta = motion(self.frame, nextframe, focus=self.params.focus, maxaccel=self.params.maxaccel, delta=(self.velx,self.vely))
            if delta is None:
                logger.error("Matching failed (probabily the motion detection window goes out of the image).")
                return None
            dx,dy = delta
        else:
            dx,dy = motion(self.frame, nextframe, focus=self.params.focus)
            
        ##### Suppress drifting.
        if self.params.zero:
            dy = 0
        #record anyway.
        self.deltax.append(dx)
        self.deltay.append(dy)
        if len(self.deltax) > 5:  #keep only 5 frames
            self.deltax.pop(0)
            self.deltay.pop(0)
        if nextframe is not None and self.cache is not None:
            self.cache.append([self.nframes, nextframe])
            if len(self.cache) > 100: #always keep 100 frames in cache
                self.cache.pop(0)
        diff_img = diffImage(nextpreview,self.preview,int(dx*self.preview_ratio),int(dy*self.preview_ratio),focus=self.params.focus)
        ##### if the motion is very small
        if not self.guess_mode:
            if (abs(dx) >= self.params.antishake or abs(dy) >= self.params.antishake):
                self.precount += 1 #number of frames since the first motion is detected.
                ddx = max(self.deltax) - min(self.deltax)
                ddy = max(self.deltay) - min(self.deltay)
                #if the displacements are almost constant in the last 3 frames,
                if ddx < self.params.antishake and ddy < self.params.antishake:
                    self.guess_mode = True
                    self.tspos = self.backward_match(dx,dy)
                    self.velx = dx
                    self.vely = dy
                    self.match_fail = 0
            if not self.guess_mode:
                logger.info("Wait ({0} {1} {2})".format(self.nframes,dx,dy))
                self.frame   = nextframe
                self.preview = nextpreview
                return diff_img
        if (abs(dx) < self.params.antishake and abs(dy) < self.params.antishake):
            ##### accumulate the motion
            ##### wait until motion becomes enough.
            self.match_fail += 1
            if self.match_fail <= self.params.trailing:
                logger.info("Skip ({0} {1} {2} +{3}/{4})".format(self.nframes,dx,dy,self.match_fail, self.params.trailing))
                # do not update the velx and vely
                #but update the frame and preview
                #self.frame   = nextframe
                #self.preview = nextpreview
                #return diff_img
            else:
                #end of work
                #Add trailing frames to the log file here.
                return None
        else:
            self.velx = dx
            self.vely = dy
            self.match_fail = 0
        logger.info("Scan {0} {2} {3} #{1}".format(self.nframes,np.amax(diff), self.velx, self.vely))
        self.absx += self.velx
        self.absy += self.vely
        self.canvas = canvas_size(self.canvas, nextframe, self.absx, self.absy)
        self.tspos += "{0} {3} {4}\n".format(self.nframes,self.absx,self.absy,self.velx,self.vely)
        self.frame   = nextframe
        self.preview = nextpreview
        return diff_img


if __name__ == "__main__":
    debug =True
    if debug:
        logging.basicConfig(level=logging.DEBUG,
                            #filename='log.txt',
                            format="%(asctime)s %(levelname)s %(message)s")
    else:
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")
    pass1 = Pass1(argv=sys.argv)
    for num, den in pass1.before():
        pass
    while True:
        ret = pass1.onestep()
        if ret is None:
            break
        if ret is not True: #True means skipping
            cv2.imshow("pass1", ret)
            cv2.waitKey(1)
    pass1.after()
