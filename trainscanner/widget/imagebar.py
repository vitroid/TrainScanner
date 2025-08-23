#!/usr/bin/env python3

import sys
import numpy as np
import cv2

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication, QFrame, QLabel

from trainscanner.widget import cv2toQImage


class ImageBar(QLabel):
    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.thumbs = []
        self.setFixedHeight(100)
        self.transformer = lambda x: x  # no conversion
        self.minwidth = 5  # Minimum width of a slit

    def paintEvent(self, event):
        if not self.thumbs:
            return

        painter = QPainter(self)
        destwidth = self.width()
        division = len(self.thumbs)
        slit_width = max(self.minwidth, destwidth // division + 1)

        # スリット幅が最小幅より小さい場合、分割数を調整
        if slit_width == self.minwidth:
            division = destwidth // slit_width - 1

        for slit in range(division):
            point = QPoint(slit * destwidth // division, 0)
            thumb = self.transformer(self.thumbs[slit * len(self.thumbs) // division])

            if thumb.width() > slit_width:
                # 画像がスリット幅より大きい場合は中央を切り出し
                w0 = (thumb.width() - slit_width) // 2
                thumb = thumb.copy(w0, 0, slit_width, thumb.height())

            painter.drawImage(point, thumb)

    def setTransformer(self, func):
        self.transformer = func

    def setThumbs(self, thumbs):
        self.thumbs = thumbs
        self.repaint()


def main():
    app = QApplication(sys.argv)
    window = ImageBar()
    window.resize(300, 100)
    window.show()

    import trainscanner.video as video

    vl = video.VideoLoader("examples/sample2.mov")
    thumbs = []

    while True:
        nframe, frame = vl.next()
        if nframe == 0:
            break

        # サムネイルの作成
        thumbh = 100
        thumbw = frame.shape[1] * thumbh // frame.shape[0]
        thumb = cv2.resize(frame, (thumbw, thumbh), interpolation=cv2.INTER_CUBIC)
        thumbs.append(cv2toQImage(thumb))

        # 9フレームスキップ
        for _ in range(9):
            if vl.skip() == 0:
                break
        else:
            continue
        break

    window.setThumbs(thumbs)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
