#!/usr/bin/env python3

from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QDialog, QApplication, QProgressBar, QVBoxLayout
from PyQt5.QtGui     import QImage, QPixmap
from PyQt5.QtCore    import QObject, pyqtSignal, QThread
import sys
import time
import numpy as np
from trainscanner import pass1

def cv2toQImage(cv2image):
    """
    It breaks the original image
    """
    height, width = cv2image.shape[0:2]
    tmp = np.zeros_like(cv2image[:,:,0])
    tmp = cv2image[:,:,0].copy()
    cv2image[:,:,0] = cv2image[:,:,2]
    cv2image[:,:,2] = tmp
    return QImage(cv2image.data, width, height, width*3, QImage.Format_RGB888)

class Worker(QObject):

    frameRendered = pyqtSignal(QImage)
    finished      = pyqtSignal()
    progress      = pyqtSignal(int)

    def __init__(self, argv):
        super(Worker, self).__init__()
        self._isRunning = True
        self.pass1 = pass1.Pass1(argv=argv)

    def task(self):
        if not self._isRunning:
            self._isRunning = True

        #self.pass1.before() is a generator.
        for num,den in self.pass1.before():
            if den:
                self.progress.emit(num*100//den)
        
        for img in self.pass1.iter():
            if not self._isRunning:
                break
            self.frameRendered.emit(cv2toQImage(img))

        self.pass1.after()
        self.finished.emit()

    def stop(self):
        self._isRunning = False


class MatcherUI(QDialog):
    thread_invoker = pyqtSignal()
    
    def __init__(self, argv, terminate=False):
        super(MatcherUI, self).__init__()

        self.btnStop = QPushButton('Stop')
        self.image_pane = QLabel()

        self.progress = QProgressBar(self)
        
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.btnStop)
        self.layout.addWidget(self.progress)
        self.layout.addWidget(self.image_pane)
        self.setLayout(self.layout)

        self.thread = QThread()
        self.thread.start()

        self.worker = Worker(argv)
        self.worker.moveToThread(self.thread)
        self.thread_invoker.connect(self.worker.task)
        self.thread_invoker.emit()
        
        self.worker.frameRendered.connect(self.updatePixmap)
        self.worker.finished.connect(self.finishIt)
        self.worker.progress.connect(self.progress.setValue)

        self.terminate = terminate
        self.btnStop.clicked.connect(lambda: self.worker.stop())
        self.btnStop.clicked.connect(self.terminateIt)
        self.terminated = False
        
    def updatePixmap(self, image):
        #it is called only when the pixmap is really updated by the thread.
        #resize image in advance.
        #w,h = image.width(), image.height()
        #scaled_image = image.scaled(int(w*self.preview_ratio), int(h*self.preview_ratio))
        pixmap = QPixmap.fromImage(image)
        self.image_pane.setPixmap(pixmap)
        #is it ok here?
        self.update()

    def terminateIt(self):
        self.close()
        if self.terminate:
            sys.exit(1)  #terminated
        self.terminated = True
        
    def finishIt(self):
        self.close()
        
    def closeEvent(self, event):
        self.stop_thread()
        
    def stop_thread(self):
        self.worker.stop()
        self.thread.quit()
        self.thread.wait()

def main():
    app = QApplication(sys.argv)
    match = MatcherUI(sys.argv, True)
    match.setWindowTitle("Matcher Preview")
    match.show()
    match.raise_()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
