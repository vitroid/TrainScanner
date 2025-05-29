#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import argparse


def rectify(img, rows=None, gap=3, head_right=True):  # gap in percent
    h, w = img.shape[0:2]

    if rows is not None:
        ww = w // rows
    else:
        rows = 30
        hh = h * rows
        ww = w // rows
        # while hh*2**0.5*(100+gap)/100 < ww:
        while hh * 1.2 * (100 + gap) / 100 > ww:
            rows -= 1
            hh = h * rows
            ww = w // rows

    hg = h * (100 + gap) // 100
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
        description="Fold a train image into a stack of images"
    )
    parser.add_argument("image_path", help="入力画像ファイルのパス")
    parser.add_argument("--output", "-o", help="出力ファイルのパス")
    parser.add_argument("--rows", "-r", type=int, help="行数 -- 2,100")
    parser.add_argument("--gap", "-g", type=int, default=0, help="マージン -- 0,100")
    parser.add_argument("--head-right", "-R", action="store_true", help="右端が先頭")
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    img = cv2.imread(args.image_path)
    canvas = rectify(img, args.rows, args.gap, args.head_right)
    if args.output:
        cv2.imwrite(args.output, canvas)
    else:
        cv2.imwrite(f"{args.image_path}.rect.png", canvas)


if __name__ == "__main__":
    main()
