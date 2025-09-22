#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import argparse
from trainscanner.i18n import tr, init_translations
import logging
import os
from tiffeditor import Rect, Range, TiffEditor


def convert(
    src_canvas,
    dst_filename: str = None,
    head_right: bool = True,
    rows: int = 4,
    overlap: int = 10,
    width: int = 0,
    thumbnail: bool = False,
    **kwargs,
):
    """
    Hans Ruijter's style
    """
    logger = logging.getLogger()
    logger.debug(f"Ignored options: {kwargs}")
    src_height, src_width = src_canvas.shape[:2]

    body_height = src_height * rows
    body_width = int(src_width / (rows + overlap / 100))

    extra_width = body_width * overlap // 100

    unscaled_width = body_width + extra_width

    if width:
        scale = width / unscaled_width
        # srcをあらかじめスケールして、あとの処理は同じにする。
        if isinstance(src_canvas, TiffEditor):
            src_canvas = src_canvas.get_scaled_image(scale)
        else:
            src_canvas = cv2.resize(
                src_canvas, (int(src_width * scale), int(src_height * scale))
            )

        src_height, src_width = src_canvas.shape[:2]

        body_height = src_height * rows
        body_width = int(src_width / (rows + overlap / 100))

        extra_width = body_width * overlap // 100

    else:
        width = unscaled_width

    if thumbnail:
        thumb_scale = width / src_width
        if isinstance(src_canvas, TiffEditor):
            thumb = src_canvas.get_scaled_image(thumb_scale)
        else:
            thumb = cv2.resize(src_canvas, (width, int(src_height * thumb_scale)))
        # cv2.imshow("thumb", thumb)
        # cv2.waitKey(0)
        thumb_height = thumb.shape[0]
    else:
        thumb_height = 0

    dst_height = body_height + thumb_height
    if dst_filename is None:
        dst_canvas = np.zeros([dst_height, width, 3], dtype=np.uint8)
    else:
        dst_canvas = TiffEditor(
            filepath=dst_filename,
            mode="w",
            shape=(dst_height, width, 3),
            dtype=np.uint8,
        )
    if thumbnail:
        dst_canvas[0 : thumb.shape[0], : thumb.shape[1]] = thumb

    # srcの各列の左端
    X = [i * body_width for i in range(rows)]
    for i in range(rows):
        cut = src_canvas[0:src_height, X[i] : X[i] + width]
        if head_right:
            dst_canvas[
                src_height * (rows - i - 1)
                + thumb_height : src_height * (rows - i)
                + thumb_height,
                :,
            ] = cut
        else:
            dst_canvas[
                src_height * i + thumb_height : src_height * (i + 1) + thumb_height,
                :,
            ] = cut

    # head_right
    # scale
    return dst_canvas


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
        "--rows",
        "-r",
        type=int,
        default=4,
        help=tr("Number of rows") + "-- 1:25",
    )
    parser.add_argument(
        "--overlap",
        "-l",
        type=int,
        default=5,
        help=tr("Overlap rate (percent)") + "-- 0:100",
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
        help=tr("Width (pixels, 0 for original image size)") + "-- 0:10000",
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

    src_canvas = TiffEditor(
        filepath=args.image_path,
        mode="r+",
    )
    convert(
        src_canvas,
        dst_filename=args.image_path + ".rect.tiff",
        head_right=args.head_right,
        rows=args.rows,
        overlap=args.overlap,
        width=args.width,
        thumbnail=args.thumbnail,
    )
    # if args.output:
    #     cv2.imwrite(args.output, canvas)
    # else:
    #     cv2.imwrite(f"{args.image_path}.rect.png", canvas)


if __name__ == "__main__":
    main()
