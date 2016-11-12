#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, division
import cv2
import numpy as np
import sys
import math

def put_image(canvas, origin, image, xoffset=0):
    h,w = canvas.shape[:2]
    xremain = w - origin[0]
    ih,iw = image.shape[:2]
    ixremain = iw - xoffset
    if xremain > ixremain:
        canvas[origin[1]:origin[1]+ih, origin[0]:origin[0]+ixremain] = image[0:ih, xoffset:xoffset+ixremain]
        return origin[0]+ixremain, origin[1]
    canvas[origin[1]:origin[1]+ih, origin[0]:origin[0]+xremain] = image[0:ih, xoffset:xoffset+xremain]
    return put_image(canvas, (0, origin[1]+ih), image, xoffset+xremain)


if __name__ == "__main__":
    images = []
    hcommon = int(sys.argv.pop(1))
    rows    = int(sys.argv.pop(1))
    total_width = 0
    for name in sys.argv[1:]:
        image = cv2.imread(name)
        h,w = image.shape[:2]
        if hcommon == 0:
            hcommon = h
        ratio = h/hcommon
        rw    = int(w/ratio)
        total_width += rw
        images.append((name,w,h,ratio))
    print("Estimated canvas size:",total_width//rows+1, hcommon*rows)
    canvas = np.zeros( (hcommon*rows, total_width//rows+1, 3), np.uint8 )
    origin = (0,0)
    for name,w,h,ratio in images:
        image = cv2.imread(name)
        scaled = cv2.resize(image,(int(w/ratio), int(h/ratio)),
                                interpolation = cv2.INTER_CUBIC)
        origin = put_image(canvas, origin, scaled)
    cv2.imwrite("hans2.jpg", canvas)
    
