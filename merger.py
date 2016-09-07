#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import trainscanner
import sys

if len(sys.argv) != 2:
    print "Usage: {0} trainscanner_logfile".format(sys.argv[0])
    sys.exit(1)

logfilename = sys.argv[1]
logfile = open(logfilename)
trainscanner.debug = False

merged = (np.zeros((100,100,3),np.uint8), (0,0))
for line in logfile.readlines():
    if len(line) > 0 and line[0] == "@":
        line = line[1:]
        cols = line.split()
        x    = int(cols[0])
        y    = int(cols[1])
        fragname = " ".join(cols[2:])
        print fragname
        location = (x,y)
        frame = cv2.imread(fragname)
        merged = trainscanner.abs_merge(merged, frame, *location)

# save the full frame
cv2.imwrite("{0}.png".format(logfilename), merged[0])
