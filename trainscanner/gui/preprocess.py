from dataclasses import dataclass
import time
from logging import DEBUG, WARN, basicConfig, getLogger, root

import cv2
import numpy as np

from PyQt6.QtCore import pyqtSignal, Qt, QObject, QPoint, QRect, QThread, QSize
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QPushButton,
    QLabel,
    QSizePolicy,
    QSlider,
    QRubberBand,
    QMessageBox,
)
from PyQt6.QtGui import QImage, QPixmap, QPainter, QKeySequence, QShortcut

from trainscanner import trainscanner, video
from trainscanner.widget.imageselector2 import ImageSelector2
import trainscanner.widget.qrangeslider as rs
from trainscanner.i18n import tr, init_translations
from trainscanner.widget import cv2toQImage

perspectiveCSS = """
QRangeSlider > QSplitter::handle {
    background: #55f;
}
QRangeSlider > QSplitter::handle:pressed {
    background: #ccf;
}
QRangeSlider #Span {
    background: #229;
}
"""

cropCSS = """
QRangeSlider > QSplitter::handle {
    background: #f55;
}
QRangeSlider > QSplitter::handle:pressed {
    background: #fcc;
}
QRangeSlider #Span {
    background: #922;
}
"""


@dataclass
class FrameInfo:
    every_n_frames: int
    frames: list[np.ndarray]


class AsyncImageLoader(QObject):
    """
    This works in the background as a separate thread
    to load the thumbnails for the time line
    """

    frameIncreased = pyqtSignal(FrameInfo)
    errorOccurred = pyqtSignal(str)  # エラーメッセージを送信するシグナルを追加

    def __init__(self, parent=None, filename="", size=0):
        super(AsyncImageLoader, self).__init__(parent)
        self.isRunning = True
        self.filename = filename  # ファイル名を保持
        self.size = size
        logger = getLogger()
        logger.debug("Open video: {0}".format(filename))

        try:
            self.vl = video.video_loader_factory(filename)
            nframe, frame = self.vl.next()
            if self.size:
                frame = trainscanner.fit_to_square(frame, self.size)
            self.snapshots = [frame]
            self.every_n_frames = 1
            self.max_frames = 128
        except Exception as e:
            logger.error(f"Error opening video file: {str(e)}")
            self.errorOccurred.emit(f"ビデオファイルを開けません: {filename}\n{str(e)}")
            self.isRunning = False
            self.snapshots = []

    def stop(self):
        self.isRunning = False
        # trash images
        self.snapshots = []

    def task(self):
        logger = getLogger()
        if not self.isRunning:
            return

        if not self.snapshots:  # 初期化時にエラーが発生していた場合
            return

        last_emit_time = time.time()
        while True:
            try:
                nframe, frame = self.vl.next()
                if nframe == 0:
                    logger.debug("End of video reached")
                    break
                if self.size:
                    frame = trainscanner.fit_to_square(frame, self.size)
                self.snapshots.append(frame)
                if len(self.snapshots) == self.max_frames:
                    logger.debug("max frames reached")
                    self.every_n_frames *= 2
                    self.snapshots = self.snapshots[::2]
                logger.debug(f"frames: {len(self.snapshots)}")
                now = time.time()
                if now - last_emit_time > 0.1:
                    self.frameIncreased.emit(
                        FrameInfo(
                            every_n_frames=self.every_n_frames,
                            frames=self.snapshots,
                        )
                    )
                    last_emit_time = now

                # Skip frames
                for i in range(self.every_n_frames - 1):
                    nframe = self.vl.skip()
                    if nframe == 0:
                        logger.debug("End of video reached during skip")
                        break
                # このやりかただと、一番最後のフレームを落してしまう。

            except Exception as e:
                logger.error(f"Error during video loading: {str(e)}")
                self.errorOccurred.emit(
                    f"ビデオの読み込み中にエラーが発生しました: {str(e)}"
                )
                break

        # 0.1秒待ってから再度emitする。
        time.sleep(0.1)
        if self.snapshots:  # エラーが発生していない場合のみemit
            self.frameIncreased.emit(
                FrameInfo(
                    every_n_frames=self.every_n_frames,
                    frames=self.snapshots,
                )
            )
        self.isRunning = False
        return


