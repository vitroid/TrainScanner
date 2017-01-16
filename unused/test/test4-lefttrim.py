#http://stackoverflow.com/questions/25795380/how-to-crop-a-image-and-save
import sys
from PyQt4 import QtGui, QtCore

class QExampleLabel (QtGui.QLabel):
    def __init__(self, parentQWidget = None):
        super(QExampleLabel, self).__init__(parentQWidget)
        self.initUI()
        self.parent = parentQWidget

    def initUI (self):
        self.setPixmap(QtGui.QPixmap('by.png'))

    def mousePressEvent (self, eventQMouseEvent):
        x = eventQMouseEvent.x()
        print(x)
        y = self.height()
        self.currentQRubberBand = QtGui.QRubberBand(QtGui.QRubberBand.Rectangle, self)
        self.currentQRubberBand.setGeometry(QtCore.QRect(0,0,x,y))
        self.currentQRubberBand.show()

    def mouseMoveEvent (self, eventQMouseEvent):
        x = eventQMouseEvent.x()
        y = self.height()
        self.currentQRubberBand.setGeometry(QtCore.QRect(0,0,x,y).normalized())

    def mouseReleaseEvent (self, eventQMouseEvent):
        self.currentQRubberBand.hide()
        currentQRect = self.currentQRubberBand.geometry()
        self.currentQRubberBand.deleteLater()
        #cropQPixmap = self.pixmap().copy(currentQRect)
        #cropQPixmap.save('output.png')

if __name__ == '__main__':
    myQApplication = QtGui.QApplication(sys.argv)
    myQExampleLabel = QExampleLabel()
    myQExampleLabel.show()
    sys.exit(myQApplication.exec_())
