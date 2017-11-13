#!/usr/bin/env python3

"""
Wrapper for video systems

It does not fit the iterator framework.
"""

import videosequence as vs
import numpy as np

class VideoLoader(object):
    def __init__(self,filename):
        self.vs = vs.VideoSequence(filename)
        self.nframe = 0

    def next(self):
        self.nframe += 1
        if self.nframe > len(self.vs):
            return 0, 0
        return self.nframe, np.asarray(self.vs[self.nframe-1]).copy()  #RGB to BGR

    def skip(self,n=1):
        self.nframe += n
        if self.nframe > len(self.vs):
            return 0, 0
        return self.nframe



if __name__ == "__main__":
    vl = VideoLoader("../examples/sample3.mov")

    while True:
        nframe, frame = vl.next()
        if nframe == 0:
            break
        print(frame.shape, nframe)

