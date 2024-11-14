#!/usr/bin/env python3

"""
Wrapper for video systems

It does not fit the iterator framework.
"""

import skvideo.io


class VideoLoader(object):
    def __init__(self, filename):
        vi = skvideo.io.FFmpegReader(filename)
        self.iter = vi.nextFrame()
        self.nframe = 0

    def next(self):
        self.nframe += 1
        try:
            frame = self.iter.__next__()
        except StopIteration:
            return 0, 0
        return self.nframe, frame[:, :, ::-1].copy()  # RGB to BGR

    def skip(self):
        self.nframe += 1
        try:
            frame = self.iter.__next__()
        except StopIteration:
            return 0
        return self.nframe


if __name__ == "__main__":
    vl = VideoLoader("../examples/sample3.mov")

    while True:
        nframe, frame = vl.next()
        if nframe == 0:
            break
        print(frame.shape, nframe)
