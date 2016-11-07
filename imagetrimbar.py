#http://stackoverflow.com/questions/24106903/resizing-qpixmap-while-maintaining-aspect-ratio


from PyQt4 import QtGui, QtCore
import sys
from PyQt4.QtCore import Qt
from imagebar import ImageBar

class ImageTrimBar(ImageBar):
    trim_changed = QtCore.pyqtSignal(float)

    def __init__(self):
        super(ImageTrimBar, self).__init__()
        self.currentQRubberBand = QtGui.QRubberBand(QtGui.QRubberBand.Rectangle, self)
        self.trim = 0.0
        #pal = QtGui.QPalette()
        #pal.setBrush(QtGui.QPalette.Highlight, QtGui.QBrush(Qt.red));
        #pal.setBrush(QtGui.QPalette.Base, QtGui.QBrush(Qt.red));
        #pal.setBrush(QtGui.QPalette.Foreground, QtGui.QBrush(Qt.red));
        #self.currentQRubberBand.setPalette(pal);

    def mousePressEvent (self, eventQMouseEvent):
        x = eventQMouseEvent.x()
        y = self.height()
        self.currentQRubberBand.setGeometry(QtCore.QRect(0,0,x,y))
        self.currentQRubberBand.show()
        #self.trim_changed.emit(float(x) / self.width())

    def mouseMoveEvent (self, eventQMouseEvent):
        x = eventQMouseEvent.x()
        y = self.height()
        self.currentQRubberBand.setGeometry(QtCore.QRect(0,0,x,y).normalized())
        #self.trim_changed.emit(float(x) / self.width())

    def mouseReleaseEvent (self, eventQMouseEvent):
        #self.currentQRubberBand.hide()
        #currentQRect = self.currentQRubberBand.geometry()
        #self.currentQRubberBand.deleteLater()
        x = eventQMouseEvent.x()
        self.trim_changed.emit(float(x) / self.width())


    def externalAction(self, x):
        """
        invoked when trim position is changed/the widget is resized
        """
        y = self.height()
        self.currentQRubberBand.setGeometry(QtCore.QRect(0,0,x,y).normalized())

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
    window = ImageTrimBar()
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

        
