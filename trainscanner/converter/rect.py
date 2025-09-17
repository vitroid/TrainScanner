#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import argparse
from trainscanner.i18n import tr, init_translations
import logging
import os
from trainscanner.image import Region
from trainscanner.image.rasterio_canvas import RasterioCanvas
import rasterio


def convert(
    src_canvas,
    dst_filename,
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
    src_width = src_canvas.region.right - src_canvas.region.left
    src_height = src_canvas.region.bottom - src_canvas.region.top

    body_height = src_height * rows
    body_width = int(src_width / (rows + overlap / 50))

    extra_width = body_width * overlap // 100

    total_width = body_width + 2 * extra_width
    scale = width / total_width
    if thumbnail:
        thumb = src_canvas.get_image(total_width)
        # cv2.imshow("thumb", thumb)
        # cv2.waitKey(0)
        thumb_height = thumb.shape[0]
        dst_canvas = RasterioCanvas(
            "new",
            dst_filename,
            region=Region(
                left=0, right=total_width, top=0, bottom=body_height + thumb_height
            ),
            scale=scale,
        )
        dst_canvas.put_image((0, body_height), thumb)
    else:
        thumb_height = 0
        dst_canvas = RasterioCanvas(
            "new",
            dst_filename,
            region=Region(left=0, right=total_width, top=0, bottom=body_height),
            scale=scale,
        )

    # srcの各列の左端
    X = [extra_width + i * (body_width + extra_width) for i in range(0, rows)]
    X[0] = 0
    for i in range(0, rows):
        cut = src_canvas.get_region(
            Region(
                left=X[i],
                right=X[i] + (body_width + extra_width),
                top=0,
                bottom=src_height,
            )
        )
        if head_right:
            dst_canvas.put_image((0, src_height * i), cut)
        else:
            dst_canvas.put_image((0, src_height * (rows - i - 1)), cut)

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

    src_canvas = RasterioCanvas(
        "r+",
        tiff_filename=args.image_path,
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
