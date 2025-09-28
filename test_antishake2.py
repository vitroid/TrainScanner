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
    def __init__(self, velocity=1):
        self._absx = 0
        self._absy = 0
        self._last_frame = None
        self._velocity = velocity

    def add_frame(self, frame, mask):
        h, w = frame.shape[:2]
        frame_std = standardize(frame)

        if self._last_frame is None:
            self._last_frame = frame_std.copy()
            return frame, (0, 0), (0, 0)

        frame0_extend = np.zeros(
            (h + 2 * self._velocity, w + 2 * self._velocity), dtype=np.float32
        )
        frame0_extend[
            self._velocity : -self._velocity, self._velocity : -self._velocity
        ] = self._last_frame
        scores = cv2.matchTemplate(frame0_extend, frame_std * mask, cv2.TM_CCORR)
        print(scores)
        _, _, _, max_loc = cv2.minMaxLoc(scores)
        dx, dy = (max_loc[0] - self._velocity, max_loc[1] - self._velocity)
        print(f"{dx=} {dy=}")
        self._absx += dx
        self._absy += dy
        diff_img = self._last_frame.copy()
        shifted_frame = shift(frame_std, dx, dy)
        cv2.imshow("diff", diff_img - shifted_frame)
        self._last_frame = frame_std.copy()
        return shift(frame, self._absx, self._absy), (dx, dy), (self._absx, self._absy)


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
