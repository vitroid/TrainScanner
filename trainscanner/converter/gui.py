#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Core of the GUI and image process
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QApplication,
    QPushButton,
    QCheckBox,
    QTabWidget,
    QLabel,
    QButtonGroup,
    QLineEdit,
    QSlider,
)
from PyQt6.QtGui import QKeySequence, QShortcut
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
import trainscanner
from trainscanner.converter import scroll
from trainscanner.converter import helix
from trainscanner.converter import rect
from trainscanner.converter import hans_style as hans
from trainscanner.converter import movie
from trainscanner.converter import list_cli_options
from trainscanner.converter.helix import get_parser as helix_parser
from trainscanner.converter.rect import get_parser as rect_parser
from trainscanner.converter.hans_style import get_parser as hans_parser
from trainscanner.converter.scroll import get_parser as scroll_parser
from trainscanner.converter.movie import get_parser as movie2_parser
from trainscanner.widget.qfloatslider import QFloatSlider
from trainscanner.widget.qlogslider import LogSliderHandle
from trainscanner.widget.qvalueslider import QValueSlider
from tiledimage.cachedimage import CachedImage
from trainscanner.i18n import tr

# options handler
import sys

from concurrent.futures import ThreadPoolExecutor


# Drag and drop work. Buttons would not be necessary.


# https://www.tutorialspoint.com/pyqt/pyqt_qfiledialog_widget.htm
class SettingsGUI(QWidget):
    def __init__(self, parent=None):
        super(SettingsGUI, self).__init__(parent)
        self.setAcceptDrops(True)

        finish_layout = QVBoxLayout()

        # 説明文を追加
        instruction = QLabel(tr("Drag & drop an image strip"))
        instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        finish_layout.addWidget(instruction)

        # self.btn_finish_perf = QCheckBox(tr("Add the film perforations"))
        # finish_layout.addWidget(self.btn_finish_perf)

        # タブウィジェットを作成
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)

        # 各タブの内容を作成
        converters = {
            "hans": {
                "internal_name": "hans_style",
                "options_list": list_cli_options(hans_parser()),
            },
            "rect": {
                "internal_name": "rect",
                "options_list": list_cli_options(rect_parser()),
            },
            "helix": {
                "internal_name": "helix",
                "options_list": list_cli_options(helix_parser()),
            },
            "scroll": {
                "internal_name": "scroll",
                "options_list": list_cli_options(scroll_parser()),
            },
            "movie": {
                "internal_name": "movie",
                "options_list": list_cli_options(movie2_parser()),
            },
        }
        self.getters = dict()
        # ffmpegの確認
        self.has_ffmpeg = shutil.which("ffmpeg") is not None
        self.tab_widgets = []
        for converter, contents in converters.items():
            internal_name = contents["internal_name"]
            options, description = contents["options_list"]

            tab = QWidget()
            tab_layout = QVBoxLayout()
            desc = tr(description)
            if not self.has_ffmpeg and converter in ["movie", "scroll"]:
                desc += " (ffmpeg required)"
                tab.setEnabled(False)
            tab_layout.addWidget(QLabel(desc))

            # オプションの表示
            self.getters[converter] = dict()
            for option in options:
                # オプションのキーワードを取得
                for option_keyword in option["option_strings"]:
                    if option_keyword[:2] == "--":
                        option_keyword = option_keyword[2:]
                        break
                else:
                    continue
                if option["type"] in (int, float):
                    help = option["help"]
                    # print(help, option)
                    min = option["min"]
                    max = option["max"]
                    # sliderの左にラベルを付けたい。
                    hbox = QHBoxLayout()
                    label = QLabel(tr(help))
                    hbox.addWidget(label)
                    if option["type"] == int:
                        slider = QValueSlider()
                        slider.setMinimum(int(min))
                        slider.setMaximum(int(max))
                        if option["default"] is not None:
                            slider.setValue(int(option["default"]))
                        else:
                            slider.setValue(int(min))
                        # スライダーの両端に最小値と最大値を表示したい。
                        min_label = QLabel(f"{int(min)}")
                        max_label = QLabel(f"{int(max)}")
                    else:  # float
                        if 0 < min < max and max / min > 99:
                            slider = QFloatSlider(
                                float_min_value=min,
                                float_max_value=max,
                                sliderhandleclass=LogSliderHandle,
                            )
                        else:
                            slider = QFloatSlider(
                                float_min_value=min,
                                float_max_value=max,
                            )
                        slider.setMinimum(min)
                        slider.setMaximum(max)
                        if option["default"] is not None:
                            slider.setValue(float(option["default"]))
                        else:
                            slider.setValue(min)
                        # スライダーの両端に最小値と最大値を表示したい。
                        min_label = QLabel(f"{min}")
                        max_label = QLabel(f"{max}")
                    hbox.addWidget(min_label)
                    hbox.addWidget(slider)
                    hbox.addWidget(max_label)
                    tab_layout.addLayout(hbox)
                    self.getters[converter][option_keyword] = slider
                elif (
                    option["type"] is None
                    and option["nargs"] == 0
                    and "-h" not in option["option_strings"]
                    and "-R" not in option["option_strings"]
                ):
                    checkbox = QCheckBox(tr(option["help"]))
                    # checkbox.setChecked(option["default"])
                    tab_layout.addWidget(checkbox)
                    self.getters[converter][option_keyword] = checkbox
                elif option["type"] == str:
                    # title付きのテキストフィールド
                    hbox = QHBoxLayout()
                    label = QLabel(tr(option["help"]))
                    hbox.addWidget(label)
                    lineedit = QLineEdit(tr(option["default"]))
                    hbox.addWidget(lineedit)
                    tab_layout.addLayout(hbox)
                    self.getters[converter][option_keyword] = lineedit
                # else:
                #     tab_layout.addWidget(QLabel(tr(option["help"])))
            tab.setLayout(tab_layout)
            self.tab_widget.addTab(tab, tr(converter))
            self.tab_widgets.append(tab)

        finish_layout.addWidget(self.tab_widget)

        # 矢印ボタンとテキストのレイアウト
        arrow_layout = QHBoxLayout()

        # 矢印ラジオボタングループの作成
        self.arrow_group = QButtonGroup(self)

        # 左向き矢印ボタン
        self.btn_left = QPushButton("←")
        self.btn_left.setFixedWidth(50)
        self.btn_left.setCheckable(True)  # チェック可能なボタンに
        self.btn_left.setChecked(True)  # デフォルトで選択
        self.arrow_group.addButton(self.btn_left)
        arrow_layout.addWidget(self.btn_left)

        # "Go"テキスト
        go_label = QLabel(tr("Direction"))
        go_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow_layout.addWidget(go_label)

        # 右向き矢印ボタン
        self.btn_right = QPushButton("→")
        self.btn_right.setFixedWidth(50)
        self.btn_right.setCheckable(True)  # チェック可能なボタンに
        self.arrow_group.addButton(self.btn_right)
        arrow_layout.addWidget(self.btn_right)

        finish_layout.addLayout(arrow_layout)

        self.setLayout(finish_layout)
        self.setWindowTitle(tr("Converter"))

        # Command-Wで閉じるショートカットを追加
        close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        close_shortcut.activated.connect(self.close)

        # Command-Qで終了するショートカットを追加
        quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_shortcut.activated.connect(QApplication.quit)

        self.executor = ThreadPoolExecutor(
            max_workers=4
        )  # クラスの初期化時などで1回だけ作る

    def start_process(self):
        logger = logging.getLogger()
        head_right = self.btn_right.isChecked()
        if self.filename[-6:] == ".pngs/":
            self.filename = self.filename[:-1]
            cachedimage = CachedImage("inherit", dir=self.filename, disposal=False)
            logger.debug(":: {0}".format(cachedimage))
            img = cachedimage.get_region(None)
        else:
            img = cv2.imread(self.filename)
        file_name = self.filename
        # if self.btn_finish_perf.isChecked():
        #     img = film.filmify(img)
        #     file_name += ".film.png"
        #     cv2.imwrite(file_name, img)

        converter = self.tab_widget.tabText(self.tab_widget.currentIndex())
        # gettersを使って、値を取得
        args = dict()
        for option_keyword, option in self.getters[converter].items():
            if isinstance(option, QValueSlider):
                args[option_keyword] = option.get_display_value()
            elif isinstance(option, QLineEdit):
                args[option_keyword] = option.text()
            elif isinstance(option, QCheckBox):
                args[option_keyword] = option.isChecked()
        logger.debug(f"args: {args}")
        # tabのラベルで分岐
        self.executor.submit(
            self.process_image, converter, img, file_name, head_right, args
        )

    def process_image(self, tab, img, file_name, head_right, args):
        if tab == "helix":
            himg = helix.helicify(img, **args)
            cv2.imwrite(file_name + ".helix.png", himg)
        elif tab == "rect":
            rimg = rect.rectify(img, head_right=head_right, **args)
            cv2.imwrite(file_name + ".rect.png", rimg)
        elif tab == "scroll":
            scroll.make_movie(file_name, head_right=head_right, **args)
        elif tab == "movie":
            movie.make_movie(file_name, head_right=head_right, **args)
        elif tab == "hans":
            hansimg = hans.hansify(img, head_right=head_right, **args)
            cv2.imwrite(file_name + ".hans.png", hansimg)

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
        mimetypes = [
            mimetype for mimetype in mimeData.formats() if mimetype == "text/uri-list"
        ]
        if mimetypes:
            data = mimeData.data(mimetypes[0])
            from urllib.parse import urlparse, unquote
            from urllib.request import url2pathname

            for line in bytes(data).decode("utf8").splitlines():
                parsed = urlparse(unquote(line))
                logger.debug("Data: {0}".format(parsed))
                if parsed.scheme == "file":
                    self.filename = url2pathname(parsed.path)
                    # Start immediately
                    self.start_process()
        # or just ignore


