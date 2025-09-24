import cv2
import numpy as np
import scipy.optimize
from logging import getLogger
from dataclasses import dataclass
import os
from tiffeditor import Rect, Range


@dataclass
class FramePosition:
    index: int
    dt: int
    velocity: tuple[float, float]


@dataclass
class MatchResult:
    index: int
    dt: int
    velocity: tuple[float, float]
    value: float
    image: np.ndarray


def standardize(x):
    return ((x - np.mean(x)) / np.std(x)).astype(np.float32)


def diffImage(frame1, frame2, dx, dy, mode="stack"):  # , focus=None, slitpos=None):
    """
    2枚のcv2画像の差を返す．
    """
    if mode == "diff":
        affine = np.matrix(((1.0, 0.0, dx), (0.0, 1.0, dy)))
        h, w = frame1.shape[0:2]
        std2 = standardize(frame2)
        frame1 = cv2.warpAffine(frame1, affine, (w, h))
        std1 = standardize(frame1)
        diff = (255 * cv2.absdiff(std1, std2)).astype(np.uint8)
        # if focus is not None:
        #     draw_focus_area(diff, focus, delta=(dx, dy))
        # if slitpos is not None:
        #     draw_slit_position(diff, slitpos, dx)
        return diff
    elif mode == "stack":
        affine = np.matrix(((1.0, 0.0, dx), (0.0, 1.0, dy)))
        h, w = frame1.shape[0:2]
        flags = np.arange(h) * 16 % h > h // 2
        frame1 = cv2.warpAffine(frame1, affine, (w, h))
        frame1[flags] = frame2[flags]
        return frame1


def draw_focus_area(f, focus: Rect):
    """
    cv2形式の画像の中に四角を描く
    """
    h, w = f.shape[0:2]
    pos = Rect(
        x_range=Range(
            min_val=w * focus.x_range.min_val // 1000,
            max_val=w * focus.x_range.max_val // 1000,
        ),
        y_range=Range(
            min_val=h * focus.y_range.min_val // 1000,
            max_val=h * focus.y_range.max_val // 1000,
        ),
    )
    colors = [(0, 255, 0), (255, 255, 0)]
    cv2.rectangle(f, (pos.left, pos.top), (pos.right, pos.bottom), colors[0], 1)


class diffview:
    def __init__(self, focus: Rect):
        self.focus = focus
        self.lastimage = None
        self.preview_size = 500

    def view(self, matchresult: MatchResult):
        preview = trainscanner.fit_to_square(matchresult.image, self.preview_size)
        # draw focus area here
        draw_focus_area(
            preview,
            self.focus,
        )
        preview_ratio = preview.shape[0] / matchresult.image.shape[0]
        if self.lastimage is None:
            self.lastimage = preview
            return None
        deltax = int(matchresult.velocity[0] * matchresult.dt * preview_ratio)
        deltay = int(matchresult.velocity[1] * matchresult.dt * preview_ratio)
        diff = diffImage(preview, self.lastimage, deltax, deltay)
        self.lastimage = preview
        return diff
