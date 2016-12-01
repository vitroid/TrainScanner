#!/usr/bin/env python3

from PyQt5.QtWidgets import QLabel, QApplication, QFrame
from PyQt5.QtGui     import QPainter
from PyQt5.QtCore    import QPoint

import sys

class ImageBar(QLabel):
    def __init__(self):
        super(ImageBar, self).__init__()
        self.setFrameStyle(QFrame.StyledPanel)
        self.thumbs = []
        self.setFixedHeight(100)
        self.transformer=lambda x:x  #no conversion
        #self._prepareImage()

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
        first = self.transformer(self.thumbs[0])
        h = first.height()
        w = first.width() + 2
        pw = self.width()
        nframes = pw//w + 1
        for i in range(nframes):
            f = i*len(self.thumbs)//nframes
            point = QPoint(i*w,0)
            painter.drawImage(point, self.transformer(self.thumbs[f]))

    def setThumbs(self,thumbs):
        self.thumbs = thumbs
        self.repaint() # repaint() will trigger the paintEvent(self, event), this way the new pixmap will be drawn on the label


def cv2toQImage(cv2image):
    """
    It breaks the original image
    """
    import numpy as np
    height, width = cv2image.shape[0:2]
    tmp = np.zeros_like(cv2image[:,:,0])
    tmp = cv2image[:,:,0].copy()
    cv2image[:,:,0] = cv2image[:,:,2]
    cv2image[:,:,2] = tmp
    return QImage(cv2image.data, width, height, width*3, QImage.Format_RGB888)

        

def main():
    import sys
    app = QApplication(sys.argv)
    window = ImageBar()
    window.resize(300,100)
    window.show()

    import cv2
    cap      = cv2.VideoCapture("sample2.mov")
    ret = True
    thumbs = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        h,w = frame.shape[0:2]
        thumbh = 100
        thumbw = w*thumbh//h
        thumb = cv2.resize(frame,(thumbw,thumbh),interpolation = cv2.INTER_CUBIC)
        thumbs.append(cv2toQImage(thumb))
        for i in range(9):
            ret = cap.grab()
            if not ret:
                break
        if not ret:
            break
    window.setThumbs(thumbs)
        
        
    sys.exit(app.exec_())    

if __name__ == "__main__":
    main()

        
