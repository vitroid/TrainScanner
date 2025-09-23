#!/usr/bin/env python3

"""
Wrapper for video systems

"""

import cv2
import os


class VideoLoader(object):
    def __init__(self, filename):
        self.dirname = filename
        self.head = 0
        # ディレクトリ内のファイルをソートしておく
        self.filenames = sorted(
            [
                f"{self.dirname}/{f}"
                for f in os.listdir(self.dirname)
                if f.endswith(".png")
            ]
        )

    def next(self):
        if self.head >= len(self.filenames):
            return None
        filename = self.filenames[self.head]
        self.head += 1
        return cv2.imread(filename)

    def skip(self):
        self.head += 1
        return self.head

    def total_frames(self):
        return len(self.filenames)

    def seek(self, frame):
        self.head = frame
        return self.head
