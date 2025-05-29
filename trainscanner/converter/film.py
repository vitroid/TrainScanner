#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import cv2
import numpy as np


def roundbox(img, p1, p2, r, color):
    cv2.circle(img, (p1[0] + r, p1[1] + r), r, color, -1)
    cv2.circle(img, (p2[0] - r, p1[1] + r), r, color, -1)
    cv2.circle(img, (p1[0] + r, p2[1] - r), r, color, -1)
    cv2.circle(img, (p2[0] - r, p2[1] - r), r, color, -1)
    cv2.rectangle(img, (p1[0], p1[1] + r), (p2[0], p2[1] - r), color, -1)
    cv2.rectangle(img, (p1[0] + r, p1[1]), (p2[0] - r, p2[1]), color, -1)


def filmify(img, label=""):
    h, w = img.shape[0:2]
    filmw = h * 35 // 24  # film width in pixel
    pad = h * (35 - 24 - 1) // 2 // 24  # padding width for perforations in pixel
    framew = h * 38 // 24  # Width of one "35 mm film" frame in pixel
    perf = framew // 8  # Perforation interval in pixel
    perfh = h * 3 // 24  # perforation hole height
    perfw = h * 2 // 24  # perforation hole width
    perfr = h // 2 // 24  # perforation hole roundness
    canh = filmw
    oneframe = np.zeros((canh, framew, 3), np.uint8)
    # perforations
    for i in range(0, 9):
        x = i * framew // 8
        roundbox(
            oneframe,
            (x - perfw // 2, pad - perfh),
            (x + perfw // 2, pad),
            perfr,
            (255, 255, 255),
        )
        roundbox(
            oneframe,
            (x - perfw // 2, filmw - pad),
            (x + perfw // 2, filmw - pad + perfh),
            perfr,
            (255, 255, 255),
        )

    canvas = np.zeros((canh, w, 3), np.uint8)
    # frame label
    count = 1
    font = cv2.FONT_HERSHEY_PLAIN
    fontsize = pad // 32
    thick = pad // 20  # font line thickness
    for i in range(0, w, framew):
        frame = oneframe.copy()
        text = str(count)
        box, _ = cv2.getTextSize(text, font, fontsize, thick)
        textw, texth = box
        cv2.putText(
            frame,
            text,
            (int(perf * 4.5) - textw // 2, int(texth * 1.2)),
            font,
            fontsize,
            (0, 150, 200),
            thick,
        )
        wend = i + framew
        if wend > w:
            canvas[:, i : i + framew - (wend - w), :] = frame[
                :, 0 : framew - (wend - w), :
            ]
        else:
            canvas[:, i : i + framew] = frame[:, :]
        count += 1

    canvas[(filmw - h) // 2 : (filmw - h) // 2 + h, 0:w] = img
    if label:
        fontsize = pad // 48
        thick = pad // 30
        box, _ = cv2.getTextSize(label, font, fontsize, thick)
        textw, texth = box
        cv2.putText(
            canvas,
            label,
            (int(perf * 0.5), int(canh)),
            font,
            fontsize,
            (0, 150, 200),
            thick,
        )
    return canvas


def get_parser():
    """
    コマンドライン引数のパーサーを生成して返す関数
    """
    parser = argparse.ArgumentParser(description="Add film perforations to the image")
    parser.add_argument("image_path", help="入力画像ファイルのパス")
    parser.add_argument("--output", "-o", help="出力ファイルのパス")
    parser.add_argument("--creative_commons_sign", "-c", help="Creative Commons sign")
    return parser




def main():
    parser = get_parser()
    args = parser.parse_args()

    img = cv2.imread(args.image_path)
    canvas = filmify(img, label=args.creative_commons_sign)
    if args.output:
        cv2.imwrite(args.output, canvas)
    else:
        cv2.imwrite(f"{args.image_path}.film.png", canvas)


if __name__ == "__main__":
    main()
