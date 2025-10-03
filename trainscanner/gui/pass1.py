#!/usr/bin/env python3

import math
import sys
import time
from logging import DEBUG, WARN, basicConfig, getLogger, INFO

import cv2
import numpy as np
import os

from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt, QTimer
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
from trainscanner.image import diffview
from pyperbox import Rect, Range


class Worker(QObject):

    frameRendered = pyqtSignal(QImage)
    finished = pyqtSignal(bool)
    progress = pyqtSignal(int)
    motionDataUpdated = pyqtSignal(list)  # [dx, dy, value] のリストを送信

    def __init__(self, argv):
        super(Worker, self).__init__()
        self._isRunning = True
        self.pass1 = pass1.Pass1(argv=argv)
        self.motions_plot = []  # リアルタイムプロット用のデータ
        self.last_plot_update_time = 0  # 最後のプロット更新時刻
        self.plot_update_interval = 0.1  # プロット更新間隔（秒）
        # self.pending_frameposition = None  # 待機中のフレーム位置

    def view(self, frameposition: pass1.FramePosition) -> None:
        # 最新のフレーム位置を保存（QTimerで制御）
        # self.pending_frameposition = frameposition

        # プロット更新（頻度制限付き）
        current_time = time.time()
        if current_time - self.last_plot_update_time >= self.plot_update_interval:
            self.last_plot_update_time = current_time
            self.motions_plot.append(
                [
                    frameposition.velocity[0],
                    frameposition.velocity[1],
                    frameposition.value,
                ]
            )
            self.motionDataUpdated.emit(self.motions_plot)

    def task(self):
        if not self._isRunning:
            self._isRunning = True

        self.pass1.cue()
        # self.pass1.before() is a generator.
        # for num, den in self.pass1.cue():
        #     if not self._isRunning:
        #         self.finished.emit(False)
        #         return
        #     if den:
        #         self.progress.emit(num * 100 // den)

        # 停止チェック用のコールバックを渡す
        def stop_check():
            return not self._isRunning

        self.pass1.run(stop_callback=stop_check)
        # self.pass1.run(hook=None, stop_callback=stop_check)

        successful = len(self.pass1.framepositions) > 0
        self.pass1.after()
        self.finished.emit(successful)

    def stop(self):
        self._isRunning = False


class MatcherUI(QDialog):
    thread_invoker = pyqtSignal()

    def __init__(self, argv, terminate=False):
        super(MatcherUI, self).__init__()

        # ロガーの初期化
        self.logger = getLogger(__name__)

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

        # フレーム更新の制御（QTimer使用）
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_frame_display)
        self.update_timer.start(100)  # 100ms間隔で更新（10FPS）

        # 非同期処理を復活：QThreadを使用
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
        self.btnStop.clicked.connect(self.stop_processing)
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

        # フレーム更新の制御
        self.last_pixmap_update_time = 0  # 最後のピクスマップ更新時刻
        self.pixmap_update_interval = 0.1  # ピクスマップ更新間隔（秒）

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
        # このメソッドは使用しない（QTimerで制御）
        pass

    def update_frame_display(self):
        """QTimerで定期的にフレーム表示を更新"""
        # 最新のフレーム位置から画像を生成
        diff = self.worker.pass1.diff_image
        if diff is not None:
            qimage = cv2toQImage(diff)
            if not qimage.isNull():
                pixmap = QPixmap.fromImage(qimage)
                if not pixmap.isNull():
                    self.image_pane.setPixmap(pixmap)
        # except Exception as e:
        #     print(f"フレーム表示更新でエラーが発生しました: {e}")

    def stop_processing(self):
        """停止ボタンが押された時の処理"""
        # ボタンのテキストを変更して停止中であることを示す
        self.btnStop.setText("停止中...")
        self.btnStop.setEnabled(False)

        # ワーカーに停止を指示
        self.worker.stop()

        # すぐに終了
        self.terminateIt()

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
            # 古い接続を切断（安全に）
            try:
                self.btnStop.clicked.disconnect()
            except TypeError:
                pass  # 接続がない場合は無視
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

        # タイムアウト付きで待機（3秒）
        if not self.thread.wait(3000):  # 3000ms = 3秒
            self.logger.warning("スレッドが正常に終了しませんでした。強制終了します。")
            self.thread.terminate()
            # 強制終了後、少し待機して確実に終了させる
            self.thread.wait(1000)  # 1秒待機


def main():
    app = QApplication(sys.argv)
    match = MatcherUI(sys.argv, True)
    match.setWindowTitle("Matcher Preview")
    match.show()
    match.raise_()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
