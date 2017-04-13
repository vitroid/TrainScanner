#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cv2
import numpy as np
import math
import sys

def roundbox(img,p1,p2,r,color):
    cv2.circle(img,(p1[0]+r,p1[1]+r),r,color,-1)
    cv2.circle(img,(p2[0]-r,p1[1]+r),r,color,-1)
    cv2.circle(img,(p1[0]+r,p2[1]-r),r,color,-1)
    cv2.circle(img,(p2[0]-r,p2[1]-r),r,color,-1)
    cv2.rectangle(img,(p1[0],p1[1]+r),(p2[0],p2[1]-r),color,-1)
    cv2.rectangle(img,(p1[0]+r,p1[1]),(p2[0]-r,p2[1]),color,-1)


if len(sys.argv) != 2:
    print("usage: {0} image".format(sys.argv[0]))
    sys.exit(1)

img = cv2.imread(sys.argv[1])

h, w = img.shape[0:2]

inst = cv2.imread("instruction/instruction.png")
ih, iw = inst.shape[0:2]

ratio = float(h)/ih
scaled = cv2.resize(inst,None,fx=ratio, fy=ratio, interpolation = cv2.INTER_CUBIC)

sh,sw = scaled.shape[0:2]
if sh > h:
    sh = h
canvas = np.zeros((h, w+sw, 3), np.uint8)
canvas[0:h,0:w] = img
canvas[0:sh,w:w+sw] = scaled

cv2.imwrite("{0}.inst.png".format(sys.argv[1]), canvas)

