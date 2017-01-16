#!/usr/bin/env python

from PyQt4.QtGui import *
from PyQt4.QtCore import *


class ImageBar(QLabel):
    def __init__(self, parent=None):
        super(ImageBar, self).__init__()

        self.thumbs = []

    def setThumbs(self, thumbs):
        self.thumbs = thumbs
        self.updateImage()

    def paintEvent(self, event):
        h = self.thumbs[0].height()
        w = self.thumbs[0].width()
        pw = self.width()
        print(self.size())
        nframes = int(pw/w) + 1
        pixmap = QPixmap(self.size())#pw,h)
        painter = QPainter()
        painter.begin(pixmap)
        for i in range(nframes):
            f = i*len(self.thumbs)/nframes
            painter.drawImage(i*w,0, self.thumbs[f])
        painter.end()

    def updateImage(self):
        self.repaint()

#    def resizeEvent(self, event):
#        if len(self.thumbs):
#            self.updateImage()
        

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
    window.resize(300,50)
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
        thumbw = w*thumbh/h
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

        
