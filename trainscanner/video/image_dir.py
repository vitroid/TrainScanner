#!/usr/bin/env python3

"""
Wrapper for video systems

"""

import cv2


class VideoLoader(object):
    def __init__(self, filename):
        self.dirname = filename
        self.nframe = 0

    def next(self):
        filename = f"{self.dirname}/{self.nframe:06d}.png"
        frame = cv2.imread(filename)
        self.nframe += 1
        if frame is None:
            return 0, frame
        return self.nframe, frame

    def skip(self):
        self.nframe += 1
        return self.nframe
