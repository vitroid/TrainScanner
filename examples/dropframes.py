import cv2
import numpy as np
import random

# read a movie and drop some frames randomly.

cap = cv2.VideoCapture("sample.mov")
frame = cap.read()
fps = cap.get(cv2.CAP_PROP_FPS)
w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
video_out = cv2.VideoWriter(
    "sample_df.mp4", cv2.VideoWriter_fourcc(*"avc1"), fps, (w, h)
)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    if random.random() < 0.1:
        continue
    video_out.write(frame)

video_out.release()
