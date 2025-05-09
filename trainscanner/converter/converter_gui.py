#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Core of the GUI and image process
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QApplication,
    QPushButton,
    QCheckBox,
    QFileDialog,
    QProgressBar,
    QRadioButton,
    QButtonGroup,
    QLabel,
)
from PyQt6.QtGui import QPalette, QPainter
from PyQt6.QtCore import QTranslator, QLocale, Qt
import cv2
import numpy as np
import math
import time
import logging

# File handling
import os
import subprocess
import shutil

# final image tranformation
from trainscanner.converter import film
from trainscanner.converter import helix
from trainscanner.converter import rect
from trainscanner.converter import hans_style as hans
from trainscanner.converter import movie
from tiledimage.cachedimage import CachedImage

# options handler
import sys


# Drag and drop work. Buttons would not be necessary.


# https://www.tutorialspoint.com/pyqt/pyqt_qfiledialog_widget.htm
class SettingsGUI(QWidget):
    def __init__(self, parent=None):
        super(SettingsGUI, self).__init__(parent)
        self.setAcceptDrops(True)

        finish_layout = QVBoxLayout()

        # 説明文を追加
        instruction = QLabel(self.tr("Drag & drop an image strip"))
        instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        finish_layout.addWidget(instruction)

        self.btn_finish_perf = QCheckBox(self.tr("Add the film perforations"))
        finish_layout.addWidget(self.btn_finish_perf)

        # ラジオボタングループの作成
        self.image_type_group = QButtonGroup(self)
        self.btn_finish_none = QRadioButton(self.tr("Do nothing"))
        self.btn_finish_helix = QRadioButton(self.tr("Make a helical image"))
        self.btn_finish_rect = QRadioButton(self.tr("Make a rectangular image"))
        self.btn_finish_hans = QRadioButton(self.tr("Make a Hans-style image"))
        self.btn_finish_movie = QRadioButton(self.tr("Make a scrolling movie"))

        # ffmpegの確認
        self.has_ffmpeg = shutil.which("ffmpeg") is not None
        self.btn_finish_movie.setEnabled(self.has_ffmpeg)
        if not self.has_ffmpeg:
            self.btn_finish_movie.setToolTip(
                self.tr(
                    "ffmpeg is not installed. Please install ffmpeg to use this feature."
                )
            )

        self.image_type_group.addButton(self.btn_finish_none)
        self.image_type_group.addButton(self.btn_finish_helix)
        self.image_type_group.addButton(self.btn_finish_rect)
        self.image_type_group.addButton(self.btn_finish_hans)
        self.image_type_group.addButton(self.btn_finish_movie)
        finish_layout.addWidget(self.btn_finish_none)
        finish_layout.addWidget(self.btn_finish_helix)
        finish_layout.addWidget(self.btn_finish_rect)
        finish_layout.addWidget(self.btn_finish_hans)
        finish_layout.addWidget(self.btn_finish_movie)

        self.pbar = QProgressBar()
        self.pbar.setValue(0)
        self.pbar.setRange(0, 6)
        finish_layout.addWidget(self.pbar)

        self.setLayout(finish_layout)
        self.setWindowTitle("Converter")

    def start_process(self):
        logger = logging.getLogger()
        self.pbar.setValue(0)
        if self.filename[-6:] == ".pngs/":
            self.filename = self.filename[:-1]
            cachedimage = CachedImage("inherit", dir=self.filename, disposal=False)
            logger.debug(":: {0}".format(cachedimage))
            img = cachedimage.get_region(None)
        else:
            img = cv2.imread(self.filename)
        file_name = self.filename
        self.pbar.setValue(1)
        if self.btn_finish_perf.isChecked():
            img = film.filmify(img)
            self.pbar.setValue(2)
            file_name += ".film.png"
            cv2.imwrite(file_name, img)
            self.pbar.setValue(3)
        if self.btn_finish_helix.isChecked():
            self.pbar.setValue(4)
            himg = helix.helicify(img)
            self.pbar.setValue(5)
            cv2.imwrite(file_name + ".helix.png", himg)
        elif self.btn_finish_rect.isChecked():
            self.pbar.setValue(4)
            rimg = rect.rectify(img)
            self.pbar.setValue(5)
            cv2.imwrite(file_name + ".rect.png", rimg)
        elif self.btn_finish_movie.isChecked():
            self.pbar.setValue(4)
            movie.make_movie(file_name)
            self.pbar.setValue(5)
        elif self.btn_finish_hans.isChecked():
            self.pbar.setValue(4)
            hansimg = hans.hansify(img)
            self.pbar.setValue(5)
            cv2.imwrite(file_name + ".hans.png", hansimg)
        elif self.btn_finish_none.isChecked():
            self.pbar.setValue(4)
            self.pbar.setValue(5)
        self.pbar.setValue(6)

    def dragEnterEvent(self, event):
        logger = logging.getLogger()
        event.accept()
        mimeData = event.mimeData()
        logger.debug("dragEnterEvent")
        for mimetype in mimeData.formats():
            logger.debug("MIMEType: {0}".format(mimetype))
            logger.debug("Data: {0}".format(mimeData.data(mimetype)))

    def dropEvent(self, event):
        logger = logging.getLogger()
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
                from urllib.parse import urlparse, unquote

                for line in bytes(data).decode("utf8").splitlines():
                    parsed = urlparse(unquote(line))
                    logger.debug("Data: {0}".format(parsed))
                    if parsed.scheme == "file":
                        self.filename = parsed.path
                        # Start immediately
                        self.start_process()
        # or just ignore


# for pyinstaller
def resource_path(relative):
    return os.path.join(os.environ.get("_MEIPASS", os.path.abspath(".")), relative)


import pkgutil


def main():
    logging.basicConfig(
        level=logging.WARN, format="%(asctime)s %(levelname)s %(message)s"
    )
    app = QApplication(sys.argv)
    translator = QTranslator(app)
    path = os.path.dirname(rect.__file__)
    if QLocale.system().language() == QLocale("ja"):
        translator.load(path + "/../i18n/trainscanner_ja")
    app.installTranslator(translator)
    se = SettingsGUI()
    se.show()
    se.raise_()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
