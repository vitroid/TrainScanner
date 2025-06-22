#!/usr/bin/env python3

import sys
import time

import cv2
import numpy as np

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QPainter, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QGroupBox,
    QSizePolicy,
    QSlider,
)

from trainscanner import pass1
from trainscanner.widget import cv2toQImage


class Worker(QObject):

    frameRendered = pyqtSignal(QImage)
    finished = pyqtSignal(bool)
    progress = pyqtSignal(int)

    def __init__(self, argv):
        super(Worker, self).__init__()
        self._isRunning = True
        self.pass1 = pass1.Pass1(argv=argv)

    def task(self):
        if not self._isRunning:
            self._isRunning = True

        # self.pass1.before() is a generator.
        for num, den in self.pass1.before():
            if den:
                self.progress.emit(num * 100 // den)

        for img in self.pass1.iter():
            if not self._isRunning:
                break
            self.frameRendered.emit(cv2toQImage(img))

        successful = self.pass1.canvas is not None and len(self.pass1.tspos) > 0
        self.pass1.after()
        self.finished.emit(successful)

    def stop(self):
        self._isRunning = False


class MatcherUI(QDialog):
    thread_invoker = pyqtSignal()

    def __init__(self, argv, terminate=False):
        super(MatcherUI, self).__init__()

        self.btnStop = QPushButton("Stop")
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
        self.success = False

        # ショートカットの設定
        close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        close_shortcut.activated.connect(self.close)

    def updatePixmap(self, image):
        # it is called only when the pixmap is really updated by the thread.
        # resize image in advance.
        # w,h = image.width(), image.height()
        # scaled_image = image.scaled(int(w*self.preview_ratio), int(h*self.preview_ratio))
        pixmap = QPixmap.fromImage(image)
        self.image_pane.setPixmap(pixmap)
        # is it ok here?
        self.update()

    def terminateIt(self):
        self.close()
        if self.terminate:
            sys.exit(1)  # terminated
        self.terminated = True

    def finishIt(self, successful: bool):
        self.close()
        self.success = successful

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
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
