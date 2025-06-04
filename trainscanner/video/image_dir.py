#!/usr/bin/env python3

"""
Wrapper for video systems

"""

import cv2
import os


class VideoLoader(object):
    def __init__(self, filename):
        self.dirname = filename
        self.nframe = 0
        # ディレクトリ内のファイルをソートしておく
        self.filenames = sorted(
            [
                f"{self.dirname}/{f}"
                for f in os.listdir(self.dirname)
                if f.endswith(".png")
            ]
        )

    def next(self):
        if self.nframe >= len(self.filenames):
            return 0, None
        filename = self.filenames[self.nframe]
        frame = cv2.imread(filename)
        self.nframe += 1
        return self.nframe, frame

    def skip(self):
        self.nframe += 1
        return self.nframe