class DeformationFixWidget(QLabel):
    def __init__(self, parent=None):
        super(QLabel, self).__init__(parent)
        self.perspective = (0, 0, 1000, 1000)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # 画像のスケーリングモードを設定
        self.setScaledContents(False)

    def sizeHint(self):
        # 親ウィジェットのサイズを取得
        parent = self.parent()
        if parent:
            return parent.size()
        return super().sizeHint()

    def minimumSizeHint(self):
        return QSize(100, 100)

    def paintEvent(self, event):
        QLabel.paintEvent(self, event)
        painter = QPainter(self)

        w = self.width()
        h = self.height()

        # widget内部の画像のサイズを取得
        pixmap = self.pixmap()
        if pixmap is None:
            return
        img_w = pixmap.width()
        img_h = pixmap.height()

        image_left = (w - img_w) // 2
        image_right = image_left + img_w
        image_top = (h - img_h) // 2

        # 既存の描画処理
        painter.setPen(Qt.GlobalColor.blue)
        painter.drawLine(
            image_left,
            image_top + self.perspective[0] * img_h // 1000,
            image_right,
            image_top + self.perspective[1] * img_h // 1000,
        )
        painter.drawLine(
            image_left,
            image_top + self.perspective[2] * img_h // 1000,
            image_right,
            image_top + self.perspective[3] * img_h // 1000,
        )


def draw_slitpos(f, slitpos):
    h, w = f.shape[0:2]
    slitpos1 = (slitpos + 500) * w // 1000
    slitpos2 = (500 - slitpos) * w // 1000
    cv2.line(f, (slitpos1, 0), (slitpos1, h), (0, 0, 255), 1)
    cv2.line(f, (slitpos2, 0), (slitpos2, h), (0, 0, 255), 1)


