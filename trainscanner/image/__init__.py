import cv2
import numpy as np
from pyperbox import Rect, Range
import math
from dataclasses import dataclass
from trainscanner import MatchResult


@dataclass
class MatchScore:
    dx: np.ndarray
    dy: np.ndarray
    value: np.ndarray


@dataclass
class PreMatchScore(MatchScore):
    frame_index: int


# fit image in a square
def fit_to_square(image, size):
    h, w = image.shape[0:2]
    modified = False
    if h > w:
        if h > size:
            w = w * size // h
            h = size
            modified = True
    else:
        if w > size:
            h = h * size // w
            w = size
            modified = True
    if not modified:
        return image
    return cv2.resize(image, (w, h), interpolation=cv2.INTER_CUBIC)


def standardize(x):
    return ((x - np.mean(x)) / np.std(x)).astype(np.float32)


def diffImage(frame1, frame2, dx, dy, mode="stack"):  # , focus=None, slitpos=None):
    """
    2枚のcv2画像の差を返す．
    """
    affine = np.matrix(((1.0, 0.0, dx), (0.0, 1.0, dy)))
    h, w = frame1.shape[0:2]
    if mode == "diff":
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
        preview = fit_to_square(matchresult.image, self.preview_size)
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


# from parser to args
def deparse(parser, params):
    args = dict()
    pvars = vars(params)
    for key in pvars:
        value = pvars[key]
        for action in parser._actions:
            kwargs = action._get_kwargs()  # list of tuple
            kwdict = dict(kwargs)
            # print(kwdict)
            if kwdict["dest"] == key:
                options = kwdict["option_strings"]
                if len(options) == 0:
                    args["__UNNAMED__"] = value
                else:
                    args[options[-1]] = value
    return args


class Transformation:
    def __init__(self, angle=0, pers=None, crop=None):
        self.angle = -angle * math.pi / 180.0
        self.pers = pers
        self.crop = crop
        self.R = None
        self.M = None

    def rotation_affine(self, w, h):
        a = math.cos(self.angle)
        b = math.sin(self.angle)
        rh = abs(h * a) + abs(w * b)
        rw = abs(h * b) + abs(w * a)
        self.rh, self.rw = int(rh), int(rw)
        halfw, halfh = w / 2, h / 2
        self.R = np.matrix(
            (
                (a, b, -a * halfw - b * halfh + rw / 2),
                (-b, a, b * halfw - a * halfh + rh / 2),
            )
        )

    def rotated_image(self, image):
        return cv2.warpAffine(image, self.R, (self.rw, self.rh))

    def warp_affine(self):
        """
        Warp.  Save the perspective matrix to the file for future use.
        """
        if self.pers is None:
            return
        w = self.rw
        h = self.rh
        L = (self.pers[2] - self.pers[0]) * h // 1000
        S = (self.pers[3] - self.pers[1]) * h // 1000
        if L < S:
            L, S = S, L
        LS = (L * S) ** 0.5
        fdist = L / S
        ndist = LS // S
        sratio = ((fdist - 1.0) ** 2 + 1) ** 0.5
        neww = int(w * sratio / ndist)
        woffset = (neww - w) // 2
        p1 = np.float32(
            [
                (0, self.pers[0] * h / 1000),
                (w, self.pers[1] * h / 1000),
                (0, self.pers[2] * h / 1000),
                (w, self.pers[3] * h / 1000),
            ]
        )
        # Unskew
        p2 = np.float32(
            [
                (0, (self.pers[0] * self.pers[1]) ** 0.5 * h / 1000),
                (neww, (self.pers[0] * self.pers[1]) ** 0.5 * h / 1000),
                (0, (self.pers[2] * self.pers[3]) ** 0.5 * h / 1000),
                (neww, (self.pers[2] * self.pers[3]) ** 0.5 * h / 1000),
            ]
        )
        self.M = cv2.getPerspectiveTransform(p1, p2)
        self.ww = neww

    def warped_image(self, image):
        if self.pers is None:
            return image
        h = image.shape[0]
        return cv2.warpPerspective(image, self.M, (self.ww, h))

    def cropped_image(self, image):
        if self.crop is None:
            return image
        h, w = image.shape[:2]
        return image[self.crop[0] * h // 1000 : self.crop[1] * h // 1000, :, :]

    def process_first_image(self, image):
        h, w = image.shape[:2]
        self.rotation_affine(w, h)
        self.warp_affine()
        return self.process_next_image(image)

    def process_next_image(self, image):
        rotated = self.rotated_image(image)
        warped = self.warped_image(rotated)
        cropped = self.cropped_image(warped)
        return rotated, warped, cropped

    def process_image(self, image):
        if self.R is None:
            return self.process_first_image(image)
        else:
            return self.process_next_image(image)

    def process_images(self, images):
        h, w = images[0].shape[:2]
        self.rotation_affine(w, h)
        self.warp_affine()
        rs = []
        ws = []
        cs = []
        for image in images:
            rotated, warped, cropped = self.process_next_image(image)
            rs.append(rotated)
            ws.append(warped)
            cs.append(cropped)
        return rs, ws, cs


def match(
    target_area: np.ndarray, target_rect: Rect, focus: np.ndarray, focus_rect: Rect
) -> MatchScore:
    # 大きな画像の一部(座標範囲はtarget_rect)であるtarget_areaの中に、同じく大きな画像(座標範囲はfocus_rect)の一部であるfocusがある。
    # その場所をさがし、変位ベクトルとスコアを返す。
    assert target_area.shape[0] == target_rect.height
    assert target_area.shape[1] == target_rect.width
    assert focus.shape[0] == focus_rect.height
    assert focus.shape[1] == focus_rect.width
    scores = cv2.matchTemplate(target_area, focus, cv2.TM_CCOEFF_NORMED)
    # scoresに座標を指示する。
    dx = range(
        target_rect.left - focus_rect.left,
        target_rect.right - focus_rect.right + 1,
    )
    dy = range(
        target_rect.top - focus_rect.top,
        target_rect.bottom - focus_rect.bottom + 1,
    )
    # 変位ベクトルとスコアをセットで返す。
    return MatchScore(dx, dy, scores)
