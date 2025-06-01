#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import argparse
from trainscanner.i18n import tr


def rectify(img, rows=None, overlap=3, head_right=True):  # overlap in percent
    h, w = img.shape[0:2]

    if rows is not None:
        ww = w // rows
    else:
        rows = 30
        hh = h * rows
        ww = w // rows
        # while hh*2**0.5*(100+gap)/100 < ww:
        while hh * 1.2 * (100 + overlap) / 100 > ww:
            rows -= 1
            hh = h * rows
            ww = w // rows

    hg = h * (100 + overlap) // 100
    canvas = np.zeros((hg * rows, ww, 3))
    canvas[:, :, :] = 255  # white
    for i in range(rows):
        if head_right:
            ws = (rows - i - 1) * ww
            we = (rows - i) * ww
        else:
            ws = i * ww
            we = (i + 1) * ww
        if w < we:
            we = w
        canvas[i * hg : i * hg + h, 0:, :] = img[:, ws:we, :]
    return canvas


def get_parser():
    """
    コマンドライン引数のパーサーを生成して返す関数
    """
    parser = argparse.ArgumentParser(
        description=tr("Fold a train image into a stack of images")
    )
    parser.add_argument("image_path", help=tr("Path of the input image file"))
    parser.add_argument("--output", "-o", help=tr("Path of the output file"))
    parser.add_argument(
        "--rows", "-r", type=int, help=tr("Number of rows") + "-- 2,100"
    )
    parser.add_argument(
        "--overlap",
        "-l",
        type=int,
        default=0,
        help=tr("Overlap (percent)") + "-- 0,100",
    )
    parser.add_argument(
        "--head-right",
        "-R",
        action="store_true",
        help=tr("The train heads to the right."),
    )
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    img = cv2.imread(args.image_path)
    canvas = rectify(img, args.rows, args.overlap, args.head_right)
    if args.output:
        cv2.imwrite(args.output, canvas)
    else:
        cv2.imwrite(f"{args.image_path}.rect.png", canvas)


if __name__ == "__main__":
    main()
