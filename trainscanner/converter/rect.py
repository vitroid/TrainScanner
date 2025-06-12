#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import argparse
from trainscanner.i18n import tr, init_translations
import logging
import os


def convert(
    img, head_right=True, aspect=2**0.5, overlap=10, width=0, thumbnail=False, **kwargs
):
    """
    Hans Ruijter's style
    """
    logger = logging.getLogger()
    logger.debug(f"Ignored options: {kwargs}")
    h, w = img.shape[:2]

    a = [999]
    for rows in range(1, 100):

        hh = h * rows
        # ====+         ww1 = ww + A
        #   +====+     ww  = ww
        #       +===== ww1 = ww + A
        # ww1 + (rows-2)*ww + ww1 = = ww*rows+2A = w
        # ww*overlap/100 = A
        # So, ww*(rows+overlap/50) = w

        ww = int(w / (rows + overlap / 50))
        a.append(np.abs(ww / hh - aspect))

    rows = np.argmin(a)

    hh = h * rows
    ww = int(w / (rows + overlap / 50))

    A = ww * overlap // 100

    neww = ww + 2 * A
    if thumbnail:
        thh = h * neww // w
        thumb = cv2.resize(img, (neww, thh), interpolation=cv2.INTER_CUBIC)
    else:
        thh = 0
        thumb = None
    # thh, thw = thumb.shape[0:2]
    canvas = np.zeros((hh + thh, neww, 3), dtype=np.uint8)
    if thumbnail:
        canvas[0:thh, 0:neww, :] = thumb
    for i in range(0, rows):
        if head_right:
            canvas[thh + (rows - i - 1) * h : thh + (rows - i) * h, 0:neww, :] = img[
                :, i * ww : (i + 1) * ww + 2 * A, :
            ]
        else:
            canvas[thh + i * h : thh + (i + 1) * h, 0:neww, :] = img[
                :, i * ww : (i + 1) * ww + 2 * A, :
            ]
    if width > 0:
        height = int((hh + thh) / neww * width)
        return cv2.resize(canvas, (width, height), interpolation=cv2.INTER_CUBIC)
    else:
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
        "--aspect",
        "-a",
        type=float,
        default=2**0.5,
        help=tr("Aspect ratio") + "-- 0.1,10",
    )
    parser.add_argument(
        "--overlap",
        "-l",
        type=int,
        default=5,
        help=tr("Overlap rate (percent)") + "-- 0,100",
    )
    parser.add_argument(
        "--head-right",
        "-R",
        action="store_true",
        help=tr("The train heads to the right."),
    )
    parser.add_argument(
        "--thumbnail",
        "-t",
        action="store_true",
        help=tr("Add a thumbnail image (Hans Ruijter's style)"),
    )
    parser.add_argument(
        "--width",
        "-W",
        type=int,
        default=0,
        help=tr("Width (pixels, 0 for original image size)") + "-- 0,10000",
    )
    return parser


def main():
    # デバッグ出力を設定
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger()
    logger.debug(f"LANG environment variable: {os.environ.get('LANG', '')}")

    # 翻訳を初期化
    init_translations()

    parser = get_parser()
    args = parser.parse_args()

    img = cv2.imread(args.image_path)
    canvas = convert(
        img, args.head_right, args.aspect, args.overlap, args.width, args.thumbnail
    )
    if args.output:
        cv2.imwrite(args.output, canvas)
    else:
        cv2.imwrite(f"{args.image_path}.rect.png", canvas)


if __name__ == "__main__":
    main()
