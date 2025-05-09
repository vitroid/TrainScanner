#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import click


def hansify(img, rows=3, overlap=10):
    """
    Hans Ruijter's style
    """
    h, w = img.shape[0:2]

    hh = h * rows
    # ====+         ww1 = ww + A
    #   +====+     ww  = ww
    #       +===== ww1 = ww + A
    # ww1 + (rows-2)*ww + ww1 = = ww*rows+2A = w
    # ww*overlap/100 = A
    # So, ww*(rows+overlap/50) = w
    ww = int(w / (rows + overlap / 50))
    A = ww * overlap // 100

    neww = ww + 2 * A
    thh = h * neww // w
    thumb = cv2.resize(img, (neww, thh), interpolation=cv2.INTER_CUBIC)
    # thh, thw = thumb.shape[0:2]
    canvas = np.zeros((hh + thh, neww, 3), dtype=np.uint8)
    canvas[0:thh, 0:neww, :] = thumb
    for i in range(0, rows):
        canvas[thh + i * h : thh + (i + 1) * h, 0:neww, :] = img[
            :, i * ww : (i + 1) * ww + 2 * A, :
        ]
    return canvas


@click.command()
@click.argument("image_path")
@click.option("--output", "-o", help="出力ファイルのパス")
@click.option("--rows", "-r", type=int, default=3, help="行数")
@click.option("--overlap", "-l", type=int, default=5, help="重複率")
def main(image_path, output, rows, overlap):
    img = cv2.imread(image_path)
    canvas = hansify(img, rows, overlap)
    if output:
        cv2.imwrite(output, canvas)
    else:
        cv2.imwrite(f"{image_path}.hans.png", canvas)


if __name__ == "__main__":
    main()
