#!/usr/bin/env python3

import math
import sys
from logging import DEBUG, WARN, basicConfig, getLogger, INFO

import cv2
import numpy as np

from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt6.QtGui import QImage, QPixmap, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
)

from trainscanner import pass1
from trainscanner.widget import cv2toQImage
from trainscanner import diffview, Region, FramePosition


class Worker(QObject):

    frameRendered = pyqtSignal(QImage)
    finished = pyqtSignal(bool)
    progress = pyqtSignal(int)

    def __init__(self, argv):
        super(Worker, self).__init__()
        self._isRunning = True
        self.pass1 = pass1.Pass1(argv=argv)
        self.v = diffview(
            focus=Region(
                self.pass1.params.focus[0],
                self.pass1.params.focus[1],
                self.pass1.params.focus[2],
                self.pass1.params.focus[3],
            )
        )
        self.motions_plot = []  # リアルタイムプロット用のデータ
        self.last_plot_update_time = 0  # 最後のプロット更新時刻
        self.plot_update_interval = 0.1  # プロット更新間隔（秒）

    # def view(self, frameposition: pass1.FramePosition) -> None:
    #     diff = self.v.view(frameposition)
    #     if diff is not None:
    #         qimage = cv2toQImage(diff)
    #         if not qimage.isNull():
    #             self.frameRendered.emit(qimage)

    #     self.motions_plot.append(
    #         [frameposition.velocity[0], frameposition.velocity[1], frameposition.value]
    #     )
    #     self.motionDataUpdated.emit(self.motions_plot)

    def task(self):
        if not self._isRunning:
            self._isRunning = True

        # self.pass1.before() is a generator.
        for num, den in self.pass1.cue():
            if den:
                self.progress.emit(num * 100 // den)

        self.pass1.run(hook=self.view)

        successful = len(self.pass1.framepositions) > 0
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
        # 無効な画像をスキップ（これが重要な修正）
        if image.isNull() or image.width() == 0 or image.height() == 0:
            return

        # it is called only when the pixmap is really updated by the thread.
        pixmap = QPixmap.fromImage(image)
        # pixmapが有効でない場合はスキップ
        if pixmap.isNull():
            return

        self.image_pane.setPixmap(pixmap)

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
