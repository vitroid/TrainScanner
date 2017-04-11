#!/usr/bin/env python3

from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QDialog, QApplication, QProgressBar, QVBoxLayout, QScrollArea
from PyQt5.QtGui     import QImage, QPixmap, QPainter
from PyQt5.QtCore    import QObject, pyqtSignal, QThread, Qt, QPoint

import math
import numpy as np
import cv2
import sys
import logging

#from QTiledImage import QTiledImage
from tiledimage import cachedimage as ci
from trainscanner.scaledcanvas import ScaledCanvas
from trainscanner import stitch


#It is run in the thread.
class Renderer(QObject):
    #frameRendered = pyqtSignal(QImage)  # it is target of emit()
    tileRendered  = pyqtSignal(tuple, np.ndarray)
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self, parent=None, stitcher=None):
        super(Renderer, self).__init__(parent)
        self.stitcher = stitcher
        self._isRunning = True
        #Dirty signal handler
        self.stitcher.canvas.set_hook(self.signal_sender)

    def signal_sender(self, pos, image):
        self.tileRendered.emit(pos, image)
                
    def task(self):
        if not self._isRunning:
            self._isRunning = True

        for num,den in self.stitcher.before():
            self.progress.emit(num*100//den)
        for num,den in self.stitcher.loop():
            if not self._isRunning:
                break
            self.progress.emit(num*100//den)
                        
        self.stitcher.after()
        self.finished.emit()
        
    def stop(self):
        self._isRunning = False
        #self.stitcher.canvas.add_hook(None)
        

class ExtensibleCanvasWidget(QLabel):
    def __init__(self, parent=None, preview_ratio=1.0):
        super(ExtensibleCanvasWidget, self).__init__(parent)
        self.preview = ScaledCanvas(scale = preview_ratio)
        
    
    def updatePixmap(self, pos, image):
        #self.count += 1
        #if self.count == 7:
        #    self.count = 0
        self.preview.put_image(pos, image)
        fullimage = self.preview.get_image()[:,:,::-1].copy()  #reverse order
        h,w = fullimage.shape[:2]
        self.resize(w, h)
        qimage = QImage(fullimage.data, w, h, w*3, QImage.Format_RGB888)
        self.setPixmap(QPixmap.fromImage(qimage))
        self.update()



class StitcherUI(QDialog):
    thread_invoker = pyqtSignal()

    def __init__(self, argv, terminate, parent=None):
        super(StitcherUI, self).__init__(parent)
        self.setWindowTitle("Stitcher Preview")
        stitcher = stitch.Stitcher(argv=argv)
        tilesize = (128,512) #can be smaller for smaller machine
        cachesize = 10
        stitcher.set_canvas(ci.CachedImage("new", dir=stitcher.cachedir, tilesize=tilesize, cachesize=cachesize))
        self.stitcher = stitcher
        #determine the shrink ratio to avoid too huge preview
        preview_ratio = 1.0
        if stitcher.dimen[0] > 10000:
            preview_ratio = 10000.0 / stitcher.dimen[0]
        if stitcher.dimen[1]*preview_ratio > 500:
            preview_ratio = 500.0 / stitcher.dimen[1]
        self.terminate = terminate
        self.thread = QThread()
        self.thread.start()

        self.worker = Renderer(stitcher=stitcher)
        #it might be too early.
        
        #determine the window size
        width,height = stitcher.dimen[:2]
        height = int(height*preview_ratio)
        #determine the preview area size
        width = int(width*preview_ratio)

        self.scrollArea = QScrollArea()
        #self.scrollArea.setMaximumHeight(1000)
        self.largecanvas = ExtensibleCanvasWidget(preview_ratio=preview_ratio)
        #print(width,height)
        #self.worker.frameRendered.connect(self.largecanvas.updatePixmap)
        self.worker.tileRendered.connect(self.largecanvas.updatePixmap)
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


def main():
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


if __name__ == '__main__':
    main()
