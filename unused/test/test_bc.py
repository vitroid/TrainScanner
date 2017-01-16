#!/usr/bin/env python3

import numpy as np

a = np.array([(1,2,3,4),
              (5,6,7,8),
              (9,10,11,12)])
b = np.array([1,0,-1])

print(a*b[:,np.newaxis])
