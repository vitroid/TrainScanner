#!/usr/bin/env python3

"""
Wrapper for video systems using PyAV

It does not fit the iterator framework.
"""

import av
import numpy as np


class VideoLoader(object):
    def __init__(self, filename):
        self.container = av.open(filename)
        self.stream = self.container.streams.video[0]
        self.nframe = 0
        self.total_frames = self.stream.frames

    def next(self):
        if self.nframe >= self.total_frames:
            return 0, None

        for frame in self.container.decode(video=0):
            if frame.index == self.nframe:
                # Convert to RGB and then to BGR (OpenCV format)
                frame = frame.to_ndarray(format="rgb24")
                frame = frame[:, :, ::-1]  # RGB to BGR
                self.nframe += 1
                return self.nframe, frame
        return 0, None

    def skip(self):
        if self.nframe >= self.total_frames:
            return 0

        self.nframe += 1
        return self.nframe


if __name__ == "__main__":
    vl = VideoLoader("examples/sample.mov")

    while True:
        nframe, frame = vl.next()
        if nframe == 0:
            break
        print(frame.shape, nframe)
