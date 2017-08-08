#!/usr/bin/env python3

"""
Wrapper for video systems

no skip
no frame number
just read from start til end
"""

import cv2

try:
    import skvideo.io
    
    # Generator
    def VideoIter(filename):
        vi = skvideo.io.FFmpegReader(filename)
        for frame in vi.nextFrame():
            yield frame[:,:,::-1].copy()  #RGB to BGR (opencv)
except ImportError:
    # Iterator
    class VideoIter(object):
        def __init__(self,filename):
            self.cap = cv2.VideoCapture(filename)

        def __iter__(self):
            return self

        def __next__(self):
            ret, frame = self.cap.read()
            if not ret:
                raise StopIteration
            return frame




if __name__ == "__main__":
    vi = VideoIter("../examples/sample3.mov")

    for i,frame in enumerate(vi):
        print(frame.shape, i+1)

