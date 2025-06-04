#!/usr/bin/env python3

"""
Wrapper for video systems

It does not fit the iterator framework.
"""

import cv2


class VideoLoader(object):
    def __init__(self, filename):
        self.cap = cv2.VideoCapture(filename)
        self.nframe = 0

    def next(self):
        ret, frame = self.cap.read()
        self.nframe += 1
        if ret == False:
            return 0, frame
        return self.nframe, frame

    def skip(self):
        ret = self.cap.grab()
        self.nframe += 1
        if ret == False:
            return 0
        return self.nframe


if __name__ == "__main__":
    vl = VideoLoader("../examples/sample3.mov")

    while True:
        nframe, frame = vl.next()
        if nframe == 0:
            break
        print(frame.shape, nframe)
