#http://stackoverflow.com/questions/24106903/resizing-qpixmap-while-maintaining-aspect-ratio


from PyQt4 import QtGui, QtCore
import sys
from PyQt4.QtCore import Qt

class Label(QtGui.QLabel):
    def __init__(self, img):
        super(Label, self).__init__()
        self.setFrameStyle(QtGui.QFrame.StyledPanel)
        self.pixmap = QtGui.QPixmap(img)

    def paintEvent(self, event):
        size = self.size()
        painter = QtGui.QPainter(self)
        point = QtCore.QPoint(0,0)
        scaledPix = self.pixmap.scaled(size, Qt.KeepAspectRatio, transformMode = Qt.SmoothTransformation)
        # start painting the label from left upper corner
        point.setX((size.width() - scaledPix.width())/2)
        point.setY((size.height() - scaledPix.height())/2)
        print point.x(), ' ', point.y()
        painter.drawPixmap(point, scaledPix)
        
    def changePixmap(self, img):
        self.pixmap = QtGui.QPixmap(img)
        self.repaint() # repaint() will trigger the paintEvent(self, event), this way the new pixmap will be drawn on the label
Y

class Main(QtGui.QWidget):          
    def __init__(self):
        super(Main, self).__init__()
        layout = QtGui.QGridLayout()
        label = Label(r"by.png")
        layout.addWidget(label)
        layout.setRowStretch(0,1)
        layout.setColumnStretch(0,1)

        self.setLayout(layout)
        self.show()

if __name__ =="__main__":
    app = QtGui.QApplication(sys.argv)
    widget = Main()
    sys.exit(app.exec_())
