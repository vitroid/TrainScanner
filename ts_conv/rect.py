#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import math
import sys
import argparse


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


def prepare_parser():
    parser = argparse.ArgumentParser(description='Helicify', fromfile_prefix_chars='@',)
    parser.add_argument('-g', '--gap', type=int, metavar='x',
                        default=0,
                        dest="gap",
                        help="Add gaps of x %% between the rows.")
    parser.add_argument('-r', '--rows', type=int, metavar='x',
                        default=None,
                        dest="rows",
                        help="Number of rows.")
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
    canvas = rectify(img, params.rows, gap=params.gap)
    if params.output == "":
        cv2.imwrite("{0}.rect.jpg".format(params.filename), canvas)
    else:
        cv2.imwrite(params.output, canvas)
    
if __name__ == "__main__":
    main()
