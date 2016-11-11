#!/usr/bin/env python
# -*- coding: utf-8 -*-

from math import *
import numpy as np

fold = np.array([0, 0.1, 0.15, 0.25])
w, h = 96396, 1920
image = "/Users/matto/Shared/ArtsAndIllustrations/Stitch\ tmp2/Kanazawa/BDMV02.mov.log.tif"

#Radius of the cylinder
#Must be large enough
R = 4000

#rotation angle of the whole strip
angle = 5 * pi / 180

#folding positions
xfold = fold * w

#center of each section
center = (fold[1:4] + fold[0:3]) / 2
xcenter = center * w

#horizontal width of the section
wsection = (fold[1:4] - fold[0:3]) * w * cos(angle)
#height of the center
zcenter = center * sin(angle)

#Distance from the center of the cylinder
rsection = sqrt(R**2 - (wsection / 2)**2)

#they are all information
#They canbe calculated inside the povray.
#If it has an array feature.


    
