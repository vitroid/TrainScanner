#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import math
import sys
import argparse


def hansify(img, rows=3, overlap=10):
    """
    Hans Ruijter's style
    """
    h, w = img.shape[0:2]

    hh = h * rows
    #====+         ww1 = ww + A
    #   +====+     ww  = ww
    #       +===== ww1 = ww + A
    #ww1 + (rows-2)*ww + ww1 = = ww*rows+2A = w
    #ww*overlap/100 = A
    #So, ww*(rows+overlap/50) = w
    ww = int(w / (rows + overlap/50))
    A  = ww*overlap // 100

    neww = ww + 2*A
    thh = h*neww//w
    thumb = cv2.resize(img,(neww,thh), interpolation = cv2.INTER_CUBIC)
    #thh, thw = thumb.shape[0:2]
    canvas = np.zeros((hh+thh, neww,3),dtype=np.uint8)
    canvas[0:thh, 0:neww, :] = thumb
    for i in range(0,rows):
        canvas[thh+i*h:thh+(i+1)*h, 0:neww, :] = img[:,i*ww:(i+1)*ww+2*A,:]
    return canvas


def prepare_parser():
    parser = argparse.ArgumentParser(description='Helicify', fromfile_prefix_chars='@',)
    parser.add_argument('-l', '--overlap', type=int, metavar='x',
                        default=5,
                        dest="overlap",
                        help="Overlaps between rows in percent.")
    parser.add_argument('-r', '--rows', type=int, metavar='x',
                        default=3,
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
    canvas = hansify(img, params.rows, overlap=params.overlap)
    if params.output == "":
        cv2.imwrite("{0}.hans.jpg".format(params.filename), canvas)
    else:
        cv2.imwrite(params.output, canvas)
    
if __name__ == "__main__":
    main()
