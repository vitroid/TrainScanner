#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import math
import logging
import argparse
from trainscanner.i18n import tr, init_translations


# Determine tilt angle by Newton-Raphson method
# assuming that the aspect ratio is a:1
# The final image size should be px:py = a:1
# where px = h / sin(theta)
# and   py = w sin(theta) + h cos(theta)
# what we want is t = sin(theta) to satisfy the equations.
# So,
# h / t - a * (w * t + h*cos(theta))
# a t (wt + h cos(theta)) - h == 0 = f(t)
# a (wtt + h t sqrt(1-tt)) - h == 0 = f(t)
# f'(t) = a ( 2wt + ht sqrt() + ht .....
def rn_sine(w, h, aspect=2.0**0.5):
    def f(t):
        return aspect * (w * t**2 + h * t * (1 - t**2) ** 0.5) - h

    def df(t):
        return aspect * (
            2 * w * t + h * (1 - t**2) ** 0.5 - h * t**2 / (1 - t**2) ** 0.5
        )

    t = 0.5
    for i in range(10):
        t = t - f(t) / df(t)
    return t


def convert(img, aspect=2.0**0.5, width: int = None, head_right=True, **kwargs):
    """
    Helicify and project on a A-size paper proportion.
    Note: it fails when the strip is too short.
    """
    logger = logging.getLogger(__name__)
    logger.debug(f"Ignored options: {kwargs}")

    h, w = img.shape[0:2]
    if head_right:
        img = cv2.flip(img, 1)
    # height with a gap
    hg = int(h * 1.03)

    sine = rn_sine(w, hg, aspect=aspect)
    cosine = (1 - sine**2) ** 0.5
    px = hg / sine
    py = w * sine + hg * cosine

    N = (w - px * 2 * cosine) * cosine / px + 2
    N = int(math.ceil(N))

    row = int(px / cosine)
    row0 = int(hg * sine / cosine)
    xofs = int(hg * sine)

    canw = row + row0 * (N - 1)
    canh = hg * N

    padx = int(hg * sine)
    pady = int(px * sine)

    canvas = np.zeros((canh + pady * 2, canw + padx, 3), np.uint8)
    canvas[:, :, :] = 255
    for i in range(1, N - 1):
        x0 = i * (row - row0)
        # print(padx,canw,x0+canw,img.shape)
        if img.shape[1] <= x0 + canw:
            ww = img.shape[1] - x0
        else:
            ww = canw
        canvas[i * hg + pady : i * hg + h + pady, padx : padx + ww, :] = img[
            0:h, x0 : x0 + ww, :
        ]
    if img.shape[1] < canw:
        logger.warning(f"Image width is too short: {img.shape[1]} < {canw}")
        return img
    canvas[pady : h + pady, padx : canw + padx, :] = img[0:h, 0:canw, :]
    residue = w - (row - row0) * (N - 1)
    canvas[(N - 1) * hg + pady : (N - 1) * hg + h + pady, padx : residue + padx, :] = (
        img[0:h, w - residue : w, :]
    )
    a = cosine
    b = -sine
    cx = padx
    cy = pady

    R = np.matrix(((a, b, (1 - a) * cx - b * cy), (-b, a, b * cx + (1 - a) * cy)))
    canvas = cv2.warpAffine(canvas, R, (int(canw + padx), int(canh + pady * 2)))
    canvas2 = np.zeros((int(py), int(px), 3), np.uint8)
    canvas2[:, :, :] = canvas[
        pady : pady + int(py), padx - xofs : padx - xofs + int(px), :
    ]

    if head_right:
        canvas2 = cv2.flip(canvas2, 1)

    if width > 0:
        canvas_h, canvas_w = canvas2.shape[:2]
        height = canvas_h * width // canvas_w
        return cv2.resize(canvas2, (width, height), interpolation=cv2.INTER_CUBIC)
    else:
        return canvas2


def get_parser():
    parser = argparse.ArgumentParser(
        description=tr("Make a helical strip from a train image")
    )
    parser.add_argument("image_path", help=tr("Path of the input image file"))
    parser.add_argument("--output", "-o", help=tr("Path of the output file"))
    parser.add_argument(
        "--aspect",
        "-a",
        type=float,
        default=2.0**0.5,
        help=tr("Aspect ratio") + "-- 0.1,10",
    )
    parser.add_argument(
        "--head-right",
        "-R",
        action="store_true",
        help=tr("The train heads to the right."),
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
    logging.basicConfig(level=logging.DEBUG)

    init_translations()

    parser = get_parser()
    args = parser.parse_args()

    """
    Make a helical strip from a train image
    """

    img = cv2.imread(args.image_path)
    canvas2 = convert(
        img, aspect=args.aspect, width=args.width, head_right=args.head_right
    )
    if args.output:
        cv2.imwrite(args.output, canvas2)
    else:
        cv2.imwrite(f"{args.image_path}.helix.png", canvas2)


if __name__ == "__main__":
    main()
