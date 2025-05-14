#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import math

# File handling
import os
import subprocess

# options handler
import sys
import time
from logging import DEBUG, WARN, basicConfig, getLogger, root

# external modules
import cv2
import numpy as np
from PyQt6.QtCore import (
    QLocale,
    QObject,
    QPoint,
    QRect,
    QSize,
    Qt,
    QThread,
    QTranslator,
    pyqtSignal,
)
from PyQt6.QtGui import QImage, QPainter, QPixmap

# Core of the GUI and image process
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRubberBand,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

#
# sub dialog windows
# private modules
from trainscanner import pass1_gui
from trainscanner import qrangeslider as rs
from trainscanner import stitch_gui, trainscanner, video
from trainscanner.imageselector2 import ImageSelector2
from trainscanner.pass1 import prepare_parser as pp1
from trainscanner.stitch import prepare_parser as pp2

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
        logger.debug("Open video: {0}".format(filename))
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
class SettingsGUI(QWidget):
    def __init__(self, parent=None):
        super(SettingsGUI, self).__init__(parent)
        self.setAcceptDrops(True)

        # options
        self.trailing = 30
        self.editor = None
        self.antishake = 5
        self.estimate = 10
        self.slitwidth = 50
        self.identity = 0.5
        self.accel = 1

        # private
        # layout
        layout = QHBoxLayout()

        # leftmost panel for specifying options
        left_layout = QVBoxLayout()
        self.btn = QPushButton(self.tr("Open a movie"))
        self.btn.clicked.connect(self.getfile)
        left_layout.addWidget(self.btn)

        self.le = QLabel(self.tr("(File name appears here)"))
        # self.le = QLabel()
        left_layout.addWidget(self.le)

        # self.pbar = QProgressBar()
        # self.pbar.setValue(0)
        # left_layout.addWidget(self.pbar)

        # Left panel, upper pane: settings
        gbox_settings = QGroupBox(self.tr("Settings"))
        settings2_layout = QGridLayout()
        rows = 0
        # http://myenigma.hatenablog.com/entry/2016/01/24/113413

        # Example of a slider with a label ###################################
        # the slider is in a Hbox

        settings2_layout.addWidget(
            QLabel(self.tr("Slit mixing")), rows, 0, Qt.AlignmentFlag.AlignRight
        )

        self.slitwidth_slider_valuelabel = QLabel("{0}%".format(self.slitwidth))
        settings2_layout.addWidget(
            self.slitwidth_slider_valuelabel, rows, 1, Qt.AlignmentFlag.AlignCenter
        )

        settings2_layout.addWidget(
            QLabel(self.tr("Sharp")), rows, 2, Qt.AlignmentFlag.AlignRight
        )
        self.slitwidth_slider = QSlider(Qt.Orientation.Horizontal)  # スライダの向き
        self.slitwidth_slider.setRange(5, 300)  # スライダの範囲
        self.slitwidth_slider.setValue(self.slitwidth)  # 初期値
        self.slitwidth_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slitwidth_slider.valueChanged.connect(self.slitwidth_slider_on_draw)
        settings2_layout.addWidget(self.slitwidth_slider, rows, 3)
        settings2_layout.addWidget(QLabel(self.tr("Diffuse")), rows, 4)

        rows += 1
        #####################################################################

        # Example of a slider with a label ###################################
        # the slider is in a Hbox

        settings2_layout.addWidget(
            QLabel(self.tr("Minimal displacement between the frames")),
            rows,
            0,
            Qt.AlignmentFlag.AlignRight,
        )

        self.antishake_slider_valuelabel = QLabel(
            "{0} ".format(self.antishake) + self.tr("pixels")
        )
        settings2_layout.addWidget(
            self.antishake_slider_valuelabel, rows, 1, Qt.AlignmentFlag.AlignCenter
        )

        settings2_layout.addWidget(
            QLabel(self.tr("Small")), rows, 2, Qt.AlignmentFlag.AlignRight
        )
        self.antishake_slider = QSlider(Qt.Orientation.Horizontal)  # スライダの向き
        self.antishake_slider.setRange(0, 15)  # スライダの範囲
        self.antishake_slider.setValue(5)  # 初期値
        # スライダの目盛りを両方に出す
        self.antishake_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.antishake_slider.valueChanged.connect(self.antishake_slider_on_draw)
        settings2_layout.addWidget(self.antishake_slider, rows, 3)
        settings2_layout.addWidget(QLabel(self.tr("Large")), rows, 4)

        rows += 1
        #####################################################################

        # Example of a slider with a label ###################################
        # the slider is in a Hbox

        settings2_layout.addWidget(
            QLabel(self.tr("Number of frames to estimate the velocity")),
            rows,
            0,
            Qt.AlignmentFlag.AlignRight,
        )

        self.estimate_slider_valuelabel = QLabel(
            "{0} ".format(self.estimate) + self.tr("frames")
        )
        settings2_layout.addWidget(
            self.estimate_slider_valuelabel, rows, 1, Qt.AlignmentFlag.AlignCenter
        )

        settings2_layout.addWidget(
            QLabel(self.tr("Short")), rows, 2, Qt.AlignmentFlag.AlignRight
        )
        self.estimate_slider = QSlider(Qt.Orientation.Horizontal)  # スライダの向き
        self.estimate_slider.setRange(5, 50)  # スライダの範囲
        self.estimate_slider.setValue(10)  # 初期値
        # スライダの目盛りを両方に出す
        self.estimate_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.estimate_slider.valueChanged.connect(self.estimate_slider_on_draw)
        settings2_layout.addWidget(self.estimate_slider, rows, 3)
        settings2_layout.addWidget(QLabel(self.tr("Long")), rows, 4)

        rows += 1
        #####################################################################

        #####################################################################
        # Example of a checkbox
        settings2_layout.addWidget(
            QLabel(self.tr("Ignore vertical displacements")),
            rows,
            0,
            Qt.AlignmentFlag.AlignRight,
        )
        self.btn_zerodrift = QCheckBox()
        self.btn_zerodrift.setCheckState(Qt.CheckState.Checked)
        # self.b2.toggled.connect(lambda:self.btnstate(self.b2))
        settings2_layout.addWidget(
            self.btn_zerodrift, rows, 1, Qt.AlignmentFlag.AlignCenter
        )
        rows += 1
        #####################################################################

        #####################################################################
        # Example of a checkbox
        settings2_layout.addWidget(
            QLabel(
                self.tr("The train is initially stalling in the motion detection area.")
            ),
            rows,
            0,
            Qt.AlignmentFlag.AlignRight,
        )
        self.btn_stall = QCheckBox()
        # self.btn_stall.setCheckState(Qt.CheckState.Checked)
        # self.b2.toggled.connect(lambda:self.btnstate(self.b2))
        settings2_layout.addWidget(
            self.btn_stall, rows, 1, Qt.AlignmentFlag.AlignCenter
        )
        rows += 1
        #####################################################################

        # #####################################################################
        # #Example of a checkbox
        settings2_layout.addWidget(
            QLabel(self.tr("Max acceleration")), rows, 0, Qt.AlignmentFlag.AlignRight
        )
        # self.btn_accel = QCheckBox()
        # self.btn_accel.setCheckState(Qt.CheckState.Checked)
        # settings2_layout.addWidget(self.btn_accel,rows, 1)
        # rows += 1
        # #####################################################################
        # #Example of a slider with a label ###################################
        # #the slider is in a Hbox

        # #settings2_layout.addWidget(QLabel(self.tr('Permit camera waggle')), rows, 0, Qt.AlignmentFlag.AlignRight)

        self.accel_slider_valuelabel = QLabel(str(self.accel))
        settings2_layout.addWidget(self.accel_slider_valuelabel, rows, 1)

        settings2_layout.addWidget(QLabel(self.tr("Tripod")), rows, 2)
        self.accel_slider = QSlider(Qt.Orientation.Horizontal)  # スライダの向き
        self.accel_slider.setRange(1, 15)  # スライダの範囲
        self.accel_slider.setValue(1)  # 初期値
        self.accel_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.accel_slider.valueChanged.connect(self.accel_slider_on_draw)
        settings2_layout.addWidget(self.accel_slider, rows, 3)
        settings2_layout.addWidget(QLabel(self.tr("Handheld")), rows, 4)
        # self.btn_accel.toggled.connect(self.btn_accel_toggle)

        rows += 1
        # #####################################################################

        # #Example of a checkbox and slider with a label
        # #-i (identity)

        # settings2_layout.addWidget(QLabel(self.tr('Skip identical frames')), rows, 0, Qt.AlignmentFlag.AlignRight)

        # #self.btn_skipident = QCheckBox(self.tr('Skip identical frames'))
        # #self.b2.toggled.connect(lambda:self.btnstate(self.b2))
        # #skipident_layout.addWidget(self.btn_skipident)

        # self.skipident_valuelabel = QLabel(str(self.identity))
        # settings2_layout.addWidget(self.skipident_valuelabel, rows, 1)

        # settings2_layout.addWidget(QLabel(self.tr('Strict')), rows, 2)
        # self.identthres_slider = QSlider(Qt.Orientation.Horizontal)  # スライダの向き
        # self.identthres_slider.setRange(1, 5)  # スライダの範囲
        # self.identthres_slider.setValue(2)  # 初期値
        # #スライダの目盛りを両方に出す
        # self.identthres_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        # self.connect(self.identthres_slider, SIGNAL('valueChanged(int)'), self.identthres_slider_on_draw)
        # #the slider is in a Hbox
        # settings2_layout.addWidget(self.identthres_slider, rows, 3)
        # settings2_layout.addWidget(QLabel(self.tr('Loose')), rows, 4)
        # rows += 1
        # #####################################################################

        # Example of a slider with a label ###################################
        # the slider is in a Hbox

        settings2_layout.addWidget(
            QLabel(self.tr("Trailing frames")), rows, 0, Qt.AlignmentFlag.AlignRight
        )

        self.trailing_slider_valuelabel = QLabel(
            "{0} ".format(self.trailing) + self.tr("frames")
        )
        settings2_layout.addWidget(
            self.trailing_slider_valuelabel, rows, 1, Qt.AlignmentFlag.AlignCenter
        )

        settings2_layout.addWidget(
            QLabel(self.tr("Short")), rows, 2, Qt.AlignmentFlag.AlignRight
        )
        self.trailing_slider = QSlider(Qt.Orientation.Horizontal)  # スライダの向き
        self.trailing_slider.setRange(1, 150)  # スライダの範囲
        self.trailing_slider.setValue(10)  # 初期値
        # スライダの目盛りを両方に出す
        self.trailing_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.trailing_slider.valueChanged.connect(self.trailing_slider_on_draw)
        settings2_layout.addWidget(self.trailing_slider, rows, 3)
        settings2_layout.addWidget(QLabel(self.tr("Long")), rows, 4)

        rows += 1
        #####################################################################

        #####################################################################
        # Example of a checkbox
        settings2_layout.addWidget(
            QLabel(self.tr("Debug")), rows, 0, Qt.AlignmentFlag.AlignRight
        )
        self.btn_debug = QCheckBox()
        # self.btn_stall.setCheckState(Qt.CheckState.Checked)
        self.btn_debug.toggled.connect(self.toggle_debug)
        settings2_layout.addWidget(
            self.btn_debug, rows, 1, Qt.AlignmentFlag.AlignCenter
        )
        rows += 1
        #####################################################################

        gbox_settings.setLayout(settings2_layout)

        left_layout.addWidget(gbox_settings)

        # Left panel, lower pane: finish

        finish_layout_gbox = QGroupBox(self.tr("Finish"))
        finish_layout = QVBoxLayout()

        length_layout = QHBoxLayout()
        length_layout.addWidget(
            QLabel(self.tr("Set the upper bound of the product image width"))
        )
        self.btn_length = QCheckBox()
        length_layout.addWidget(self.btn_length)
        spin = QSpinBox()
        spin.setMinimum(100)
        spin.setMaximum(500000)
        spin.setValue(10000)
        spin.setMinimumWidth(50)
        self.spin_length = spin
        length_layout.addWidget(spin)
        length_layout.addWidget(QLabel(self.tr("pixels")))

        finish_layout.addLayout(length_layout)
        # https://www.tutorialspoint.com/pyqt/pyqt_qcheckbox_widget.htm
        self.start_button = QPushButton(self.tr("Start"), self)
        self.start_button.clicked.connect(self.start_process)
        finish_layout.addWidget(self.start_button)

        finish_layout_gbox.setLayout(finish_layout)
        left_layout.addWidget(finish_layout_gbox)

        # combine panels
        layout.addLayout(left_layout)
        self.setLayout(layout)
        self.setWindowTitle("Settings")

    def dragEnterEvent(self, event):
        logger = getLogger()
        event.accept()
        mimeData = event.mimeData()
        logger.debug("dragEnterEvent")
        for mimetype in mimeData.formats():
            logger.debug("MIMEType: {0}".format(mimetype))
            logger.debug("Data: {0}".format(mimeData.data(mimetype)))

    def dropEvent(self, event):
        logger = getLogger()
        event.accept()
        mimeData = event.mimeData()
        logger.debug("dropEvent")
        for mimetype in mimeData.formats():
            logger.debug("MIMEType: {0}".format(mimetype))
            logger.debug("Data: {0}".format(mimeData.data(mimetype)))
        # Open only when:
        # 1. Only file is given
        # 3. and the mimetipe is text/uri-list
        # 2. That has the regular extension.
        logger.debug("len:{0}".format(len(mimeData.formats())))
        if len(mimeData.formats()) == 1:
            mimetype = mimeData.formats()[0]
            if mimetype == "text/uri-list":
                data = mimeData.data(mimetype)
                from urllib.parse import unquote, urlparse

                for line in bytes(data).decode("utf8").splitlines():
                    parsed = urlparse(unquote(line))
                    logger.debug("Data: {0}".format(parsed))
                    if parsed.scheme == "file":
                        if self.editor is not None:
                            self.editor.close()
                        self.fileparser(parsed.path)
                        return
        # or just ignore

    def reset_input(self):
        self.filename = ""
        self.editor = None
        self.le.setText(self.tr("(File name appears here)"))

    def getfile(self):
        logger = getLogger()
        if self.editor is not None:
            self.editor.close()
        logger.debug("Let's select a file")
        filename, types = QFileDialog.getOpenFileName(
            self,
            self.tr("Open a movie file"),
            "",
            "Movie files (*.mov *.mp4 *.m4v *.mts *.tsconf)",
        )
        logger.debug("File: {0}".format(filename))
        if filename == "":  # or if the file cannot be opened,
            return
        self.fileparser(filename)

    def fileparser(self, filename):
        logger = getLogger()
        self.filename = filename
        if self.filename.rfind(".tsconf") + 7 == len(self.filename):
            # read all initial values from the file.
            ap = argparse.ArgumentParser(description="TrainScanner")
            parser_stitch = pp2(ap)
            # Set priority to the path of the given tsconf
            tsconf = self.filename
            tsconfdir = os.path.dirname(tsconf)
            if tsconfdir == "":
                tsconfdir = "."

            ## modified params,unknown = parser_stitch.parse_known_args(["@"+tsconf])
            with open(tsconf) as f:
                args = f.read().splitlines()
            params, unknown = parser_stitch.parse_known_args(args)
            logger.debug("Params1 {0} {1}".format(params, unknown))
            unknown += [params.filename]  # supply filename for pass1 parser
            # Assume the movie file is in the same dir as the tsconf
            self.filename = tsconfdir + "/" + os.path.basename(params.filename)
            # Otherwise use the path written in the tsconf file. (original location)
            if not os.path.exists(self.filename):
                self.filename = params.filename
            logger.debug("Movie  {0}".format(self.filename))
            parser_pass1 = pp1()
            ## modified params2,unknown2 = parser_pass1.parse_known_args(["@"+tsconf])
            params2, unknown2 = parser_pass1.parse_known_args(args)
            logger.debug("Params2 {0} {1}".format(params2, unknown2))
            # Only non-default values should overwrite the pp2 result.
            p1 = vars(params)
            p2 = vars(params2)
            for key in p2:
                p1[key] = p2[key]
            # set variables in self
            # and make the editor also.
            # Overwrite the filename
            p1["filename"] = self.filename
            self.editor = EditorGUI(self, params=p1)
            self.slitwidth_slider.setValue(int(p1["slitwidth"] * 100))
            self.antishake_slider.setValue(p1["antishake"])
            self.estimate_slider.setValue(p1["estimate"])
            if p1["zero"]:
                self.btn_zerodrift.setCheckState(Qt.CheckState.Checked)
            else:
                self.btn_zerodrift.setCheckState(Qt.CheckState.Unchecked)
            if p1["stall"]:
                self.btn_stall.setCheckState(Qt.CheckState.Checked)
            else:
                self.btn_stall.setCheckState(Qt.CheckState.Unchecked)
            self.trailing_slider.setValue(p1["trailing"])

        else:
            self.editor = EditorGUI(self, filename=self.filename)
        # dir = os.path.dirname(self.filename)
        # base = os.path.basename(self.filename)
        # self.filename = "sample3.mov"
        self.editor.show()

        # we shall set editor's values here.
        self.editor.sliderL.setMin(0)
        self.editor.sliderL.setMax(1000)
        self.editor.sliderL.setRange(
            self.editor.perspective[0], self.editor.perspective[2], 10
        )
        self.editor.sliderR.setMin(0)
        self.editor.sliderR.setMax(1000)
        self.editor.sliderR.setRange(
            self.editor.perspective[1], self.editor.perspective[3], 10
        )
        logger.debug(
            "setRange crop {0} {1}".format(self.editor.croptop, self.editor.cropbottom)
        )
        self.editor.crop_slider.setMin(0)
        self.editor.crop_slider.setMax(1000)
        self.editor.crop_slider.setRange(
            self.editor.croptop, self.editor.cropbottom, 10
        )
        self.editor.slit_slider.setValue(self.editor.slitpos)
        self.editor.angle_label.setText(
            "{0} ".format(self.editor.angle_degree) + self.tr("degrees")
        )
        self.le.setText(self.filename)

    def toggle_debug(self):
        # Once remove all the handlers
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        if self.btn_debug.isChecked():
            print("!!!")
            basicConfig(
                level=DEBUG,
                # filename='log.txt',
                format="%(asctime)s %(levelname)s %(message)s",
            )
        else:
            basicConfig(level=WARN, format="%(asctime)s %(levelname)s %(message)s")

    def trailing_slider_on_draw(self):
        self.trailing = self.trailing_slider.value()
        self.trailing_slider_valuelabel.setText(
            "{0} ".format(self.trailing) + self.tr("frames")
        )

    def slitwidth_slider_on_draw(self):
        self.slitwidth = self.slitwidth_slider.value()
        self.slitwidth_slider_valuelabel.setText("{0}%".format(self.slitwidth))

    def antishake_slider_on_draw(self):
        self.antishake = self.antishake_slider.value()
        self.antishake_slider_valuelabel.setText(
            "{0} ".format(self.antishake) + self.tr("pixels")
        )

    def estimate_slider_on_draw(self):
        self.estimate = self.estimate_slider.value()
        self.estimate_slider_valuelabel.setText(
            "{0} ".format(self.estimate) + self.tr("frames")
        )

    def accel_slider_on_draw(self):
        self.accel = self.accel_slider.value()
        self.accel_slider_valuelabel.setText(str(self.accel))

    ##    def identthres_slider_on_draw(self):
    ##        self.identity = self.identthres_slider.value()
    ##        self.skipident_valuelabel.setText(str(self.identity))

    def start_process(self):
        logger = getLogger()
        if self.editor is None:
            return
        now = int(time.time()) % 100000
        logfilenamebase = self.filename + ".{0}".format(now)
        stitch_options = []
        stitch_options += ["slit={0}".format(self.editor.slitpos)]
        stitch_options += ["width={0}".format(self.slitwidth / 100.0)]
        if self.btn_length.isChecked():
            stitch_options += ["length={0}".format(self.spin_length.value())]

        common_options = []
        common_options += [
            "--perspective",
        ] + [str(x) for x in self.editor.perspective]
        common_options += ["--rotate", "{0}".format(self.editor.angle_degree)]
        common_options += [
            "--crop",
        ] + [str(x) for x in (self.editor.croptop, self.editor.cropbottom)]
        pass1_options = []
        pass1_options += ["--trail", "{0}".format(self.trailing)]
        pass1_options += ["--antishake", "{0}".format(self.antishake)]
        pass1_options += ["--estimate", "{0}".format(self.estimate)]
        pass1_options += ["--identity", "{0}".format(self.identity)]
        pass1_options += [
            "--skip",
            "{0}".format(self.editor.imageselector2.slider.start() * 10),
        ]
        pass1_options += [
            "--last",
            "{0}".format(self.editor.imageselector2.slider.end() * 10),
        ]
        pass1_options += [
            "--focus",
        ] + [str(x) for x in self.editor.focus]
        if self.btn_zerodrift.isChecked():
            pass1_options += [
                "--zero",
            ]
        if self.btn_stall.isChecked():
            pass1_options += [
                "--stall",
            ]
        pass1_options += ["--maxaccel", "{0}".format(self.accel)]
        pass1_options += ["--log", logfilenamebase]

        # wrap the options to record in the tsconf file
        # THIS IS WEIRD. FIND BETTER WAY.
        # LOG FILE MADE BY PASS1_GUI IS DIFFERENT FROM THAT BY GUI5.PY..
        # IT IS ALSO WEIRD.
        # PASS1 must write the options and settings in the tsconf by itself.
        argv = (
            [
                "pass1",
            ]
            + common_options
            + pass1_options
        )
        for op in stitch_options:
            argv += ["-2", op]
        argv += [
            self.filename,
        ]

        matcher = pass1_gui.MatcherUI(argv, False)  # do not terminate
        matcher.exec()
        if matcher.terminated or not matcher.success:
            matcher = None
            return
        matcher = None
        argv = ["stitch"]
        ## modified argv += [ "@"+logfilenamebase+".tsconf",]
        argv += [
            "--file",
            logfilenamebase + ".tsconf",
        ]

        stitcher = stitch_gui.StitcherUI(argv, False)
        file_name = stitcher.stitcher.outfilename
        stitcher.setMaximumHeight(500)
        stitcher.showMaximized()
        stitcher.exec()
        stitcher = None

    def closeEvent(self, event):
        if self.editor is not None:
            self.editor.close()


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
        layout = self.make_layout()
        self.imageselector2 = ImageSelector2()
        self.imageselector2.slider.startValueChanged.connect(self.frameChanged)
        self.imageselector2.slider.endValueChanged.connect(self.frameChanged)
        imageselector_layout = QHBoxLayout()
        imageselector_layout.addWidget(self.imageselector2)
        imageselector_gbox = QGroupBox(self.tr("1. Seek the first video frame"))
        imageselector_gbox.setLayout(imageselector_layout)
        glayout = QVBoxLayout()
        glayout.addWidget(imageselector_gbox)
        glayout.addLayout(layout)
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

    def make_layout(self):
        # layout
        layout = QHBoxLayout()

        # second left panel for image rotation
        rotation_layout = QHBoxLayout()
        self.btn = QPushButton(self.tr("-90"))
        self.btn.clicked.connect(self.angle_sub90)
        rotation_layout.addWidget(self.btn)
        self.btn = QPushButton(self.tr("-1"))
        self.btn.clicked.connect(self.angle_dec)
        rotation_layout.addWidget(self.btn)
        rotation_layout.addWidget(QLabel(self.tr("rotation")))
        self.angle_label = QLabel("0 " + self.tr("degrees"))
        rotation_layout.addWidget(self.angle_label)
        self.btn = QPushButton(self.tr("+1"))
        self.btn.clicked.connect(self.angle_inc)
        rotation_layout.addWidget(self.btn)
        self.btn = QPushButton(self.tr("+90"))
        self.btn.clicked.connect(self.angle_add90)
        rotation_layout.addWidget(self.btn)

        #
        crop_layout = QVBoxLayout()
        self.crop_slider = rs.QRangeSlider(
            splitterWidth=10, vertical=True
        )  # スライダの向き
        self.crop_slider.setMinimumWidth(15)
        self.crop_slider.setStyleSheet(cropCSS)
        self.crop_slider.setDrawValues(False)
        self.crop_slider.startValueChanged.connect(self.croptop_slider_on_draw)
        self.crop_slider.endValueChanged.connect(self.cropbottom_slider_on_draw)
        # self.crop_slider.setMinimumHeight(500)

        crop_layout.addWidget(self.crop_slider)

        self.sliderL = rs.QRangeSlider(
            splitterWidth=10, vertical=True
        )  # スライダの向き
        self.sliderL.setMinimumWidth(15)
        self.sliderL.setStyleSheet(perspectiveCSS)
        self.sliderL.setDrawValues(False)
        self.sliderL.startValueChanged.connect(self.sliderTL_on_draw)
        self.sliderL.endValueChanged.connect(self.sliderBL_on_draw)
        # self.sliderL.setMinimumHeight(500)

        self.sliderR = rs.QRangeSlider(
            splitterWidth=10, vertical=True
        )  # スライダの向き
        self.sliderR.setMinimumWidth(15)
        self.sliderR.setStyleSheet(perspectiveCSS)
        self.sliderR.setDrawValues(False)
        self.sliderR.startValueChanged.connect(self.sliderTR_on_draw)
        self.sliderR.endValueChanged.connect(self.sliderBR_on_draw)
        # self.sliderR.setMinimumHeight(500)

        raw_image_layout = QVBoxLayout()
        self.raw_image_pane = DrawableLabel()
        self.raw_image_pane.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.raw_image_pane.setMinimumSize(self.preview_size, self.preview_size)
        raw_image_layout.addWidget(self.raw_image_pane)
        raw_image_layout.setAlignment(
            self.raw_image_pane, Qt.AlignmentFlag.AlignHCenter
        )
        raw_image_layout.setAlignment(self.raw_image_pane, Qt.AlignmentFlag.AlignTop)

        processed_edit_gbox_layout = QVBoxLayout()
        processed_edit_gbox = QGroupBox(self.tr("3. Motion Detection and Slit"))
        box = QVBoxLayout()
        processed_image_layout = QVBoxLayout()
        self.processed_pane = MyLabel(func=self.show_snapshots)
        self.processed_pane.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.processed_pane.setMinimumSize(self.preview_size, self.preview_size)
        processed_image_layout.addWidget(self.processed_pane)
        processed_image_layout.setAlignment(
            self.processed_pane, Qt.AlignmentFlag.AlignTop
        )

        hbox = QHBoxLayout()
        hbox.addLayout(processed_image_layout)
        hbox.addLayout(crop_layout)
        box.addLayout(hbox)
        processed_edit_gbox.setLayout(box)
        processed_edit_gbox_layout.addWidget(processed_edit_gbox)

        slit_slider_label = QLabel(self.tr("Slit position"))
        self.slit_slider = QSlider(Qt.Orientation.Horizontal)  # スライダの向き
        self.slit_slider.setRange(-500, 500)  # スライダの範囲
        # スライダの目盛りを両方に出す
        self.slit_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slit_slider.valueChanged.connect(self.slit_slider_on_draw)
        slit_slider_layout = QHBoxLayout()
        slit_slider_layout.addWidget(slit_slider_label)
        slit_slider_layout.addWidget(self.slit_slider)
        box.addLayout(slit_slider_layout)
        box.setAlignment(slit_slider_layout, Qt.AlignmentFlag.AlignTop)

        # combine panels
        topleft_layout = QHBoxLayout()
        topleft_layout.addWidget(self.sliderL)
        topleft_layout.addLayout(raw_image_layout)
        topleft_layout.addWidget(self.sliderR)
        left_layout = QVBoxLayout()
        left_layout.addLayout(topleft_layout)
        left_layout.addLayout(rotation_layout)
        left_layout.setAlignment(rotation_layout, Qt.AlignmentFlag.AlignTop)
        raw_edit_gbox = QGroupBox(self.tr("2. Repair deformation"))
        raw_edit_gbox.setLayout(left_layout)
        raw_edit_gbox_layout = QVBoxLayout()
        raw_edit_gbox_layout.addWidget(raw_edit_gbox)
        layout.addLayout(raw_edit_gbox_layout)
        layout.addLayout(processed_edit_gbox_layout)
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

    def show_snapshots(self, region=None):
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
        self.put_cv2_image(rotated, self.raw_image_pane)
        if region is not None:
            logger.debug("show_snapshot region {0}".format(region))
            # assume the QLabel size is square preview_size x preview_size
            top, left, bottom, right = (
                region.top(),
                region.left(),
                region.bottom(),
                region.right(),
            )
            if top < 0:
                top = 0
            if left < 0:
                left = 0
            if right > self.preview_size:
                right = self.preview_size
            if bottom > self.preview_size:
                bottom = self.preview_size
            # and also assume that the cropped image is centered and sometimes shrinked.
            top -= self.preview_size // 2
            bottom -= self.preview_size // 2
            left -= self.preview_size // 2
            right -= self.preview_size // 2
            # expected image size in the window
            height, width = cropped.shape[0:2]
            if height > width:
                if height > self.preview_size:
                    width = width * self.preview_size // height
                    height = self.preview_size
            else:
                if width > self.preview_size:
                    height = height * self.preview_size // width
                    width = self.preview_size
            # indicate the region size relative to the image size
            top = top * 1000 // height + 500
            bottom = bottom * 1000 // height + 500
            left = left * 1000 // width + 500
            right = right * 1000 // width + 500
            if top < 0:
                top = 0
            if top > 1000:
                top = 1000
            if bottom < 0:
                bottom = 0
            if bottom > 1000:
                bottom = 1000
            if left < 0:
                left = 0
            if left > 1000:
                left = 1000
            if right < 0:
                right = 0
            if right > 1000:
                right = 1000
            self.focus = left, right, top, bottom

        self.put_cv2_image(cropped, self.processed_pane)

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


# for pyinstaller
def resource_path(relative):
    return os.path.join(os.environ.get("_MEIPASS", os.path.abspath(".")), relative)


def main():
    # pyqt_set_trace()
    basicConfig(level=WARN, format="%(asctime)s %(levelname)s %(message)s")
    app = QApplication(sys.argv)
    translator = QTranslator(app)
    path = os.path.dirname(trainscanner.__file__)

    # まずLANG環境変数を確認
    lang = os.environ.get("LANG", "").split("_")[0]

    # LANGが設定されていない場合はQLocaleを使用
    if not lang:
        locale = QLocale()
        lang = locale.name().split("_")[0]

    if lang == "ja":
        translator.load(path + "/i18n/trainscanner_ja")
    elif lang == "fr":
        translator.load(path + "/i18n/trainscanner_fr")
    app.installTranslator(translator)
    se = SettingsGUI()
    se.show()
    se.raise_()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
