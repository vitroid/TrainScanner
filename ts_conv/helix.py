#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import math
import argparse
import sys

#Determine tilt angle by Newton-Raphson method
#assuming that the aspect ratio is a:1
#The final image size should be px:py = a:1
#where px = h / sin(theta)
#and   py = w sin(theta) + h cos(theta)
#what we want is t = sin(theta) to satisfy the equations.
#So,
#h / t - a * (w * t + h*cos(theta))
#a t (wt + h cos(theta)) - h == 0 = f(t)
#a (wtt + h t sqrt(1-tt)) - h == 0 = f(t)
#f'(t) = a ( 2wt + ht sqrt() + ht .....
def rn_sine(w,h, aspect=2.0**0.5):
    def f(t):
        return aspect *(w*t**2+h*t*(1-t**2)**0.5) - h
    def df(t):
        return aspect *(2*w*t+h*(1-t**2)**0.5-h*t**2/(1-t**2)**0.5)
    t = 0.5
    for i in range(10):
        t = t - f(t)/df(t)
    return t




def helicify(img, aspect=2.0**0.5):
    """
    Helicify and project on a A-size paper proportion.
    Note: it fails when the strip is too short.
    """
    h, w = img.shape[0:2]
    #height with a gap
    hg = int(h*1.03)

    sine = rn_sine(w,hg,aspect=aspect)
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
        x0 = i*(row-row0)
        #print(padx,canw,x0+canw,img.shape)
        if img.shape[1] <= x0 + canw:
            ww = img.shape[1] - x0
        else:
            ww = canw
        canvas[i*hg+pady:i*hg+h+pady, padx:padx+ww, :] = img[0:h, x0:x0+ww, :]
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


def add_margin(img, margin):
    h,w = img.shape[:2]
    if h > w:
        m = int(h*margin/100)
    else:
        m = int(w*margin/100)
    canvas2 = np.zeros((h+m*2,w+m*2,3), np.uint8)
    canvas2[:,:,:] = 255
    canvas2[m:m+h, m:m+w, :] = img[:,:,:]
    return canvas2
    


def prepare_parser():
    parser = argparse.ArgumentParser(description='Helicify', fromfile_prefix_chars='@',)
    parser.add_argument('-m', '--margin', type=float, metavar='x',
                        default=0,
                        dest="margin",
                        help="Add margin of x %% of the wider edge around the image.")
    parser.add_argument('-a', '--aspect', type=float, metavar='x',
                        default=2.0**0.5,
                        dest="aspect",
                        help="Specify the aspect ratio (default=1.414).")
    parser.add_argument('-o', '--output', type=str, metavar='outfilename',
                        default="",
                        dest="output",
                        help="Output file name.")
    parser.add_argument('filename', type=str,
                        help="Image file name.")
    return parser


def main():
    parser = prepare_parser()
    params = parser.parse_args(sys.argv[1:])
    print(params.filename)
    img = cv2.imread(params.filename)
    canvas2 = helicify(img, aspect=params.aspect)
    if params.margin != 0:
        canvas2 = add_margin(canvas2, params.margin)
    if params.output == "":
        cv2.imwrite("{0}.helix.jpg".format(params.filename), canvas2)
    else:
        cv2.imwrite(params.output, canvas2)


if __name__ == "__main__":
    main()
