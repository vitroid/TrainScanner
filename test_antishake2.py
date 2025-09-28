import cv2
import numpy as np
import sys


def standardize(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return ((gray - np.mean(gray)) / np.std(gray)).astype(np.float32)


def shiftx(frame, dx):
    return np.roll(frame, dx, axis=1)


def shifty(frame, dy):
    return np.roll(frame, dy, axis=0)


def shift(frame, dx, dy):
    return shiftx(shifty(frame, dy), dx)


class AntiShaker2:
    # 直前のフレームとの差を返しつつ、変位の総量(最初のフレームからの累積変位)を記憶しておく。
    def __init__(self):
        self.absx = 0
        self.absy = 0
        self.last_frame = None

    def add_frame(self, frame, mask):
        h, w = frame.shape[:2]
        frame_std = standardize(frame)

        if self.last_frame is None:
            self.last_frame = frame_std.copy()
            return frame, (0, 0), (0, 0)

        max_shift = 1
        frame0_extend = np.zeros(
            (h + 2 * max_shift, w + 2 * max_shift), dtype=np.float32
        )
        frame0_extend[max_shift:-max_shift, max_shift:-max_shift] = self.last_frame
        print(frame0_extend.dtype, frame_std.dtype, mask.dtype)
        scores = cv2.matchTemplate(frame0_extend, frame_std * mask, cv2.TM_CCORR)
        _, _, _, max_loc = cv2.minMaxLoc(scores)
        dx, dy = (max_loc[0] - max_shift, max_loc[1] - max_shift)
        self.absx += dx
        self.absy += dy
        diff_img = self.last_frame.copy()
        shifted_frame = shift(frame_std, dx, dy)
        cv2.imshow("diff", diff_img - shifted_frame)
        self.last_frame = frame_std.copy()
        return shift(frame, self.absx, self.absy), (dx, dy), (self.absx, self.absy)


if __name__ == "__main__":
    antishaker = AntiShaker2()
    # 動画を読み込む
    if len(sys.argv) < 2:
        videofile = "examples/sample3.mov"
        videofile = "/Users/matto/Dropbox/ArtsAndIllustrations/Stitch tmp2/TrainScannerWorkArea/他人の動画/antishake test/Untitled.mp4"
    else:
        videofile = sys.argv[1]
    cap = cv2.VideoCapture(videofile)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame, delta, abs_loc = antishaker.add_frame(
            frame, np.ones(frame.shape[:2], dtype=np.float32)
        )
        cv2.imshow("frame", frame)
        cv2.waitKey(0)
