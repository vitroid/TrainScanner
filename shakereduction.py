#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import sys
import argparse
import logging

import pass1



def prepare_parser():
    parser = argparse.ArgumentParser(description='Shake reduction', fromfile_prefix_chars='@',)
    parser.add_argument('-S', '--skip', type=int, metavar='N',
                        default=0,
                        dest="skip",
                        help="Skip first N frames.")
    parser.add_argument('-L', '--last', type=int, metavar='N',
                        default=0,
                        dest="last",
                        help="Specify the last frame.")
    parser.add_argument('-f', '--focus', type=int,
                        nargs=4, default=[200,800,166,333],
                        dest="focus", 
                        help="Motion detection area relative to the image size.")
    parser.add_argument('--crop', type=int,
                        nargs=4, default=[0,1000,0,1000],
                        dest="crop", 
                        help="Frame cropping.")
    parser.add_argument('-m', '--maxaccel', type=int,
                        default=1,
                        dest="maxaccel", metavar="N",
                        help="Interframe acceleration in pixels.")
    parser.add_argument('filename', type=str,
                        help="Movie file name.")
    return parser


                
class ShakeReduction():
    def __init__(self,argv):
        self.parser = prepare_parser()
        self.params, unknown = self.parser.parse_known_args(argv[1:])

        self.cap    = cv2.VideoCapture(self.params.filename)

    def fastforward(self):
        self.nframe = 1
        last = 0
        for i in range(self.params.skip):  #skip frames
            ret = self.cap.grab()
            self.nframe += 1
            if self.nframe * 100 // self.params.skip != last:
                last = self.nframe * 100 // self.params.skip
                yield last
            if not ret:
                break
        ret, self.frame0 = self.cap.read()
        self.nframe += 1
        if not ret:
            sys.exit(0)

    
    def onestep(self):
        logger = logging.getLogger()
        h,w = self.frame0.shape[0:2]
        crop = [self.params.crop[0]*w//1000,
                self.params.crop[1]*w//1000,
                self.params.crop[2]*h//1000,
                self.params.crop[3]*h//1000]
        wc = crop[1] - crop[0]
        hc = crop[3] - crop[2]
        out   =  cv2.VideoWriter(self.params.filename+".sr.m4v",cv2.VideoWriter_fourcc('m','p','4','v'), 30, (wc,hc))
        cropped = self.frame0[crop[2]:crop[3],
                              crop[0]:crop[1], :]
        out.write(cropped)

        dx = 0
        dy = 0
        while True:
            ret, newframe = self.cap.read()
            self.nframe += 1
            if not ret:
                return
            d = pass1.motion(newframe, self.frame0, focus=self.params.focus, maxaccel=self.params.maxaccel, delta=(dx,dy))
            if d is not None:
                dx, dy = d
            logger.info("{2} Delta: {0} {1}".format(dx,dy, self.nframe))
            affine = np.matrix(((1.0,0.0,-dx),(0.0,1.0,-dy)))
            h,w = self.frame0.shape[0:2]
            cv2.warpAffine(newframe, affine, (w,h), newframe)
            cropped = newframe[crop[2]:crop[3],
                               crop[0]:crop[1], :]
            out.write(cropped)
            yield newframe
        
if __name__ == "__main__":
    debug =True
    if debug:
        logging.basicConfig(level=logging.DEBUG,
                            #filename='log.txt',
                            format="%(asctime)s %(levelname)s %(message)s")
    else:
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")
    shaker = ShakeReduction(argv=sys.argv)
    for progress in shaker.fastforward():
        logging.getLogger().debug("Progress {0}".format(progress))
    for frame in shaker.onestep():
        h,w = frame.shape[0:2]
        ratio = 700/max(w,h)
        if ratio < 1.0:
            frame = cv2.resize(frame, None, fx=ratio, fy=ratio)
        pass1.draw_focus_area(frame, shaker.params.focus)
        crop = [shaker.params.crop[0]*w//1000,
                shaker.params.crop[1]*w//1000,
                shaker.params.crop[2]*h//1000,
                shaker.params.crop[3]*h//1000]
        cropped = frame[crop[2]:crop[3],
                        crop[0]:crop[1], :]
        cv2.imshow("shakeR", cropped)
        cv2.waitKey(1)

