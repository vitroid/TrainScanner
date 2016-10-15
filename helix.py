#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cv2
import numpy as np
import math

import sys

#Determine tilt angle by Newton-Raphson method
#assuming that the aspect ratio is sqrt(2):1
#The final image size should be px:py = sqrt(2):1
#where px = h / sin(theta)
#and   py = w sin(theta) + h cos(theta)
def rn_sine(w,h):
    def f(t):
        return 2**0.5 *(w*t**2+h*t*(1-t**2)**0.5) - h
    def df(t):
        return 2**0.5 *(2*w*t+h*(1-t**2)**0.5-h*t**2/(1-t**2)**0.5)
    t = 0
    for i in range(10):
        t = t - f(t)/df(t)
    return t




def helicify(img):
    """
    Helicify and project on a A-size paper proportion.
    Note: it fails when the strip is too short.
    """
    h, w = img.shape[0:2]
    #height with a gap
    hg = int(h*1.03)

    sine = rn_sine(w,hg)
    cosine = (1 - sine**2)**0.5
    px = hg / sine
    py = w*sine + hg*cosine

    N = (w - px*2*cosine) * cosine / px + 2
    N = int(math.ceil(N))

    row = int(px / cosine)
    row0 = int(hg * sine / cosine)
    xofs = int(hg*sine)

    canw = row+row0*(N-1)
    canh = hg*N

    padx = int(hg*sine)
    pady = int(px*sine)

    canvas = np.zeros((canh+pady*2, canw+padx,3), np.uint8)
    canvas[:,:,:] =255
    for i in range(1,N-1):
        canvas[i*hg+pady:i*hg+h+pady, padx:canw+padx, :] = img[0:h, i*(row - row0): i*(row-row0) + canw, :]
    canvas[pady:h+pady, padx:canw+padx, :] = img[0:h, 0:canw, :]
    residue = w - (row-row0)*(N-1)
    canvas[(N-1)*hg+pady:(N-1)*hg+h+pady, padx:residue+padx, :] = img[0:h, w-residue:w, :]
    a = cosine
    b = -sine
    cx = padx
    cy = pady

    R = np.matrix(((a,b,(1-a)*cx - b*cy),(-b,a,b*cx+(1-a)*cy)))
    canvas = cv2.warpAffine(canvas, R, (int(canw+padx),int(canh+pady*2)))
    canvas2 = np.zeros((int(py),int(px),3), np.uint8)
    canvas2[:,:,:] = canvas[pady:pady+int(py), padx-xofs:padx-xofs+int(px), :]

    return canvas2

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "usage: {0} image".format(sys.argv[0])
        sys.exit(1)
    img = cv2.imread(sys.argv[1])
    canvas2 = helicify(img)
    cv2.imwrite("{0}.helix.jpg".format(sys.argv[1]), canvas2)