# for pyinstaller
def resource_path(relative):
    return os.path.join(os.environ.get("_MEIPASS", os.path.abspath(".")), relative)


import pkgutil


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    logger = logging.getLogger()
    app = QApplication(sys.argv)
    translator = QTranslator(app)
    path = os.path.dirname(trainscanner.__file__)
    logger.debug(f"Application path: {path}")

    # まずLANG環境変数を確認
    lang = os.environ.get("LANG", "").split("_")[0]
    logger.debug(f"LANG environment variable: {lang}")

    # LANGが設定されていない場合はQLocaleを使用
    if not lang:
        locale = QLocale()
        lang = locale.name().split("_")[0]
        logger.debug(f"Using QLocale language: {lang}")

    qm_path = None
    if lang == "ja":
        qm_path = path + "/i18n/trainscanner_ja"
    elif lang == "fr":
        qm_path = path + "/i18n/trainscanner_fr"

    if qm_path:
        logger.debug(f"Loading Qt translations from: {qm_path}")
        if translator.load(qm_path):
            logger.debug("Successfully loaded Qt translations")
            app.installTranslator(translator)
        else:
            logger.error("Failed to load Qt translations")

    # 独自の翻訳システムを初期化
    from trainscanner.i18n import init_translations

    logger.debug("Initializing custom translation system")
    init_translations()

    se = SettingsGUI()
    se.show()
    se.raise_()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
