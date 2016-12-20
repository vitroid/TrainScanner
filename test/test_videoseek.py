#!/usr/bin/env python3

import videosequence as vs

#from contextlib import closing
import cv2
import numpy as np
import random

frames = vs.VideoSequence("a.mp4")
print(len(frames))
a=b=1
for i in range(10):
    print(type(frames[a]))
    cv2image = cv2.cvtColor(np.array(frames[a]), cv2.COLOR_RGB2BGR)
    cv2.imshow("test", cv2image)
    cv2.waitKey(1)
    a,b = b,a+b
    b %= 100
frames.close()