class ClippingWidget(QLabel):
    def __init__(self, parent=None, hook=None, focus=None):
        self.hook = hook
        QLabel.__init__(self, parent)
        self.rubberBand = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self.origin = QPoint()
        self.slitpos = 250
        self.focus = focus.copy()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # 画像のスケーリングモードを設定
        self.setScaledContents(False)

    def sizeHint(self):
        # 親ウィジェットのサイズを取得
        parent = self.parent()
        if parent:
            return parent.size()
        return super().sizeHint()

    def minimumSizeHint(self):
        return QSize(100, 100)

    def widget_to_fractional_coords(self, point):
        # ウィジェットの中の画像のサイズを取得
        pixmap = self.pixmap()
        if pixmap is None:
            return 0, 0
        img_w = pixmap.width()
        img_h = pixmap.height()

        # 画像の表示位置を計算（ウィジェットの中央）
        x = (self.width() - img_w) // 2
        y = (self.height() - img_h) // 2

        # マウス座標が画像の範囲内かチェック
        if (
            point.x() < x
            or point.x() > x + img_w
            or point.y() < y
            or point.y() > y + img_h
        ):
            return 0, 0

        # ウィジェット座標から画像座標への変換
        img_x = (point.x() - x) * 1000 // img_w
        img_y = (point.y() - y) * 1000 // img_h
        return img_x, img_y

    def paintEvent(self, event):
        QLabel.paintEvent(self, event)
        painter = QPainter(self)
        painter.setPen(Qt.GlobalColor.red)

        # 実際のウィジェットのサイズを取得
        w = self.width()
        h = self.height()
        # 画像のサイズを取得
        pixmap = self.pixmap()
        if pixmap is None:
            return
        img_w = pixmap.width()
        img_h = pixmap.height()

        # 画像の表示位置を計算
        x = (w - img_w) // 2
        y = (h - img_h) // 2

        d = 20
        painter.drawLine(
            x + img_w // 2 - self.slitpos * img_w // 1000,
            y,
            x + img_w // 2 - self.slitpos * img_w // 1000,
            y + img_h,
        )
        painter.drawLine(
            x + img_w // 2 - self.slitpos * img_w // 1000 - d,
            y + img_h // 2,
            x + img_w // 2 - self.slitpos * img_w // 1000,
            y + img_h // 2 - d,
        )
        painter.drawLine(
            x + img_w // 2 - self.slitpos * img_w // 1000 - d,
            y + img_h // 2,
            x + img_w // 2 - self.slitpos * img_w // 1000,
            y + img_h // 2 + d,
        )
        painter.drawLine(
            x + img_w // 2 + self.slitpos * img_w // 1000,
            y,
            x + img_w // 2 + self.slitpos * img_w // 1000,
            y + img_h,
        )
        painter.drawLine(
            x + img_w // 2 + self.slitpos * img_w // 1000 + d,
            y + img_h // 2,
            x + img_w // 2 + self.slitpos * img_w // 1000,
            y + img_h // 2 - d,
        )
        painter.drawLine(
            x + img_w // 2 + self.slitpos * img_w // 1000 + d,
            y + img_h // 2,
            x + img_w // 2 + self.slitpos * img_w // 1000,
            y + img_h // 2 + d,
        )
        painter.setPen(Qt.GlobalColor.green)
        painter.drawRect(
            x + img_w * self.focus[0] // 1000,
            y + img_h * self.focus[2] // 1000,
            img_w * (self.focus[1] - self.focus[0]) // 1000,
            img_h * (self.focus[3] - self.focus[2]) // 1000,
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.origin = QPoint(event.pos())
            self.rubberBand.setGeometry(QRect(self.origin, QSize()))
            self.rubberBand.show()

    def mouseMoveEvent(self, event):
        if not self.origin.isNull():
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.rubberBand.hide()
            region = QRect(self.origin, event.pos()).normalized()

            # ウィジェット座標を分数座標に変換
            x1, y1 = self.widget_to_fractional_coords(region.topLeft())
            x2, y2 = self.widget_to_fractional_coords(region.bottomRight())

            # 座標を0-1000の範囲に制限
            x1 = max(0, min(1000, x1))
            x2 = max(0, min(1000, x2))
            y1 = max(0, min(1000, y1))
            y2 = max(0, min(1000, y2))

            # focusを更新（分数座標系）
            self.focus = (x1, x2, y1, y2)

            if self.hook is not None:
                self.hook(self.focus)


# https://www.tutorialspoint.com/pyqt/pyqt_qfiledialog_widget.htm
class EditorGUI(QWidget):
    thread_invoker = pyqtSignal()

    def __init__(self, settings, parent=None, filename=None, params=None):
        super(EditorGUI, self).__init__(parent)

        init_translations()

        # ショートカットの設定
        close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        close_shortcut.activated.connect(self.close)

        # options
        # self.skip       = 0
        logger = getLogger()
        self.perspective = [0, 0, 1000, 1000]
        self.angle_degree = 0
        self.focus = [333, 666, 333, 666]
        self.croptop = 0
        self.cropbottom = 1000
        self.slitpos = 250
        if params is not None:
            logger.debug("EditorGUI params {0}".format(params))
            self.angle_degree = params["rotate"]
            if params["perspective"] is not None:
                self.perspective = params["perspective"]
            self.focus = params["focus"]
            self.slitpos = params["slitpos"]
            self.croptop, self.cropbottom = params["crop"]
            # self.skip         = params["skip"] #no use
            filename = params["filename"]
        # private
        self.preview_size = 500
        self.frame = 0
        self.settings = settings
        # make the threaded loader
        self.thread = QThread()
        self.thread.start()
        self.lastupdatethumbs = 0  # from epoch

        self.asyncimageloader = AsyncImageLoader(
            filename=filename, size=self.preview_size
        )
        self.asyncimageloader.moveToThread(self.thread)
        self.thread_invoker.connect(self.asyncimageloader.task)
        self.thread_invoker.emit()
        self.asyncimageloader.frameIncreased.connect(self.updateTimeLine)
        self.asyncimageloader.errorOccurred.connect(
            self.handleError
        )  # エラーハンドラを接続

        # close on quit
        # http://stackoverflow.com/questions/27420338/how-to-clear-child-window-reference-stored-in-parent-application-when-child-wind
        # self.setAttribute(Qt.WA_DeleteOnClose)
        bottom_pane = self.bottom_pane_layout()
        self.imageselector2 = ImageSelector2()
        self.imageselector2.slider.startValueChanged.connect(self.frameChanged)
        self.imageselector2.slider.endValueChanged.connect(self.frameChanged)
        imageselector_layout = QHBoxLayout()
        imageselector_layout.addWidget(self.imageselector2)
        imageselector_gbox = QGroupBox(tr("1. Specify the frame range"))
        imageselector_gbox.setLayout(imageselector_layout)

        # finish_layout_gbox = QGroupBox(tr("4. Finish"))
        # finish_layout = QVBoxLayout()
        # https://www.tutorialspoint.com/pyqt/pyqt_qcheckbox_widget.htm
        self.start_button = QPushButton(tr("Stich"), self)
        self.start_button.clicked.connect(self.settings.start_process)
        # finish_layout.addWidget(self.start_button)

        # finish_layout_gbox.setLayout(finish_layout)

        # The outmost box
        glayout = QVBoxLayout()
        glayout.addWidget(imageselector_gbox)
        glayout.addLayout(bottom_pane)
        # glayout.addWidget(finish_layout_gbox)
        glayout.addWidget(self.start_button)
        self.setLayout(glayout)
        self.setWindowTitle("Editor")

        # Set minimum size instead of fixed size
        self.setMinimumSize(800, 600)

        self.show_snapshots()

    def thumbtransformer(self, cv2image):
        rotated, warped, cropped = self.transform.process_image(cv2image)
        h, w = cropped.shape[0:2]
        thumbh = 100
        thumbw = w * thumbh // h
        thumb = cv2.resize(cropped, (thumbw, thumbh), interpolation=cv2.INTER_CUBIC)
        return cv2toQImage(thumb)

    def updateTimeLine(self, frameinfo: FrameInfo = None):
        # count time and limit update
        now = time.time()
        # if now - self.lastupdatethumbs < 0.1:  # 更新頻度を0.05秒に変更
        #     return
        # transformation filter
        self.imageselector2.imagebar.setTransformer(self.thumbtransformer)
        self.imageselector2.setThumbs(frameinfo.frames)
        if frameinfo.every_n_frames:
            self.every_n_frames = frameinfo.every_n_frames
        self.lastupdatethumbs = time.time()

    def deformation_rangeslider_widget(self, top_on_draw, bottom_on_draw):
        rangeslider = rs.QRangeSlider(splitterWidth=10, vertical=True)  # スライダの向き
        rangeslider.setFixedWidth(15)
        rangeslider.setStyleSheet(perspectiveCSS)
        rangeslider.setDrawValues(False)
        rangeslider.startValueChanged.connect(top_on_draw)
        rangeslider.endValueChanged.connect(bottom_on_draw)
        # self.sliderL.setMinimumHeight(500)
        return rangeslider

    def rotation_deformation_control(self):
        layout = QHBoxLayout()
        self.btn = QPushButton(tr("-90"))
        self.btn.clicked.connect(self.angle_sub90)
        layout.addWidget(self.btn)
        self.btn = QPushButton(tr("-1"))
        self.btn.clicked.connect(self.angle_dec)
        layout.addWidget(self.btn)
        layout.addWidget(QLabel(tr("rotation")))
        self.angle_label = QLabel("0 " + tr("degrees"))
        layout.addWidget(self.angle_label)
        self.btn = QPushButton(tr("+1"))
        self.btn.clicked.connect(self.angle_inc)
        layout.addWidget(self.btn)
        self.btn = QPushButton(tr("+90"))
        self.btn.clicked.connect(self.angle_add90)
        layout.addWidget(self.btn)
        return layout

    def crop_rangeslider_widget(self):
        # crop_layout = QVBoxLayout()
        slider = rs.QRangeSlider(splitterWidth=10, vertical=True)  # スライダの向き
        slider.setFixedWidth(15)
        slider.setStyleSheet(cropCSS)
        slider.setDrawValues(False)
        slider.startValueChanged.connect(self.croptop_slider_on_draw)
        slider.endValueChanged.connect(self.cropbottom_slider_on_draw)
        # self.crop_slider.setMinimumHeight(500)
        return slider

        # crop_layout.addWidget(self.crop_slider)
        # return crop_layout

    def deformation_image_layout(self):
        self.left_image_pane = DeformationFixWidget()
        self.left_image_pane.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # サイズポリシーはDeformationFixWidgetのコンストラクタで設定するため、ここでは削除
        self.left_image_pane.setMinimumSize(100, 100)  # 最小サイズを設定

        layout = QVBoxLayout()
        layout.addWidget(self.left_image_pane, 1)  # ストレッチファクター1
        # 中央揃えは維持
        layout.setAlignment(self.left_image_pane, Qt.AlignmentFlag.AlignHCenter)
        layout.setAlignment(self.left_image_pane, Qt.AlignmentFlag.AlignTop)
        return layout

    def set_focus(self, focus: tuple[int, int, int, int]):
        self.focus = focus
        # これを呼ばないと、古い■が残ったままになる
        self.show_snapshots()

    def crop_image_layout(self):
        layout = QVBoxLayout()
        self.right_image_pane = ClippingWidget(hook=self.set_focus, focus=self.focus)
        self.right_image_pane.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.right_image_pane.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding
        )
        self.right_image_pane.setMinimumSize(100, 100)  # 最小サイズを設定
        layout.addWidget(self.right_image_pane, 1)
        layout.setAlignment(self.right_image_pane, Qt.AlignmentFlag.AlignHCenter)
        layout.setAlignment(self.right_image_pane, Qt.AlignmentFlag.AlignTop)
        return layout

    def slit_slider_widget(self):
        slider = QSlider(Qt.Orientation.Horizontal)  # スライダの向き
        slider.setRange(-500, 500)  # スライダの範囲
        # スライダの目盛りを両方に出す
        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        slider.valueChanged.connect(self.slit_slider_on_draw)
        return slider

    def left_pane_layout(self):

        self.sliderL = self.deformation_rangeslider_widget(
            self.sliderTL_on_draw, self.sliderBL_on_draw
        )
        self.sliderR = self.deformation_rangeslider_widget(
            self.sliderTR_on_draw, self.sliderBR_on_draw
        )

        # left_paneのレイアウト
        left_pane_layout = QVBoxLayout()
        left_pane_title = QGroupBox(tr("2. Repair deformation"))
        left_pane_layout.addWidget(left_pane_title)

        # left medium layout
        left_medium_layout = QVBoxLayout()
        left_medium_layout.addLayout(self.deformation_image_layout(), 1)
        rotation_deformation_layout = self.rotation_deformation_control()
        left_medium_layout.addLayout(rotation_deformation_layout)

        # 左上段
        first_box = QHBoxLayout()
        first_box.addWidget(self.sliderL)
        # first_box.addLayout(self.deformation_image_layout(), 1)
        first_box.addLayout(left_medium_layout)
        first_box.addWidget(self.sliderR)

        # 左下段
        # rotation_deformation_layout = self.rotation_deformation_control()

        # combined_box = QVBoxLayout()
        # combined_box.addLayout(first_box)
        # combined_box.addLayout(rotation_deformation_layout)
        # combined_box.setAlignment(
        #     rotation_deformation_layout, Qt.AlignmentFlag.AlignTop
        # )

        # left_pane_title.setLayout(combined_box)
        left_pane_title.setLayout(first_box)
        return left_pane_layout

    def right_pane_layout(self):

        self.crop_slider = self.crop_rangeslider_widget()
        self.slit_slider = self.slit_slider_widget()

        right_pane_layout = QVBoxLayout()
        # 右側のパネルのタイトル
        right_pane_title = QGroupBox(tr("3. Motion Detection and Slit"))
        right_pane_layout.addWidget(right_pane_title)

        # crop_image_layoutとcrop_sliderを横に並べ
        first_box = QHBoxLayout()
        crop_image_layout = self.crop_image_layout()
        first_box.addLayout(crop_image_layout, 1)
        first_box.addWidget(self.crop_slider)

        # slit_sliderのラベルと本体を横に並べ、
        second_box = QHBoxLayout()
        slit_slider_label = QLabel(tr("Slit position"))
        second_box.addWidget(slit_slider_label)
        second_box.addWidget(self.slit_slider)

        # これら2つを縦に積み
        right_combined_box = QVBoxLayout()
        right_combined_box.addLayout(first_box)
        right_combined_box.addLayout(second_box)
        right_combined_box.setAlignment(second_box, Qt.AlignmentFlag.AlignTop)

        right_pane_title.setLayout(right_combined_box)
        return right_pane_layout

    def bottom_pane_layout(self):
        layout = QHBoxLayout()
        left = self.left_pane_layout()
        right = self.right_pane_layout()
        layout.addLayout(left)
        layout.addLayout(right)
        layout.setStretch(0, 1)  # 左ペイン
        layout.setStretch(1, 1)  # 右ペイン
        return layout

    def stop_thread(self):
        self.asyncimageloader.stop()
        self.thread.quit()
        self.thread.wait()

    def angle_inc(self):
        self.angle_degree += 1
        self.angle_degree %= 360
        self.angle_label.setText(f'{self.angle_degree} {tr("degrees")}')
        self.updateTimeLine(
            FrameInfo(
                every_n_frames=0,
                frames=self.asyncimageloader.snapshots,
            )
        )
        self.show_snapshots()

    def angle_dec(self):
        self.angle_degree -= 1
        self.angle_degree %= 360
        self.angle_label.setText(f'{self.angle_degree} {tr("degrees")}')
        self.updateTimeLine(
            FrameInfo(
                every_n_frames=0,
                frames=self.asyncimageloader.snapshots,
            )
        )
        self.show_snapshots()

    def angle_add90(self):
        self.angle_degree += 90
        self.angle_degree %= 360
        self.angle_label.setText(f'{self.angle_degree} {tr("degrees")}')
        self.updateTimeLine(
            FrameInfo(
                every_n_frames=0,
                frames=self.asyncimageloader.snapshots,
            )
        )
        self.show_snapshots()

    def angle_sub90(self):
        self.angle_degree -= 90
        self.angle_degree %= 360
        self.angle_label.setText(f'{self.angle_degree} {tr("degrees")}')
        self.updateTimeLine(
            FrameInfo(
                every_n_frames=0,
                frames=self.asyncimageloader.snapshots,
            )
        )
        self.show_snapshots()

    def frameChanged(self, value):
        self.frame = value
        self.show_snapshots()

    def sliderTL_on_draw(self):
        self.perspective[0] = self.sliderL.start()
        self.updateTimeLine(
            FrameInfo(
                every_n_frames=0,
                frames=self.asyncimageloader.snapshots,
            )
        )
        self.show_snapshots()

    def sliderBL_on_draw(self):
        self.perspective[2] = self.sliderL.end()
        self.updateTimeLine(
            FrameInfo(
                every_n_frames=0,
                frames=self.asyncimageloader.snapshots,
            )
        )
        self.show_snapshots()

    def sliderTR_on_draw(self):
        self.perspective[1] = self.sliderR.start()
        self.updateTimeLine(
            FrameInfo(
                every_n_frames=0,
                frames=self.asyncimageloader.snapshots,
            )
        )
        self.show_snapshots()

    def sliderBR_on_draw(self):
        self.perspective[3] = self.sliderR.end()
        self.updateTimeLine(
            FrameInfo(
                every_n_frames=0,
                frames=self.asyncimageloader.snapshots,
            )
        )
        self.show_snapshots()

    def show_snapshots(self):
        """
        put the snapshots in the preview panes
        """
        if self.frame < 0:
            return
        logger = getLogger()
        if self.frame < 0:
            self.frame = 0
        elif self.frame >= len(self.asyncimageloader.snapshots):
            self.frame = len(self.asyncimageloader.snapshots) - 1
        image = self.asyncimageloader.snapshots[self.frame]
        self.transform = trainscanner.transformation(
            self.angle_degree, self.perspective, [self.croptop, self.cropbottom]
        )
        rotated, warped, cropped = self.transform.process_first_image(image)
        self.put_cv2_image(rotated, self.left_image_pane)
        self.put_cv2_image(cropped, self.right_image_pane)

    def put_cv2_image(self, image, widget):
        height, width = image.shape[0:2]
        qImg = cv2toQImage(image)
        pixmap = QPixmap(qImg)

        # Get the current widget size
        widget_width = widget.width()
        widget_height = widget.height()

        # アスペクト比を維持しながらスケーリング(拡大も可能)
        pixmap = pixmap.scaled(
            widget_width,
            widget_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        widget.setPixmap(pixmap)
        widget.perspective = self.perspective
        widget.slitpos = self.slitpos

    def slit_slider_on_draw(self):
        self.slitpos = self.slit_slider.value()
        self.show_snapshots()

    def croptop_slider_on_draw(self):
        self.croptop = self.crop_slider.start()
        self.updateTimeLine(
            FrameInfo(
                every_n_frames=0,
                frames=self.asyncimageloader.snapshots,
            )
        )
        self.show_snapshots()

    def cropbottom_slider_on_draw(self):
        self.cropbottom = self.crop_slider.end()
        self.updateTimeLine(
            FrameInfo(
                every_n_frames=0,
                frames=self.asyncimageloader.snapshots,
            )
        )
        self.show_snapshots()

    def closeEvent(self, event):
        self.settings.reset_input()
        self.stop_thread()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.show_snapshots()

    def handleError(self, error_message):
        """エラーメッセージを表示し、ウィンドウを閉じる"""
        QMessageBox.critical(self, "エラー", error_message)
        self.close()


# for pyinstaller
def resource_path(relative):
    return os.path.join(os.environ.get("_MEIPASS", os.path.abspath(".")), relative)


def main():
    # pyqt_set_trace()
    basicConfig(level=WARN, format="%(asctime)s %(levelname)s %(message)s")
    app = QApplication(sys.argv)
    path = os.path.dirname(trainscanner.__file__)

    se = SettingsGUI()
    se.show()
    se.raise_()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
