#!/usr/bin/env python

import videosequence as vs

frames = vs.VideoSequence("/home/vitroid/github/TrainScanner/sample.mp4")

for frame in frames:
    print(frame.shape)
