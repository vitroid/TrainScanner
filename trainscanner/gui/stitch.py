#!/usr/bin/env python3

import math
import sys
from logging import DEBUG, WARN, basicConfig, getLogger, INFO

import cv2
import numpy as np
from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPainter, QPixmap, QPen, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
)

# from QTiledImage import QTiledImage
# from tiledimage import cachedimage as ci

from trainscanner import stitch
from trainscanner.widget.scaledcanvas import ScaledCanvas
from trainscanner.i18n import init_translations, tr
from trainscanner.rasterio_canvas import get_image, crop_image


# It is run in the thread.
class Renderer(QObject):
    # frameRendered = pyqtSignal(QImage)  # it is target of emit()
    tileRendered = pyqtSignal(tuple, np.ndarray)
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self, parent=None, stitcher=None):
        super(Renderer, self).__init__(parent)
        self.stitcher = stitcher
        self._isRunning = True
        # Dirty signal handler
        self.stitcher.canvas.set_hook(self.signal_sender)

    def signal_sender(self, pos, image):
        self.tileRendered.emit(pos, image)

    def task(self):
        if not self._isRunning:
            self._isRunning = True

        for num, den in self.stitcher.before():
            self.progress.emit(num * 100 // den)
        for num, den in self.stitcher.loop():
            if not self._isRunning:
                # interrupted
                # self.stitcher.after()
                self.finished.emit()
                return
            self.progress.emit(num * 100 // den)
        # completed
        self.progress.emit(100)
        # self.stitcher.after()
        self.finished.emit()
        self.stitcher.canvas.close()

    def stop(self):
        self._isRunning = False
        # self.stitcher.canvas.add_hook(None)


class ExtensibleCanvasWidget(QLabel):
    def __init__(self, parent=None, preview_ratio=1.0, update_interval=0.2):
        super(ExtensibleCanvasWidget, self).__init__(parent)
        self.scaled_canvas = ScaledCanvas(scale=preview_ratio)
        self.last_update_time = 0  # 最後の更新時刻を記録
        self.update_interval = update_interval

    def updatePixmap(self, pos, image):
        self.scaled_canvas.put_image(pos, image)

        # 0.2秒に一回だけ画面更新を実行
        import time

        current_time = time.time()
        if current_time - self.last_update_time >= self.update_interval:
            fullimage = cv2.cvtColor(
                self.scaled_canvas.get_image(), cv2.COLOR_BGR2RGB
            )  # reverse order
            h, w = fullimage.shape[:2]
            self.resize(w, h)
            qimage = QImage(fullimage.data, w, h, w * 3, QImage.Format.Format_RGB888)
            self.setPixmap(QPixmap.fromImage(qimage))
            self.update()
            self.last_update_time = current_time


class ExtensibleCroppingCanvasWidget(ExtensibleCanvasWidget):
    def __init__(self, parent=None, preview_ratio=1.0):
        super(ExtensibleCroppingCanvasWidget, self).__init__(parent, preview_ratio)
        self.left_cut = 0
        self.right_cut = 0
        self.dragging = False
        self.drag_edge = None
        self.setMouseTracking(True)
        self.drag_threshold = 20  # ドラッグ可能な領域の幅
        self.draw_complete = False

    def setDrawComplete(self, final_image=None):
        self.draw_complete = True
        if final_image is not None:
            h, w = final_image.shape[:2]
            self.resize(w, h)
            # BGRからRGBに変換し、メモリを連続したバイト列に変換
            rgb_image = cv2.cvtColor(final_image, cv2.COLOR_BGR2RGB)
            bytes_per_line = 3 * w
            qimage = QImage(
                rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
            )
            self.setPixmap(QPixmap.fromImage(qimage))

        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.draw_complete and self.pixmap():
            painter = QPainter(self)
            # 長方形を描画
            # painter.setPen(QPen(Qt.GlobalColor.red, 2))
            # painter.drawRect(
            #     int(self.left_cut),
            #     0,
            #     int(self.width() - self.left_cut - self.right_cut),
            #     self.height(),
            # )
            # 垂直線を太く描画
            painter.setPen(QPen(Qt.GlobalColor.red, 4))
            painter.drawLine(int(self.left_cut), 0, int(self.left_cut), self.height())
            painter.drawLine(
                int(self.width() - self.right_cut - 1),
                0,
                int(self.width() - self.right_cut - 1),
                self.height(),
            )
            painter.end()

    def mousePressEvent(self, event):
        if not self.draw_complete:
            return
        x = int(event.position().x())
        # 左端の近くをクリックした場合
        if abs(x - self.left_cut) < self.drag_threshold:
            self.dragging = True
            self.drag_edge = "left"
        # 右端の近くをクリックした場合
        elif abs(x - (self.width() - self.right_cut - 1)) < self.drag_threshold:
            self.dragging = True
            self.drag_edge = "right"

    def mouseMoveEvent(self, event):
        if not self.draw_complete:
            return
        x = int(event.position().x())
        if self.dragging:
            if self.drag_edge == "left":
                self.left_cut = max(
                    0, min(x, self.width() - self.right_cut - 1 - self.drag_threshold)
                )
            else:  # right
                self.right_cut = self.width() - min(
                    self.width(), max(x, self.left_cut + self.drag_threshold)
                )
            self.update()
        else:
            # カーソル形状の変更
            if (
                abs(x - self.left_cut) < self.drag_threshold
                or abs(x - (self.width() - self.right_cut - 1)) < self.drag_threshold
            ):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.drag_edge = None


class StitcherUI(QDialog):
    thread_invoker = pyqtSignal()

    def __init__(self, argv, terminate, parent=None):
        logger = getLogger()
        super(StitcherUI, self).__init__(parent)

        init_translations()

        self.setWindowTitle(tr("Stitcher Preview"))
        stitcher = stitch.Stitcher(argv=argv)
        # tilesize = (128, 512)  # can be smaller for smaller working memory
        # cachesize = 10
        # stitcher.set_canvas(
        #     ci.CachedImage(
        #         "new", dir=stitcher.cachedir, tilesize=tilesize, cachesize=cachesize
        #     )
        # )
        self.stitcher = stitcher
        # stitcherの幅
        width = stitcher.dimen[0]
        # このwidthは原寸の幅。
        # stitchが幅を-Wで指定している場合はそちらの幅を使う
        if 0 < stitcher.params.length < stitcher.dimen[0]:
            width = stitcher.params.length

        # determine the shrink ratio to avoid too huge preview
        self.preview_ratio = 1.0
        self.preview_width = width
        if width > 10000:
            self.preview_ratio = 10000.0 / width
            self.preview_width = 10000
        self.terminate = terminate
        self.thread = QThread()
        self.thread.start()

        self.worker = Renderer(stitcher=stitcher)
        # it might be too early.

        self.scrollArea = QScrollArea()
        # self.scrollArea.setMaximumHeight(1000)
        self.largecanvas = ExtensibleCroppingCanvasWidget(
            preview_ratio=self.preview_ratio
        )
        # print(width,height)
        # self.worker.frameRendered.connect(self.largecanvas.updatePixmap)
        self.worker.tileRendered.connect(self.largecanvas.updatePixmap)
        self.worker.finished.connect(self.stitch_finished)
        self.worker.moveToThread(self.thread)
        self.thread_invoker.connect(self.worker.task)
        self.thread_invoker.emit()

        self.scrollArea.setWidget(self.largecanvas)
        self.scrollArea.setMinimumHeight(500)  # self.largecanvas.sizeHint().height())
        self.scrollArea.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.btnStop = QPushButton("Stop")
        self.btnStop.clicked.connect(lambda: self.worker.stop())
        self.btnStop.clicked.connect(self.stopbutton_pressed)

        self.progress = QProgressBar(self)
        self.worker.progress.connect(self.progress.setValue)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.btnStop)
        self.layout.addWidget(self.progress)
        self.layout.addWidget(self.scrollArea)
        self.layout.addStretch(1)
        self.setLayout(self.layout)

        # ショートカットの設定
        close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        close_shortcut.activated.connect(self.close)

    def crop_finished(self):
        logger = getLogger()
        # logger.info("crop_finished")
        # save the final image
        left_cut = int(self.largecanvas.left_cut / self.preview_ratio)
        right_cut = int(self.largecanvas.right_cut / self.preview_ratio)
        file_name = self.stitcher.outfilename
        cropped_file_name = file_name.replace(".tiff", "_cropped.tiff")
        crop_image(file_name, left_cut, right_cut, cropped_file_name)

        self.stopbutton_pressed()

    def stopbutton_pressed(self):
        self.close()
        if self.terminate:
            sys.exit(1)  # terminated

    def stitch_finished(self):
        # ボタンの機能を変える。
        self.btnStop.setText(tr("Crop + Finish"))
        # 古い接続を切断してから新しい接続を設定
        self.btnStop.clicked.disconnect()
        self.btnStop.clicked.connect(self.crop_finished)

        # ここで、tiledimageを読みこみ、スケールし、canvasをさしかえる。
        # ただ、cropping枠を変形した時にどこでそれを保存するのか。
        scaled_image = get_image(
            self.stitcher.outfilename, dst_width=self.preview_width
        )
        self.largecanvas.setDrawComplete(scaled_image)

        self.stop_thread()

    def closeEvent(self, event):
        self.stop_thread()

    def stop_thread(self):
        logger = getLogger()
        self.worker.stop()
        self.thread.quit()
        self.thread.wait()
        logger.info("Stitch_gui thread stopped.")


def main():
    debug = False
    if debug:
        basicConfig(
            level=DEBUG,
            # filename='log.txt',
            format="%(asctime)s %(levelname)s %(message)s",
        )
    else:
        basicConfig(level=INFO, format="%(asctime)s %(levelname)s %(message)s")

    import sys

    app = QApplication(sys.argv)
    win = StitcherUI(sys.argv, True)
    win.setMaximumHeight(500)
    win.showMaximized()
    # win.show()
    win.raise_()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
