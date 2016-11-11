#!/usr/bin/env python

#Modified from Mandelbrot.py
#http://ftp.ics.uci.edu/pub/centos0/ics-custom-build/BUILD/PyQt-x11-gpl-4.7.2/examples/threads/mandelbrot.py

#This is a skeleton for a real time canvas. It is not sure it is extensible.

from PyQt4 import QtCore, QtGui

class RenderThread(QtCore.QThread):
    renderedImage = QtCore.pyqtSignal(QtGui.QImage)  # it is target of emit()

    def __init__(self, parent=None):
        super(RenderThread, self).__init__(parent)

        self.mutex = QtCore.QMutex()
        self.condition = QtCore.QWaitCondition()

        self.resultSize = QtCore.QSize()

        self.restart = False
        self.abort = False


    def __del__(self):
        self.mutex.lock()
        self.abort = True
        self.condition.wakeOne()
        self.mutex.unlock()

        self.wait()

    def render(self, resultSize):
        locker = QtCore.QMutexLocker(self.mutex)

        self.resultSize = resultSize

        if not self.isRunning():
            self.start(QtCore.QThread.LowPriority)
        else:
            self.restart = True
            self.condition.wakeOne()

    def run(self):
        while True:
            self.mutex.lock()
            resultSize = self.resultSize
            self.mutex.unlock()


            for loop in range(100):
                resultSize.setWidth(resultSize.width() + 100)
                image = QtGui.QImage(resultSize, QtGui.QImage.Format_RGB32)
                for y in range(resultSize.height()):
                    for x in range(resultSize.width()):
                        r = x + y + loop
                        g = r + 80
                        b = g + 80
                        r %= 256
                        g %= 256
                        b %= 256
                        image.setPixel(x, y, QtGui.qRgb(r,g,b))
                if not self.restart:
                    self.renderedImage.emit(image)
                        

            self.mutex.lock()
            if not self.restart:
                self.condition.wait(self.mutex)
            self.restart = False
            self.mutex.unlock()


class ExtensibleCanvasWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        super(ExtensibleCanvasWidget, self).__init__(parent)

        self.thread = RenderThread()
        self.pixmap = QtGui.QPixmap()

        self.thread.renderedImage.connect(self.updatePixmap)

        self.setWindowTitle("ExtensibleCanvas")
        self.setCursor(QtCore.Qt.CrossCursor)
        #This is the initial paint size
        self.resize(550, 400)

    def paintEvent(self, event):
        #get the "paint" region"
        #paint is the body image of the widget
        #it is called again and again (who calls it?)
        #This just put the pixmap on the "paint"
        #perhaps the thread calls it.
        #It is called even when the image is just scrolled..... Redundant.
        #No it is required. Otherwise image disappears during scrolling.
        painter = QtGui.QPainter(self)
        painter.drawPixmap(QtCore.QPoint(), self.pixmap)
        #What if the pixmap size is different from painter size?
        #Paint does not expand even if the pixmap becomes larger and larger.
        #So you need resize() it.


    def updatePixmap(self, image):
        #it is called only when the pixmap is really updated by the thread.
        self.pixmap = QtGui.QPixmap.fromImage(image)
        self.update()



    #This will be the trigger for the first rendering
    def resizeEvent(self, event):
        self.thread.render(self.size())


class Example(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(Example, self).__init__(parent)

        self.setWindowTitle("Main Window")
        self.resize(400, 400)
        self.scrollArea = QtGui.QScrollArea()

        widget = ExtensibleCanvasWidget()
        self.scrollArea.setWidget(widget)
        self.setCentralWidget(self.scrollArea)
        


if __name__ == '__main__':

    import sys

    app = QtGui.QApplication(sys.argv)
    win = Example()
    win.show()
    sys.exit(app.exec_())
