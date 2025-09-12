#!/usr/bin/env python3

import math
import sys
from logging import DEBUG, WARN, basicConfig, getLogger, INFO

import cv2
import numpy as np
import os

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
    QHBoxLayout,
)

# matplotlibのバックエンドをQt6に設定
import matplotlib

matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from trainscanner import pass1
from trainscanner.widget import cv2toQImage
from trainscanner import diffview, Region, FramePosition


class Worker(QObject):

    frameRendered = pyqtSignal(QImage)
    finished = pyqtSignal(bool)
    progress = pyqtSignal(int)
    motionDataUpdated = pyqtSignal(list)  # [dx, dy, value] のリストを送信

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

    def view(self, frameposition: pass1.FramePosition) -> None:
        diff = self.v.view(frameposition)
        if diff is not None:
            qimage = cv2toQImage(diff)
            if not qimage.isNull():
                self.frameRendered.emit(qimage)

        self.motions_plot.append(
            [frameposition.velocity[0], frameposition.velocity[1], frameposition.value]
        )
        self.motionDataUpdated.emit(self.motions_plot)

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

        # デバッグモードの検出
        self.debug_mode = "--debug" in argv

        self.btnStop = QPushButton("Stop")
        self.image_pane = QLabel()

        self.progress = QProgressBar(self)

        # デバッグモード用のプロットウィジェット
        if self.debug_mode:
            self.setup_debug_plot()
            # デバッグモード時はウィンドウサイズを大きく
            self.resize(1200, 600)

        # レイアウトの設定
        if self.debug_mode:
            # デバッグモードでは横並びレイアウト
            main_layout = QHBoxLayout()

            # 左側：画像表示
            left_layout = QVBoxLayout()
            left_layout.addWidget(self.btnStop)
            left_layout.addWidget(self.progress)
            left_layout.addWidget(self.image_pane)

            # 右側：プロット
            main_layout.addLayout(left_layout)
            main_layout.addWidget(self.plot_canvas)

            self.setLayout(main_layout)
        else:
            # 通常モードでは縦並びレイアウト
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

        # デバッグモード用の接続
        if self.debug_mode:
            self.worker.motionDataUpdated.connect(self.update_plot)

        self.terminate = terminate
        self.btnStop.clicked.connect(lambda: self.worker.stop())
        self.btnStop.clicked.connect(self.terminateIt)
        self.terminated = False
        self.success = False

        # ショートカットの設定
        close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        close_shortcut.activated.connect(self.close)

    def setup_debug_plot(self):
        """デバッグモード用のプロットウィジェットを設定"""
        self.figure = Figure(figsize=(8, 6))
        self.plot_canvas = FigureCanvas(self.figure)
        self.plot_canvas.setMinimumSize(400, 300)

        # プロット用のデータ
        self.motion_data = []
        # プロット更新の制御
        self.plot_updating = False  # プロット更新中フラグ

    def update_plot(self, motions_plot_data):
        """リアルタイムでモーションプロットを更新"""
        if not self.debug_mode or not motions_plot_data:
            return

        # 前回のプロット更新が完了していない場合はスキップ
        if self.plot_updating:
            return

        # プロット更新開始
        self.plot_updating = True

        try:
            # データを更新
            self.motion_data = motions_plot_data

            # プロットをクリア
            self.figure.clear()

            # データがある場合のみプロット
            if len(self.motion_data) > 1:
                data = np.array(self.motion_data)
                frames = np.arange(len(data))

                # 2つのサブプロット作成：上下に配置
                # 上：X, Y変位を同じパネルに
                ax1 = self.figure.add_subplot(211)
                ax1.plot(frames, data[:, 0], "b-", linewidth=1, label="X displacement")
                ax1.plot(frames, data[:, 1], "r-", linewidth=1, label="Y displacement")
                ax1.set_ylabel("Displacement (px)")
                ax1.set_title("Motion Analysis (Real-time)")
                ax1.grid(True, alpha=0.3)
                ax1.legend()

                # 下：マッチング値（value）
                ax2 = self.figure.add_subplot(212)
                ax2.plot(frames, data[:, 2], "g-", linewidth=1, label="Match value")
                ax2.set_ylabel("Match value")
                ax2.set_xlabel("Frame number")
                ax2.grid(True, alpha=0.3)
                ax2.legend()

                # レイアウト調整
                self.figure.tight_layout()

            # キャンバスを更新
            self.plot_canvas.draw()

        finally:
            # プロット更新完了
            self.plot_updating = False

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
        self.success = successful
        # デバッグモードの場合はプロットを残すため自動で閉じない
        if not self.debug_mode:
            self.close()
        else:
            # デバッグモードの場合はボタンテキストを変更し、動作も変更
            self.btnStop.setText("Close")
            # 古い接続を切断
            self.btnStop.clicked.disconnect()
            # 新しい接続を設定（正常終了として扱う）
            self.btnStop.clicked.connect(self.close)

    def closeEvent(self, event):
        # 処理が正常に完了している場合は、terminatedをFalseに設定
        # これにより、Stitchステップに進むことができる
        if self.success:
            self.terminated = False
        else:
            # 処理が完了していない場合は中断として扱う
            self.terminated = True
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
