#!/usr/bin/env python3

import videosequence as vs

from contextlib import closing
import cv2
import random

with closing(vs.VideoSequence("a.mp4")) as frames:
    a=b=1
    for i in range(1000):
        print(type(frames[a]))
        cv2.imshow("test", frames[a])
        cv2.waitkey(1)
        a,b = b,a+b
        b %= 100
