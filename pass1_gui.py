#!/usr/bin/env python
import time, sys
from PyQt4.QtCore  import *
from PyQt4.QtGui import *
import pass1
import sys
import numpy as np

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
    'Object managing the simulation'

    frameRendered = pyqtSignal(QImage)
    finished = pyqtSignal()

    def __init__(self):
        super(Worker, self).__init__()
        self._isRunning = True
        self.pass1 = pass1.Pass1(sys.argv)
        self.pass1.before()

    def task(self):
        if not self._isRunning:
            self._isRunning = True

        while self._isRunning == True:
            ret = self.pass1.onestep()
            if ret is None:
                break
            if ret is not True: #True means skipping frame
                self.frameRendered.emit(cv2toQImage(ret))

        #print "finished..."
        self.pass1.after()
        self.finished.emit()

    def stop(self):
        self._isRunning = False


class SimulationUi(QWidget):
    thread_invoker = pyqtSignal()
    
    def __init__(self):
        super(SimulationUi, self).__init__()

        self.btnStop = QPushButton('Stop')
        self.image_pane = QLabel()

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.btnStop)
        self.layout.addWidget(self.image_pane)
        self.setLayout(self.layout)

        self.thread = QThread()
        self.thread.start()

        self.worker = Worker()
        self.worker.moveToThread(self.thread)
        self.thread_invoker.connect(self.worker.task)
        self.thread_invoker.emit()
        
        self.worker.frameRendered.connect(self.updatePixmap)
        self.worker.finished.connect(self.finishIt)

        self.btnStop.clicked.connect(lambda: self.worker.stop())
        self.btnStop.clicked.connect(self.terminateIt)
        
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
        sys.exit(1)  #terminated
        
    def finishIt(self):
        self.close()
        
    def closeEvent(self, event):
        self.stop_thread()
        
    def stop_thread(self):
        self.worker.stop()
        self.thread.quit()
        self.thread.wait()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    simul = SimulationUi()
    simul.show()
    simul.raise_()
    sys.exit(app.exec_())
