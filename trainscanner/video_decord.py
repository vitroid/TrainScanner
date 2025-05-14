#!/usr/bin/env python3

"""
Wrapper for video systems using decord

It does not fit the iterator framework.
"""

import decord
import numpy as np


class VideoLoader(object):
    def __init__(self, filename):
        self.vr = decord.VideoReader(filename)
        self.nframe = 0
        self.total_frames = len(self.vr)

    def next(self):
        if self.nframe >= self.total_frames:
            return 0, None

        frame = self.vr[self.nframe].asnumpy()
        self.nframe += 1
        return self.nframe, frame

    def skip(self):
        if self.nframe >= self.total_frames:
            return 0

        self.nframe += 1
        return self.nframe


if __name__ == "__main__":
    vl = VideoLoader("../examples/sample3.mov")

    while True:
        nframe, frame = vl.next()
        if nframe == 0:
            break
        print(frame.shape, nframe)
