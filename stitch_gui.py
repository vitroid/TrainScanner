#!/usr/bin/env python3

from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QDialog, QApplication, QProgressBar, QVBoxLayout, QScrollArea
from PyQt5.QtGui     import QImage, QPixmap, QPainter
from PyQt5.QtCore    import QObject, pyqtSignal, QThread, Qt, QPoint

import stitch
import math
import numpy as np
import cv2
import sys
import logging

class Renderer(QObject):
    frameRendered = pyqtSignal(QImage)  # it is target of emit()
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self, parent=None, stitcher=None, preview_ratio=1.0):
        super(Renderer, self).__init__(parent)
        self.stitcher = stitcher
        self._isRunning = True
        self.preview_ratio = preview_ratio
            

    def cv2toQImage(self,image):
        tmp = np.zeros_like(image[:,:,0])
        tmp = image[:,:,0].copy()
        image[:,:,0] = image[:,:,2]
        image[:,:,2] = tmp

                
    def task(self):
        if not self._isRunning:
            self._isRunning = True

        for num,den in self.stitcher.before():
            self.progress.emit(num*100//den)
        for num,den in self.stitcher.loop():
            if not self._isRunning:
                break
        #while self._isRunning == True:
        #    result = self.stitcher.onestep()
            canvas = self.stitcher.image #.copy()
            height, width = canvas.shape[0:2]
            h = int(height*self.preview_ratio)
            w = int(width *self.preview_ratio)
            resized = cv2.resize(canvas, (w, h), interpolation = cv2.INTER_CUBIC)
            self.cv2toQImage(resized)
            image = QImage(resized.data, w, h, w*3, QImage.Format_RGB888)
            self.frameRendered.emit(image)
        #    num,den = self.stitcher.getProgress()
            self.progress.emit(num*100//den)
            
        #    if result is not None:
        #        break
                        
        self.stitcher.after()
        self.stitcher.done()
        self.finished.emit()
        
    def stop(self):
        self._isRunning = False


class ExtensibleCanvasWidget(QWidget):
    def __init__(self, width, height, parent=None):
        super(ExtensibleCanvasWidget, self).__init__(parent)

        self.pixmap = QPixmap()

        self.setWindowTitle("ExtensibleCanvas")
        self.setCursor(Qt.CrossCursor)
        #This is the initial paint size
        self.resize(width, height)

    def paintEvent(self, event):
        #get the "paint" region"
        #paint is the body image of the widget
        #it is called again and again (who calls it?)
        #This just put the pixmap on the "paint"
        #perhaps the thread calls it.
        #It is called even when the image is just scrolled..... Redundant.
        #No it is required. Otherwise image disappears during scrolling.
        painter = QPainter(self)
        #Always resize. Is it ok here? NO
        #self.resize(self.pixmap.size())
        painter.drawPixmap(QPoint(), self.pixmap)
        #What if the pixmap size is different from painter size?
        #Paint does not expand even if the pixmap becomes larger and larger.
        #So you need resize() it.


    def updatePixmap(self, image):
        self.pixmap = QPixmap.fromImage(image)
        self.update()



    #This will be the trigger for the first rendering
    #def resizeEvent(self, event):
    #    self.thread.render(self.size())


class StitcherUI(QDialog):
    thread_invoker = pyqtSignal()

    def __init__(self, argv, terminate, parent=None):
        super(StitcherUI, self).__init__(parent)
        self.setWindowTitle("Stitcher Preview")
        stitcher = stitch.Stitcher(argv=argv)
        self.stitcher = stitcher
        #determine the shrink ratio to avoid too huge preview
        preview_ratio = 1.0
        if stitcher.image.shape[1] > 10000:
            preview_ratio = 10000.0 / stitcher.image.shape[1]
        if stitcher.image.shape[0]*preview_ratio > 500:
            preview_ratio = 500.0 / stitcher.image.shape[0]
        self.terminate = terminate
        self.thread = QThread()
        self.thread.start()

        self.worker = Renderer(stitcher=stitcher, preview_ratio=preview_ratio)
        #it might be too early.
        
        #determine the window size
        height,width = stitcher.image.shape[0:2]
        height = int(height*preview_ratio)
        #determine the preview area size
        width = int(width*preview_ratio)

        self.scrollArea = QScrollArea()
        #self.scrollArea.setMaximumHeight(1000)
        self.largecanvas = ExtensibleCanvasWidget(width, height)
        #print(width,height)
        self.worker.frameRendered.connect(self.largecanvas.updatePixmap)
        #Do not close the window when finished.
        #self.worker.finished.connect(self.finishIt)
        self.worker.moveToThread(self.thread)
        self.thread_invoker.connect(self.worker.task)
        self.thread_invoker.emit()

        self.scrollArea.setWidget(self.largecanvas)
        self.scrollArea.setMinimumHeight(500) #self.largecanvas.sizeHint().height())
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.btnStop = QPushButton('Stop')
        self.btnStop.clicked.connect(lambda: self.worker.stop())
        self.btnStop.clicked.connect(self.terminateIt)
        
        self.progress = QProgressBar(self)
        self.worker.progress.connect(self.progress.setValue)
        
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.btnStop)
        self.layout.addWidget(self.progress)
        self.layout.addWidget(self.scrollArea)
        self.layout.addStretch(1)
        self.setLayout(self.layout)
        

        
    def terminateIt(self):
        self.close()
        if self.terminate:
            sys.exit(1)  #terminated
        
    def finishIt(self):
        self.close()
        
    def closeEvent(self, event):
        self.stop_thread()
        
    def stop_thread(self):
        logger = logging.getLogger()
        self.worker.stop()
        self.thread.quit()
        self.thread.wait()
        logger.debug("Stitch_gui thread stopped.")


if __name__ == '__main__':
    debug =False
    if debug:
        logging.basicConfig(level=logging.DEBUG,
                            #filename='log.txt',
                            format="%(asctime)s %(levelname)s %(message)s")
    else:
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")

    import sys

    app = QApplication(sys.argv)
    win = StitcherUI(sys.argv, True)
    win.setMaximumHeight(500)
    win.showMaximized()
    #win.show()
    win.raise_()
    sys.exit(app.exec_())
