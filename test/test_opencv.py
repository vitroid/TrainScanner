#!/usr/bin/env python

import skvideo.io

#cap = skvideo.io.VideoCapture("/home/vitroid/github/TrainScanner/sample.mp4")
cap = skvideo.io.FFmpegReader("/home/vitroid/github/TrainScanner/sample.mp4")

for frame in cap.nextFrame():
    print(frame.shape)
