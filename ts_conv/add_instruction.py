#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cv2
import numpy as np
import click


@click.command()
@click.argument("image_path")
def add_instruction(image_path):

    img = cv2.imread(image_path)

    h, w = img.shape[0:2]

    inst = cv2.imread("instruction/instruction.png")
    ih, iw = inst.shape[0:2]

    ratio = float(h) / ih
    scaled = cv2.resize(inst, None, fx=ratio, fy=ratio, interpolation=cv2.INTER_CUBIC)

    sh, sw = scaled.shape[0:2]
    if sh > h:
        sh = h
    canvas = np.zeros((h, w + sw, 3), np.uint8)
    canvas[0:h, 0:w] = img
    canvas[0:sh, w : w + sw] = scaled

    cv2.imwrite(f"{image_path}.inst.png", canvas)
