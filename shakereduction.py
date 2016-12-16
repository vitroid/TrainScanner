#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import math
import trainscanner
import sys
import re
import argparse
import itertools
import pass1



def prepare_parser():
    parser = argparse.ArgumentParser(description='TrainScanner matcher', fromfile_prefix_chars='@',)
    parser.add_argument('-S', '--skip', type=int, metavar='N',
                        default=0,
                        dest="skip",
                        help="Skip first N frames.")
    parser.add_argument('-f', '--focus', type=int,
                        nargs=4, default=[333,666,333,666],
                        dest="focus", 
                        help="Motion detection area relative to the image size.")
    parser.add_argument('-m', '--maxaccel', type=int,
                        default=1,
                        dest="maxaccel", metavar="N",
                        help="Interframe acceleration in pixels.")
    parser.add_argument('-t', '--trail', type=int,
                        default=10,
                        dest="trailing",
                        help="Trailing frames after the train runs away.")
    parser.add_argument('filename', type=str,
                        help="Movie file name.")
    return parser


                
class ShakeReduction():
    def __init__(self,argv):
        self.parser = prepare_parser()
        self.params, unknown = self.parser.parse_known_args(argv[1:])

        self.cap    = cv2.VideoCapture(self.params.filename)
        for i in range(self.params.skip):  #skip frames
            ret = self.cap.grab()
            if not ret:
                break
        ret, self.frame = self.cap.read()
        if not ret:
            sys.exit(0)
        h,w = self.frame.shape[0:2]
        self.out   =  cv2.VideoWriter(self.params.filename+".sr.m4v",cv2.VideoWriter_fourcc('m','p','4','v'), 30, (w,h))
        self.out.write(self.frame)
        cv2.imshow("first", self.frame)
        cv2.waitKey(1)
        self.dx = 0
        self.dy = 0
    def onestep(self):
        ret, newframe = self.cap.read()
        if not ret:
            return False
        d = pass1.motion(newframe, self.frame, focus=self.params.focus, maxaccel=self.params.maxaccel, delta=(self.dx,self.dy))
        if d is not None:
            self.dx, self.dy = d
        affine = np.matrix(((1.0,0.0,-self.dx),(0.0,1.0,-self.dy)))
        h,w = self.frame.shape[0:2]
        cv2.warpAffine(newframe, affine, (w,h), newframe)
        pass1.draw_focus_area(newframe, self.params.focus)
        self.out.write(newframe)
        cv2.imshow("shakeR", newframe)
        cv2.waitKey(1)
        return True

if __name__ == "__main__":
    shaker = ShakeReduction(argv=sys.argv)
    while shaker.onestep():
        pass
