#!/usr/bin/env python3

import sys

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication, QFrame, QLabel


class ImageBar(QLabel):
    def __init__(self):
        super(ImageBar, self).__init__()
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.thumbs = []
        self.setFixedHeight(100)
        self.transformer = lambda x,: x  # no conversion
        self.minwidth = 5  # Minimum width of a slit
        # self._prepareImage()

    def paintEvent(self, event):
        self._prepareImage()

    def setTransformer(self, func):
        self.transformer = func

    def _prepareImage(self):
        """
        set the pixmap here.
        """
        painter = QPainter(self)
        if len(self.thumbs) == 0:
            return
        destwidth = self.width()
        division = len(self.thumbs)
        NF = division
        slit_width = destwidth // division + 1
        if slit_width < self.minwidth:
            slit_width = self.minwidth
            division = destwidth // slit_width - 1
        for slit in range(division):
            point = QPoint(slit * destwidth // division, 0)
            i = slit * NF // division
            thumb = self.transformer(self.thumbs[i])
            w = thumb.width()
            h = thumb.height()
            if w > slit_width:
                w0 = (w - slit_width) // 2
                cropped = thumb.copy(w0, 0, slit_width, h)
                painter.drawImage(point, cropped)
            else:
                painter.drawImage(point, thumb)

    def setThumbs(self, thumbs):
        self.thumbs = thumbs
        self.repaint()  # repaint() will trigger the paintEvent(self, event), this way the new pixmap will be drawn on the label


def cv2toQImage(cv2image):
    """
    It breaks the original image
    """
    import numpy as np

    height, width = cv2image.shape[0:2]
    tmp = cv2image[:, :, 0].copy()
    cv2image[:, :, 0] = cv2image[:, :, 2]
    cv2image[:, :, 2] = tmp
    return QImage(cv2image.data, width, height, width * 3, QImage.Format.Format_RGB888)


def main():
    import sys

    app = QApplication(sys.argv)
    window = ImageBar()
    window.resize(300, 100)
    window.show()

    # from trainscanner import video
    import cv2
    import trainscanner.video as video

    vl = video.VideoLoader("examples/sample2.mov")
    ret = True
    thumbs = []
    while True:
        nframe, frame = vl.next()
        if nframe == 0:
            break
        h, w = frame.shape[0:2]
        thumbh = 100
        thumbw = w * thumbh // h
        thumb = cv2.resize(frame, (thumbw, thumbh), interpolation=cv2.INTER_CUBIC)
        thumbs.append(cv2toQImage(thumb))
        terminate = False
        for i in range(9):
            nframe = vl.skip()
            if nframe == 0:
                terminate = True
                break
        if terminate:
            break
    window.setThumbs(thumbs)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
