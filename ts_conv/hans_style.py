#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import math
import sys





def main():
    if len(sys.argv) <2:
        print("usage: {0} image rows".format(sys.argv[0]))
        sys.exit(1)

    img = cv2.imread(sys.argv[1])
    h, w = img.shape[0:2]

    if len(sys.argv) == 3:
        rows = int(sys.argv[2])
    else:
        rows = 1
        hh = h
        ww = w
        while hh*2**0.5 < ww:
            rows += 1
            hh = h * rows
            ww = w / rows

    neww = w/rows
    thumb = cv2.resize(img,(w/rows,h/rows), interpolation = cv2.INTER_CUBIC)
    thh, thw = thumb.shape[0:2]
    canvas = np.zeros((h*rows+h/rows,neww,3))
    canvas[0:thh, 0:thw, :] = thumb
    for i in range(rows):
        canvas[thh+i*h:thh+(i+1)*h, 0:neww, :] = img[:,i*neww:(i+1)*neww,:]
    cv2.imwrite("{0}.hans.jpg".format(sys.argv[1]), canvas)

if __name__ == "__main__":
    main()
