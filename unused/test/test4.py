import sys
from PyQt4 import QtGui, QtCore

class QExampleLabel (QtGui.QLabel):
    def __init__(self, parentQWidget = None):
        super(QExampleLabel, self).__init__(parentQWidget)
        self.initUI()

    def initUI (self):
        self.setPixmap(QtGui.QPixmap('by.png'))

    def mousePressEvent (self, eventQMouseEvent):
        self.originQPoint = eventQMouseEvent.pos()
        self.currentQRubberBand = QtGui.QRubberBand(QtGui.QRubberBand.Rectangle, self)
        self.currentQRubberBand.setGeometry(QtCore.QRect(self.originQPoint, QtCore.QSize()))
        self.currentQRubberBand.show()

    def mouseMoveEvent (self, eventQMouseEvent):
        self.currentQRubberBand.setGeometry(QtCore.QRect(self.originQPoint, eventQMouseEvent.pos()).normalized())

    def mouseReleaseEvent (self, eventQMouseEvent):
        self.currentQRubberBand.hide()
        currentQRect = self.currentQRubberBand.geometry()
        self.currentQRubberBand.deleteLater()
        cropQPixmap = self.pixmap().copy(currentQRect)
        cropQPixmap.save('output.png')

if __name__ == '__main__':
    myQApplication = QtGui.QApplication(sys.argv)
    myQExampleLabel = QExampleLabel()
    myQExampleLabel.show()
    sys.exit(myQApplication.exec_())
