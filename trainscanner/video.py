#!/usr/bin/env python3

"""
Wrapper for video systems

It does not fit the iterator framework.
"""

import importlib
import sys

def VideoLoader(filename):
    module = None
    ostype = sys.platform
    if ostype == "darwin":
        module     = importlib.import_module("trainscanner.video_sk")
        #module     = importlib.import_module("trainscanner.video_cv2")
    elif 0 == ostype.find("linux"):
        module     = importlib.import_module("trainscanner.video_sk") # linux's cv2 does not contain video decoders
    elif 0 == ostype.find("win"):
        module     = importlib.import_module("trainscanner.video_cv2")
    return module.VideoLoader(filename)


def main():
    vl = VideoLoader("examples/sample3.mov") #58 frames

    while True:
        nframe, frame = vl.next()
        if nframe == 0:
            break
        print(frame.shape, nframe)

if __name__ == "__main__":
    main()
