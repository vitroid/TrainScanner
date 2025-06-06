#!/usr/bin/env python3

"""
Wrapper for video systems

It does not fit the iterator framework.
"""

import sys
from trainscanner.video import video_cv2, image_dir
import os


def VideoLoader(filename: str):
    filename = filename.rstrip("/")
    if os.path.isdir(filename):
        return image_dir.VideoLoader(filename)
    ostype = sys.platform
    if ostype == "darwin":
        return video_cv2.VideoLoader(filename)
    elif 0 == ostype.find("linux"):
        return video_cv2.VideoLoader(filename)
    elif 0 == ostype.find("win"):
        return video_cv2.VideoLoader(filename)
    else:
        raise ValueError(f"Unsupported platform: {ostype}")


if __name__ == "__main__":
    vl = VideoLoader("../examples/sample3.mov")  # 58 frames

    while True:
        nframe, frame = vl.next()
        if nframe == 0:
            break
        print(frame.shape, nframe)
