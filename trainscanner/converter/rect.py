#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import click


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


@click.command()
@click.argument("image_path")
@click.option("--output", "-o", help="出力ファイルのパス")
@click.option("--rows", "-r", type=int, default=None, help="行数")
@click.option("--gap", "-g", type=int, default=0, help="マージン")
@click.option("--head-right", "-R", is_flag=True, help="右端が先頭")
def main(image_path, output, rows, gap, head_right):
    """
    Fold a train image into a stack of images
    """
    img = cv2.imread(image_path)
    canvas = rectify(img, rows, gap, head_right)
    if output:
        cv2.imwrite(output, canvas)
    else:
        cv2.imwrite(f"{image_path}.rect.png", canvas)


if __name__ == "__main__":
    main()
