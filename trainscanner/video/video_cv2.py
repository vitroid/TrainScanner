#!/usr/bin/env python3

"""
Wrapper for video systems

It does not fit the iterator framework.
"""

import cv2


class VideoLoader(object):
    # In TrainScanner, the video frame starts from 0
    def __init__(self, filename):
        self.cap = cv2.VideoCapture(filename)
        self.head = 0
        # 1 is the first frame

    def next(self):
        ret, frame = self.cap.read()
        if ret == False:
            return None
        framenumber = self.head
        self.head += 1
        return frame

    def skip(self):
        ret = self.cap.grab()
        self.head += 1
        if ret == False:
            return None
        return self.head

    def total_frames(self):
        return int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # def seek(self, frame):
    #     ret = self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
    #     if ret == False:
    #         return None
    #     self.head = frame
    #     return self.head

    def seek(self, frame):
        if frame < self.head:
            assert False
        while frame != self.head:
            self.skip()
        return self.head


if __name__ == "__main__":
    vl = VideoLoader("../examples/sample3.mov")

    while True:
        nframe, frame = vl.next()
        if nframe == 0:
            break
        print(frame.shape, nframe)
