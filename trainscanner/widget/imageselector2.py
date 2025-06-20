#!/usr/bin/env python

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication, QSlider, QVBoxLayout, QWidget

from trainscanner.widget import qrangeslider as rs
from trainscanner.widget.imagebar import ImageBar
from trainscanner.widget import cv2toQImage


class ImageSelector2(QWidget):
    resized = pyqtSignal(int)

    def __init__(self, parent=None):
        super(ImageSelector2, self).__init__()
        layout = QVBoxLayout()
        self.imagebar = ImageBar()  # Difference from IS1
        self.slider = rs.QRangeSlider(splitterWidth=10)
        self.slider.setRange(0, 0)
        layout.addWidget(self.imagebar)
        layout.addWidget(self.slider)
        layout.setSpacing(0)
        self.setLayout(layout)

    def setThumbs(self, thumbs):
        if len(thumbs) < 2:
            return

        # move the slide bar and trim indicator
        lastlen = len(self.imagebar.thumbs)
        lasthead = self.slider.start()
        lasttail = self.slider.end()

        self.imagebar.setThumbs(thumbs.copy())
        if lastlen == len(thumbs):
            return
        self.slider.setMax(len(thumbs) - 1)
        self.slider.setStart(lasthead)
        if lastlen - 1 <= lasttail:
            self.slider.setEnd(len(thumbs) - 1)
        else:
            self.slider.setEnd(lasttail)


def main():
    import sys

    app = QApplication(sys.argv)
    window = ImageSelector2()
    window.resize(300, 50)
    window.show()

    import cv2

    from trainscanner import video

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
