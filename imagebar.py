#http://stackoverflow.com/questions/24106903/resizing-qpixmap-while-maintaining-aspect-ratio


from PyQt4 import QtGui, QtCore
import sys
from PyQt4.QtCore import Qt

class ImageBar(QtGui.QLabel):
    def __init__(self):
        super(ImageBar, self).__init__()
        self.setFrameStyle(QtGui.QFrame.StyledPanel)
        self.thumbs = []
        self.setFixedHeight(100)
        #self._prepareImage()

    def paintEvent(self, event):
        self._prepareImage()
    
    def _prepareImage(self):
        """
        set the pixmap here.
        """
        painter = QtGui.QPainter(self)
        if len(self.thumbs) == 0:
            return
        h = self.thumbs[0].height()
        w = self.thumbs[0].width() + 5
        pw = self.width()
        nframes = int(pw/w) + 1
        for i in range(nframes):
            f = i*len(self.thumbs)/nframes
            point = QtCore.QPoint(i*w,0)
            painter.drawImage(point, self.thumbs[f])

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
    return QtGui.QImage(cv2image.data, width, height, width*3, QtGui.QImage.Format_RGB888)

        

def main():
    import sys
    app = QtGui.QApplication(sys.argv)
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

        
