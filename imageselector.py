#!/usr/bin/env python

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from imagetrimbar import ImageTrimBar

class ImageSelector(QWidget):
    resized = pyqtSignal(int)
    def __init__(self, parent=None):
        super(ImageSelector, self).__init__()
        layout = QVBoxLayout()
        self.imagebar = ImageTrimBar()
        self.imagebar.trim_changed.connect(self.leftEnd)
        self.slider   = QSlider(Qt.Horizontal)
        self.trimmed  = 0.0
        self.firstFrame = 0 #calculated
        layout.addWidget(self.imagebar)
        layout.addWidget(self.slider)
        layout.setSpacing(0)
        self.setLayout(layout)
        self.resized.connect(self.imagebar.externalAction)
        self.connect(self.slider, SIGNAL('valueChanged(int)'), self.slider_on_draw)
        
        
    def setThumbs(self, thumbs):
        #move the slide bar and trim indicator
        lastlen = len(self.imagebar.thumbs)
        lasttrim = self.trimmed * lastlen
        lastslid = self.slider.value()
        #print(lastlen,lasttrim,lastslid)

        self.imagebar.setThumbs(thumbs)
        self.slider.setRange(0,len(thumbs)-1)
        self.slider.setValue(lastslid)
        self.leftEnd(lasttrim / len(thumbs))

    def leftEnd(self, value):
        #print("LeftEnd",value)
        self.trimmed = value  #0.0 ... 1.0
        self.firstFrame = int(value * len(self.imagebar.thumbs))
        #if self.slider.value() < self.firstFrame:
        self.slider.setValue(self.firstFrame)
            
    def resizeEvent(self, event):
        self.resized.emit(int(self.trimmed*self.width()))
        #Sent to the trimbar.

    def slider_on_draw(self):
        v = self.slider.value()
        vmin = int(len(self.imagebar.thumbs) * self.trimmed)
        if v < vmin:
            self.slider.setValue(vmin)
        


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
    window = ImageSelector()
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

        
