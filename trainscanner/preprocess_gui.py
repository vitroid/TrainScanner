from logging import getLogger
import time

import cv2
from PyQt6.QtCore import pyqtSignal, Qt, QObject, QPoint, QRect, QThread
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
)
from PyQt6.QtGui import QImage, QPixmap, QPainter

from trainscanner import trainscanner, video
from trainscanner.imageselector2 import ImageSelector2
import trainscanner.qrangeslider as rs

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


class AsyncImageLoader(QObject):
    """
    This works in the background as a separate thread
    to load the thumbnails for the time line
    """

    frameIncreased = pyqtSignal(list)

    def __init__(self, parent=None, filename="", size=0):
        super(AsyncImageLoader, self).__init__(parent)
        self.isRunning = True

        # capture the first frame ASAP to avoid "no frame" errors.
        self.size = size
        logger = getLogger()
        logger.debug(f"Open video: {filename}")
        self.vl = video.VideoLoader(filename)
        nframe, frame = self.vl.next()
        if self.size:
            frame = trainscanner.fit_to_square(frame, self.size)
        self.snapshots = [frame]

    def stop(self):
        self.isRunning = False
        # trash images
        self.snapshots = []

    def task(self):
        if not self.isRunning:
            self.isRunning = True

        while self.isRunning:
            nframe, frame = self.vl.next()
            if nframe == 0:
                return
            if self.size:
                frame = trainscanner.fit_to_square(frame, self.size)
            self.snapshots.append(frame)
            self.frameIncreased.emit(self.snapshots)
            for i in range(9):
                nframe = self.vl.skip()
                if nframe == 0:
                    return


class DrawableLabel(QLabel):
    def __init__(self, parent=None):
        super(QLabel, self).__init__(parent)
        self.perspective = (0, 0, 1000, 1000)
        self.geometry = (0, 0, 1000, 1000)

    def paintEvent(self, event):
        QLabel.paintEvent(self, event)
        painter = QPainter(self)
        painter.setPen(Qt.GlobalColor.blue)
        # painter.setBrush(Qt.yellow)
        # painter.drawRect(10, 10, 100, 100)
        x, y, w, h = self.geometry
        painter.drawLine(
            x,
            y + self.perspective[0] * h // 1000,
            x + w,
            y + self.perspective[1] * h // 1000,
        )
        painter.drawLine(
            x,
            y + self.perspective[2] * h // 1000,
            x + w,
            y + self.perspective[3] * h // 1000,
        )


def draw_slitpos(f, slitpos):
    h, w = f.shape[0:2]
    slitpos1 = (slitpos + 500) * w // 1000
    slitpos2 = (500 - slitpos) * w // 1000
    cv2.line(f, (slitpos1, 0), (slitpos1, h), (0, 0, 255), 1)
    cv2.line(f, (slitpos2, 0), (slitpos2, h), (0, 0, 255), 1)


