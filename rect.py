#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import math
import sys



def rectify(img, rows=None, gap=3 ): #gap in percent
    h, w = img.shape[0:2]

    if rows is not None:
        ww = w // rows
    else:
        rows = 30
        hh = h * rows
        ww = w // rows
        #while hh*2**0.5*(100+gap)/100 < ww:
        while hh*1.2*(100+gap)/100 > ww:
            rows -= 1
            hh = h * rows
            ww = w // rows

    hg = h*(100+gap)//100
    canvas = np.zeros((hg*rows,ww,3))
    canvas[:,:,:] = 255  #white
    for i in range(rows):
        we = (i+1)*ww
        if w < we:
            we = w
        canvas[i*hg:i*hg+h, 0:, :] = img[:,i*ww:we,:]
    return canvas

if __name__ == "__main__":
    if len(sys.argv) <2:
        print("usage: {0} image rows".format(sys.argv[0]))
        sys.exit(1)

    img = cv2.imread(sys.argv[1])
    if len(sys.argv)==3:
        canvas = rectify(img, int(sys.argv[2]))
    else:
        canvas = rectify(img)
    cv2.imwrite("{0}.rect.jpg".format(sys.argv[1]), canvas)
    
