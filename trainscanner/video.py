#!/usr/bin/env python3

"""
Wrapper for video systems

no skip
no frame number
just read from start til end
"""

import cv2

# Iterator
class Cv2VideoIter(object):
    def __init__(self,filename):
        self.cap = cv2.VideoCapture(filename)

    def __iter__(self):
        return self

    def __next__(self):
        ret, frame = self.cap.read()
        if not ret:
            raise StopIteration
        return frame

import skvideo.io

# Generator
def SkVideoIter(filename):
    vi = skvideo.io.FFmpegReader(filename)
    for frame in vi.nextFrame():
        yield frame[:,:,::-1].copy()  #RGB to BGR (opencv)


if __name__ == "__main__":
    vi = Cv2VideoIter("../examples/sample3.mov")

    for i,frame in enumerate(vi):
        print("cv2",frame.shape, i+1)

    vi = SkVideoIter("../examples/sample3.mov")

    for i,frame in enumerate(vi):
        print("sk",frame.shape,i+1)

