import cv2
import numpy as np
import sys


def standardize(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return ((gray - np.mean(gray)) / np.std(gray)).astype(np.float32)


def shiftx(frame, dx):
    if dx == 0:
        return frame
    h, w = frame.shape[:2]
    result = np.zeros_like(frame)
    if dx > 0:
        result[:, dx:] = frame[:, :-dx]
        return result
    result[:, :dx] = frame[:, -dx:]
    return result


def shifty(frame, dy):
    if dy == 0:
        return frame
    h, w = frame.shape[:2]
    result = np.zeros_like(frame)
    if dy > 0:
        result[dy:, :] = frame[:-dy, :]
        return result
    result[:dy, :] = frame[-dy:, :]
    return result


def shift(frame, dx, dy):
    # 余った部分は0にする。
    return shiftx(shifty(frame, dy), dx)


class AntiShaker:
    def __init__(self):
        self.deltas = []

    def add_frame(self, frame, mask):
        h, w = frame.shape[:2]
        frame_std = standardize(frame)
        if len(self.deltas) == 0:
            self.frame0 = frame_std.copy()
            self.deltas.append((0, 0))
            return frame, (0, 0)

        max_shift = 1
        dx, dy = self.deltas[-1]
        frame0_extend = np.zeros(
            (h + 2 * max_shift, w + 2 * max_shift), dtype=np.float32
        )
        frame0_extend[max_shift:-max_shift, max_shift:-max_shift] = self.frame0
        frame0_extend = shift(frame0_extend, -dx, -dy)
        print(frame0_extend.dtype, frame_std.dtype, mask.dtype)
        scores = cv2.matchTemplate(frame0_extend, frame_std * mask, cv2.TM_CCORR)
        min_val, max_val0, min_loc, max_loc = cv2.minMaxLoc(scores)
        dx, dy = (dx + max_loc[0] - max_shift, dy + max_loc[1] - max_shift)
        self.deltas.append((dx, dy))
        diff_img = self.frame0.copy()
        shifted_frame = shift(frame_std, dx, dy)
        cv2.imshow("diff", diff_img - shifted_frame)
        return shift(frame, dx, dy), (dx, dy)


if __name__ == "__main__":
    antishaker = AntiShaker()
    cap = cv2.VideoCapture(sys.argv[1])
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame, delta = antishaker.add_frame(
            frame, np.ones(frame.shape[:2], dtype=np.float32)
        )
        cv2.imshow("frame", frame)
        cv2.waitKey(0)
