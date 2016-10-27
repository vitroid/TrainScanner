#!/usr/bin/env python

#Modified from Mandelbrot.py
#http://ftp.ics.uci.edu/pub/centos0/ics-custom-build/BUILD/PyQt-x11-gpl-4.7.2/examples/threads/mandelbrot.py

#This is a skeleton for a real time canvas. It is not sure it is extensible.

from PyQt4 import QtCore, QtGui

import stitch
import math
import numpy as np

class RenderThread(QtCore.QThread):
    renderedImage = QtCore.pyqtSignal(QtGui.QImage)  # it is target of emit()

    def __init__(self, parent=None, st=None, movie=None, istream=None):
        super(RenderThread, self).__init__(parent)
        self.mutex = QtCore.QMutex()
        self.st = st
        self.movie = movie
        self.istream = istream
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

    def cv2toQImage(self,image):
        tmp = np.zeros_like(image[:,:,0])
        tmp = image[:,:,0].copy()
        image[:,:,0] = image[:,:,2]
        image[:,:,2] = tmp
        
    def run(self):
        while True:
            self.mutex.lock()
            resultSize = self.resultSize
            self.mutex.unlock()

            self.st.stitch_begin(self.movie, self.istream)
            while True:
                result = self.st.stitch_one()
                canvas = self.st.canvas[0].copy()
                height, width = canvas.shape[0:2]
                self.cv2toQImage(canvas)
                image = QtGui.QImage(canvas.data, width, height, width*3, QtGui.QImage.Format_RGB888)
                if not self.restart:
                    #emit signal is not always processed. Why?
                    self.renderedImage.emit(image)
                if result is not None:
                    break
                        

            self.mutex.lock()
            if not self.restart:
                self.condition.wait(self.mutex)
            self.restart = False
            self.mutex.unlock()


class ExtensibleCanvasWidget(QtGui.QWidget):
    def __init__(self, parent=None, st=None, movie=None, istream=None):
        super(ExtensibleCanvasWidget, self).__init__(parent)

        self.thread = RenderThread(st=st, movie=movie, istream=istream)
        self.pixmap = QtGui.QPixmap()

        self.thread.renderedImage.connect(self.updatePixmap)

        self.setWindowTitle("ExtensibleCanvas")
        self.setCursor(QtCore.Qt.CrossCursor)
        #This is the initial paint size
        height,width = st.canvas[0].shape[0:2]
        self.resize(width, height)

    def paintEvent(self, event):
        #get the "paint" region"
        #paint is the body image of the widget
        #it is called again and again (who calls it?)
        #This just put the pixmap on the "paint"
        #perhaps the thread calls it.
        #It is called even when the image is just scrolled..... Redundant.
        #No it is required. Otherwise image disappears during scrolling.
        painter = QtGui.QPainter(self)
        #Always resize. Is it ok here? NO
        #self.resize(self.pixmap.size())
        painter.drawPixmap(QtCore.QPoint(), self.pixmap)
        #What if the pixmap size is different from painter size?
        #Paint does not expand even if the pixmap becomes larger and larger.
        #So you need resize() it.


    def updatePixmap(self, image):
        #it is called only when the pixmap is really updated by the thread.
        self.pixmap = QtGui.QPixmap.fromImage(image)
        #is it ok here?
        #self.resize(self.pixmap.size())
        self.update()



    #This will be the trigger for the first rendering
    def resizeEvent(self, event):
        self.thread.render(self.size())


class Example(QtGui.QMainWindow):
    def __init__(self, parent=None, st=None, movie=None, istream=None):
        super(Example, self).__init__(parent)

        self.setWindowTitle("Main Window")
        height,width = st.canvas[0].shape[0:2]
        self.resize(400,height)
        #self.setMinimumHeight(height)
        self.scrollArea = QtGui.QScrollArea()
        self.scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        widget = ExtensibleCanvasWidget(st=st, movie=movie, istream=istream)
        self.scrollArea.setWidget(widget)
        self.setCentralWidget(self.scrollArea)
        


if __name__ == '__main__':

    import sys

    import sys

    debug = False #True
    slitpos = 250
    slitwidth = 1
    film = False
    helix = False
    label= ""
    dimen = None
    # -r and -p option must be identical to pass1.py
    #(or they may be given in the input file)
    while len(sys.argv) > 1:
        if sys.argv[1] in ("-d", "--debug"):
            debug = True
        elif sys.argv[1] in ("-C", "--canvas"):
            dimen = [int(x) for x in sys.argv.pop(2).split(",")]
        elif sys.argv[1] in ("-s", "--slit"):
            slitpos = int(sys.argv.pop(2))
        elif sys.argv[1] in ("-w", "--width"):
            slitwidth = float(sys.argv.pop(2))
        elif sys.argv[1] in ("-l", "--label"):
            label = sys.argv.pop(2)
        elif sys.argv[1] in ("-F", "--film"):
            film = True
        elif sys.argv[1] in ("-H", "--helix"):
            helix = True
        elif sys.argv[1][0] == "-":
            print("Unknown option: ", sys.argv[1])
            Usage(sys.argv)
        sys.argv.pop(1)
    if dimen is None:
        stitch.Usage(sys.argv)
    #if len(sys.argv) != 2:
    if len(sys.argv) != 1:
        stitch.Usage(sys.argv)
    #movie = sys.argv[1]
    #LOG = open("{0}.pass1.log".format(movie))
    LOG = sys.stdin
    line = LOG.readline()
    movie = line.splitlines()[0] #chomp
    angle = 0
    gpts = None #np.float32([380, 350, 1680, 1715])
    crop = 0,1000
    while True:
        line = LOG.readline()
        if line[0:3] == "#-r":
            angle = -float(line.split()[1]) * math.pi / 180
        elif line[0:3] == "#-p":
            gpts  = [int(x) for x in line.split()[1].split(",")]
        elif line[0:3] == "#-c":
            crop  = [int(x) for x in line.split()[1].split(",")]
        else:
            break
    st = stitch.Stitcher(angle=angle, pers=gpts, slitpos=slitpos, slitwidth=slitwidth, scale=1, crop=crop, dimen=dimen)
    #canvas = st.stitch(movie, LOG)
    #cv2.imwrite("{0}.png".format(movie), canvas)
    #if film:
    #    import film
    #    canvas = film.filmify(canvas, label=label)
    #    movie += ".film"
    #    cv2.imwrite("{0}.jpg".format(movie), canvas)
    #if helix:
    #    import helix
    #    canvas = helix.helicify(canvas)
    #    movie += ".helix"
    #    cv2.imwrite("{0}.jpg".format(movie), canvas)

    app = QtGui.QApplication(sys.argv)
    win = Example(st=st, movie=movie, istream=LOG)
    win.show()
    sys.exit(app.exec_())
