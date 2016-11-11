import time, sys
from PyQt4.QtCore  import *
from PyQt4.QtGui import *

class Worker(QObject):
    'Object managing the simulation'

    stepIncreased = pyqtSignal(int)

    def __init__(self):
        super(Worker, self).__init__()
        self._step = 0
        self._isRunning = True
        self._maxSteps = 20

    def task(self):
        if not self._isRunning:
            self._isRunning = True
            self._step = 0

        while self._step  < self._maxSteps  and self._isRunning == True:
            self._step += 1
            self.stepIncreased.emit(self._step)
            time.sleep(0.1)

        print "finished..."

    def stop(self):
        self._isRunning = False


class SimulationUi(QDialog):
    def __init__(self):
        super(SimulationUi, self).__init__()

        self.btnStart = QPushButton('Start')
        self.btnStop = QPushButton('Stop')
        self.currentStep = QSpinBox()

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.btnStart)
        self.layout.addWidget(self.btnStop)
        self.layout.addWidget(self.currentStep)
        self.setLayout(self.layout)

        self.thread = QThread()
        self.thread.start()

        self.worker = Worker()
        self.worker.moveToThread(self.thread)
        self.worker.stepIncreased.connect(self.currentStep.setValue)

        self.btnStop.clicked.connect(lambda: self.worker.stop())
        self.btnStart.clicked.connect(self.worker.task)

        self.finished.connect(self.stop_thread)

    def stop_thread(self):
        self.worker.stop()
        self.thread.quit()
        self.thread.wait()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    simul = SimulationUi()
    simul.show()
    sys.exit(app.exec_())
