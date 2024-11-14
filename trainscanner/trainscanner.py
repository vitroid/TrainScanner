#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Now only the horizontal scroll is allowed
import cv2
import numpy as np
import math


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
            if kwdict["dest"] is key:
                options = kwdict["option_strings"]
                if len(options) == 0:
                    args["__UNNAMED__"] = value
                else:
                    args[options[-1]] = value
    return args


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


class transformation:
    def __init__(self, angle=0, pers=None, crop=None):
        self.angle = -angle * math.pi / 180.0
        self.pers = pers
        self.crop = crop
        self.R = None
        self.M = None

    def rotation_affine(self, w, h):
        a = math.cos(self.angle)
        b = math.sin(self.angle)
        rh = max(abs(h * a), abs(w * b))
        rw = max(abs(h * b), abs(w * a))
        self.rh, self.rw = int(rh), int(rw)
        self.R = np.matrix(
            (
                (a, b, (1 - a) * w / 2 - b * h / 2 + (rw - w) / 2),
                (-b, a, b * w / 2 + (1 - a) * h / 2 + (rh - h) / 2),
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


class VideoHandler_notused(transformation):
    """
    not used.
    """

    def __init__(self, angle=0, pers=None, crop=None):
        super(VideoHandler, self).__init__(self, angle, pers, crop)
        self.lastframe = -1

    def open(self, filename):
        self.filename = filename
        self.cap = cv2.VideoCapture(filename)

    def skip(self, N):
        for i in range(N):
            ret = self.cap.grap()
            if not ret:
                return False
        self.lastframe += N
        return True

    def seek(self, N):
        """
        move to the Nth frame (0 is the head)
        same meaning as skip
        """
        assert self.lastframe < 0, "For now, seek only works from the head"
        return self.skip(N)

    def read_raw(self):
        ret, self.frame = self.cap.read()
        return frame

    def read(self):
        self.rawframe = self.read_raw()
        self.rotated, self.warped, self.cropped = self.process_image(self.rawframe)
        return self.rotated, self.warped, self.cropped


if __name__ == "__main__":
    import sys

    print(
        "It is now useless as a command line tool. Use trainscanner_gui.py or pass1.py."
    )
    sys.exit(1)