class MyLabel(QLabel):

    def __init__(self, parent=None, func=None):

        self.func = func
        QLabel.__init__(self, parent)
        self.rubberBand = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self.origin = QPoint()
        self.slitpos = 250
        self.focus = (333, 666, 333, 666)  # xs,xe,ys,ye
        self.geometry = (0, 0, 1000, 1000)  # x,y,w,h

    def paintEvent(self, event):
        QLabel.paintEvent(self, event)
        painter = QPainter(self)
        painter.setPen(Qt.GlobalColor.red)
        x, y, w, h = self.geometry
        d = 20
        painter.drawLine(
            x + w // 2 - self.slitpos * w // 1000,
            y,
            x + w // 2 - self.slitpos * w // 1000,
            y + h,
        )
        painter.drawLine(
            x + w // 2 - self.slitpos * w // 1000 - d,
            y + h // 2,
            x + w // 2 - self.slitpos * w // 1000,
            y + h // 2 - d,
        )
        painter.drawLine(
            x + w // 2 - self.slitpos * w // 1000 - d,
            y + h // 2,
            x + w // 2 - self.slitpos * w // 1000,
            y + h // 2 + d,
        )
        painter.drawLine(
            x + w // 2 + self.slitpos * w // 1000,
            y,
            x + w // 2 + self.slitpos * w // 1000,
            y + h,
        )
        painter.drawLine(
            x + w // 2 + self.slitpos * w // 1000 + d,
            y + h // 2,
            x + w // 2 + self.slitpos * w // 1000,
            y + h // 2 - d,
        )
        painter.drawLine(
            x + w // 2 + self.slitpos * w // 1000 + d,
            y + h // 2,
            x + w // 2 + self.slitpos * w // 1000,
            y + h // 2 + d,
        )
        painter.setPen(Qt.GlobalColor.green)
        painter.drawRect(
            x + w * self.focus[0] // 1000,
            y + h * self.focus[2] // 1000,
            w * (self.focus[1] - self.focus[0]) // 1000,
            h * (self.focus[3] - self.focus[2]) // 1000,
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
            self.region = QRect(self.origin, event.pos()).normalized()
            if self.func is not None:
                self.func(self.region)


# https://www.tutorialspoint.com/pyqt/pyqt_qfiledialog_widget.htm
class EditorGUI(QWidget):
    thread_invoker = pyqtSignal()

    def __init__(self, settings, parent=None, filename=None, params=None):
        super(EditorGUI, self).__init__(parent)

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
        # self.destroyed.connect(self.stop_thread)  #does not work
        self.asyncimageloader.frameIncreased.connect(self.updateTimeLine)

        # close on quit
        # http://stackoverflow.com/questions/27420338/how-to-clear-child-window-reference-stored-in-parent-application-when-child-wind
        # self.setAttribute(Qt.WA_DeleteOnClose)
        bottom_pane = self.bottom_pane_layout()
        self.imageselector2 = ImageSelector2()
        self.imageselector2.slider.startValueChanged.connect(self.frameChanged)
        self.imageselector2.slider.endValueChanged.connect(self.frameChanged)
        imageselector_layout = QHBoxLayout()
        imageselector_layout.addWidget(self.imageselector2)
        imageselector_gbox = QGroupBox(self.tr("1. Specify the frame range"))
        imageselector_gbox.setLayout(imageselector_layout)
        glayout = QVBoxLayout()
        glayout.addWidget(imageselector_gbox)
        glayout.addLayout(bottom_pane)
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
        return self.cv2toQImage(thumb)

    def updateTimeLine(self, cv2thumbs):
        # count time and limit update
        now = time.time()
        if now - self.lastupdatethumbs < 0.2:
            return
        # transformation filter
        self.imageselector2.imagebar.setTransformer(self.thumbtransformer)
        self.imageselector2.setThumbs(cv2thumbs)
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
        self.btn = QPushButton(self.tr("-90"))
        self.btn.clicked.connect(self.angle_sub90)
        layout.addWidget(self.btn)
        self.btn = QPushButton(self.tr("-1"))
        self.btn.clicked.connect(self.angle_dec)
        layout.addWidget(self.btn)
        layout.addWidget(QLabel(self.tr("rotation")))
        self.angle_label = QLabel("0 " + self.tr("degrees"))
        layout.addWidget(self.angle_label)
        self.btn = QPushButton(self.tr("+1"))
        self.btn.clicked.connect(self.angle_inc)
        layout.addWidget(self.btn)
        self.btn = QPushButton(self.tr("+90"))
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
        layout = QVBoxLayout()
        self.left_image_pane = DrawableLabel()
        self.left_image_pane.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_image_pane.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.left_image_pane, 1)
        layout.setAlignment(self.left_image_pane, Qt.AlignmentFlag.AlignHCenter)
        layout.setAlignment(self.left_image_pane, Qt.AlignmentFlag.AlignTop)
        return layout

    def crop_image_layout(self):
        layout = QVBoxLayout()
        self.right_image_pane = MyLabel(func=self.show_snapshots)
        self.right_image_pane.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.right_image_pane.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
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
        left_pane_title = QGroupBox(self.tr("2. Repair deformation"))
        left_pane_layout.addWidget(left_pane_title)

        # 左上段
        first_box = QHBoxLayout()
        first_box.addWidget(self.sliderL)
        first_box.addLayout(self.deformation_image_layout(), 1)
        first_box.addWidget(self.sliderR)

        # 左下段
        rotation_deformation_layout = self.rotation_deformation_control()

        combined_box = QVBoxLayout()
        combined_box.addLayout(first_box)
        combined_box.addLayout(rotation_deformation_layout)
        combined_box.setAlignment(
            rotation_deformation_layout, Qt.AlignmentFlag.AlignTop
        )

        left_pane_title.setLayout(combined_box)
        return left_pane_layout

    def right_pane_layout(self):

        self.crop_slider = self.crop_rangeslider_widget()
        self.slit_slider = self.slit_slider_widget()

        right_pane_layout = QVBoxLayout()
        # 右側のパネルのタイトル
        right_pane_title = QGroupBox(self.tr("3. Motion Detection and Slit"))
        right_pane_layout.addWidget(right_pane_title)

        # crop_image_layoutとcrop_sliderを横に並べ
        first_box = QHBoxLayout()
        crop_image_layout = self.crop_image_layout()
        first_box.addLayout(crop_image_layout, 1)
        first_box.addWidget(self.crop_slider)

        # slit_sliderのラベルと本体を横に並べ、
        second_box = QHBoxLayout()
        slit_slider_label = QLabel(self.tr("Slit position"))
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
        self.angle_label.setText("{0} ".format(self.angle_degree) + self.tr("degrees"))
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def angle_dec(self):
        self.angle_degree -= 1
        self.angle_degree %= 360
        self.angle_label.setText("{0} ".format(self.angle_degree) + self.tr("degrees"))
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def angle_add90(self):
        self.angle_degree += 90
        self.angle_degree %= 360
        self.angle_label.setText("{0} ".format(self.angle_degree) + self.tr("degrees"))
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def angle_sub90(self):
        self.angle_degree -= 90
        self.angle_degree %= 360
        self.angle_label.setText("{0} ".format(self.angle_degree) + self.tr("degrees"))
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def frameChanged(self, value):
        self.frame = value
        self.show_snapshots()

    def sliderTL_on_draw(self):
        self.perspective[0] = self.sliderL.start()
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def sliderBL_on_draw(self):
        self.perspective[2] = self.sliderL.end()
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def sliderTR_on_draw(self):
        self.perspective[1] = self.sliderR.start()
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def sliderBR_on_draw(self):
        self.perspective[3] = self.sliderR.end()
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def cv2toQImage(self, cv2image):
        height, width = cv2image.shape[:2]
        return QImage(
            cv2image[:, :, ::-1].copy().data,
            width,
            height,
            width * 3,
            QImage.Format.Format_RGB888,
        )

    def show_snapshots(self):
        """
        put the snapshots in the preview panes
        """
        if self.frame < 0:
            return
        logger = getLogger()
        image = self.asyncimageloader.snapshots[self.frame]
        self.transform = trainscanner.transformation(
            self.angle_degree, self.perspective, [self.croptop, self.cropbottom]
        )
        rotated, warped, cropped = self.transform.process_first_image(image)
        self.put_cv2_image(rotated, self.left_image_pane)

        self.put_cv2_image(cropped, self.right_image_pane)

    def put_cv2_image(self, image, widget):
        height, width = image.shape[0:2]
        qImg = self.cv2toQImage(image)
        pixmap = QPixmap(qImg)

        # Get the current widget size
        widget_width = widget.width()
        widget_height = widget.height()

        # Scale the image to fit the widget while maintaining aspect ratio
        if height > width:
            if height > widget_height:
                pixmap = pixmap.scaledToHeight(
                    widget_height, Qt.TransformationMode.SmoothTransformation
                )
        else:
            if width > widget_width:
                pixmap = pixmap.scaledToWidth(
                    widget_width, Qt.TransformationMode.SmoothTransformation
                )

        widget.setPixmap(pixmap)
        # give hints to DrawableLabel() and MyLabel()
        widget.perspective = self.perspective
        widget.focus = self.focus
        widget.slitpos = self.slitpos
        w = pixmap.width()
        h = pixmap.height()
        x = (widget_width - w) // 2
        y = (widget_height - h) // 2
        widget.geometry = x, y, w, h

    def slit_slider_on_draw(self):
        self.slitpos = self.slit_slider.value()
        self.show_snapshots()

    def croptop_slider_on_draw(self):
        self.croptop = self.crop_slider.start()
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def cropbottom_slider_on_draw(self):
        self.cropbottom = self.crop_slider.end()
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def closeEvent(self, event):
        self.settings.reset_input()
        self.stop_thread()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.show_snapshots()

    #    self.asyncimageloader.stop()

    # This will be the trigger for the first rendering
    # def resizeEvent(self, event):
    #    self.asyncimageloader.render()
