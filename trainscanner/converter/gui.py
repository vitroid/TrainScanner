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
    QSplitter,
)
from PyQt6.QtGui import QKeySequence, QShortcut, QPixmap, QImage
from PyQt6.QtCore import QTranslator, QLocale, Qt, QTimer
import cv2
import numpy as np
import math
import time
import logging

# File handling
import os
import subprocess
import shutil
from itertools import cycle

# final image tranformation
import trainscanner
from trainscanner.converter import helix
from trainscanner.converter import rect
from trainscanner.converter import movie
from trainscanner.converter import list_cli_options
from trainscanner.converter.helix import get_parser as helix_parser
from trainscanner.converter.rect import get_parser as rect_parser
from trainscanner.converter.movie import get_parser as movie2_parser
from trainscanner.widget.qfloatslider import QFloatSlider
from trainscanner.widget.qlogslider import LogSliderHandle
from trainscanner.widget.qvalueslider import QValueSlider
from tiledimage.cachedimage import CachedImage
from trainscanner.i18n import tr

# options handler
import sys

from concurrent.futures import ThreadPoolExecutor
from trainscanner.widget import cv2toQImage

# Drag and drop work. Buttons would not be necessary.


def image_loader(filename, width=None):
    if filename[-6:] == ".pngs/":
        filename = filename[:-1]
        cachedimage = CachedImage("inherit", dir=filename, disposal=False)
        current_image = cachedimage.get_region(None)
    else:
        current_image = cv2.imread(filename)
    if width:
        # アスペクト比を保ったまま幅を5000にする。
        current_image = cv2.resize(
            current_image,
            (width, current_image.shape[0] * width // current_image.shape[1]),
        )
    return current_image


# https://www.tutorialspoint.com/pyqt/pyqt_qfiledialog_widget.htm
class SettingsGUI(QWidget):
    def __init__(self, parent=None):
        super(SettingsGUI, self).__init__(parent)
        self.setAcceptDrops(True)
        self.current_image = None  # 現在の画像を保持
        self.logger = logging.getLogger(__name__)  # クラス固有のロガーを作成
        self.movie_preview_timer = None  # 動画プレビュー用のタイマー
        self.movie_frames = None  # 動画フレームのイテレータ

        # メインの水平レイアウトを作成
        main_layout = QHBoxLayout()

        # 左側のウィジェット（既存の設定部分）
        left_widget = QWidget()
        finish_layout = QVBoxLayout()

        # ファイルパス表示用のラベルを追加
        self.file_path_label = QLabel(tr("No file selected"))
        self.file_path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        finish_layout.addWidget(self.file_path_label)

        # 説明文を追加
        instruction = QLabel(tr("Drag & drop an image strip"))
        instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        finish_layout.addWidget(instruction)

        # self.btn_finish_perf = QCheckBox(tr("Add the film perforations"))
        # finish_layout.addWidget(self.btn_finish_perf)

        # タブウィジェットを作成
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_widget.currentChanged.connect(
            self.on_tab_changed
        )  # タブ切り替え時のシグナルを接続

        # 各タブの内容を作成
        converters = {
            "rect": {
                "internal_name": "rect",
                "options_list": list_cli_options(rect_parser()),
            },
            "helix": {
                "internal_name": "helix",
                "options_list": list_cli_options(helix_parser()),
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
            if not self.has_ffmpeg and converter in [
                "movie",
            ]:
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
                    min = option["min"]
                    max = option["max"]
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
                        self.logger.debug(
                            f"Connecting valueChanged signal for {option_keyword}"
                        )
                        # スライダーの値変更を監視
                        slider.valueChanged.connect(
                            lambda v, k=option_keyword: self.on_value_changed(k, v)
                        )
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
                        self.logger.debug(
                            f"Connecting valueChanged signal for {option_keyword}"
                        )
                        # スライダーの値変更を監視
                        slider.valueChanged.connect(
                            lambda v, k=option_keyword: self.on_value_changed(k, v)
                        )
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
                    self.logger.debug(
                        f"Connecting stateChanged signal for {option_keyword}"
                    )
                    checkbox.stateChanged.connect(
                        lambda state, k=option_keyword: self.on_value_changed(k, state)
                    )
                    tab_layout.addWidget(checkbox)
                    self.getters[converter][option_keyword] = checkbox
                elif option["type"] == str:
                    hbox = QHBoxLayout()
                    label = QLabel(tr(option["help"]))
                    hbox.addWidget(label)
                    lineedit = QLineEdit(tr(option["default"]))
                    self.logger.debug(
                        f"Connecting textChanged signal for {option_keyword}"
                    )
                    lineedit.textChanged.connect(
                        lambda text, k=option_keyword: self.on_value_changed(k, text)
                    )
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
        self.logger.debug("Connecting buttonClicked signal for arrow group")
        self.arrow_group.buttonClicked.connect(
            lambda button: self.on_value_changed("direction", button)
        )

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

        # スタートボタンを追加
        self.start_button = QPushButton(tr("Start Conversion"))
        self.start_button.setEnabled(False)  # 初期状態は無効
        self.start_button.clicked.connect(self.start_process)
        finish_layout.addWidget(self.start_button)

        left_widget.setLayout(finish_layout)

        # 右側のプレビュー用ウィジェット
        right_widget = QWidget()
        preview_layout = QVBoxLayout()

        # プレビュー用のラベル
        self.preview_label = QLabel(tr("Preview"))
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(400, 400)  # 最小サイズを設定
        preview_layout.addWidget(self.preview_label)

        right_widget.setLayout(preview_layout)

        # スプリッターを作成して左右のウィジェットを配置
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 400])  # 初期サイズを設定

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
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
        img = image_loader(self.filename)
        file_name = self.filename

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
        elif tab == "movie":
            movie.make_movie(img, file_name + ".mp4", head_right=head_right, **args)

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
                    # ファイルパスを表示
                    self.file_path_label.setText(self.filename)
                    # スタートボタンを有効化
                    self.start_button.setEnabled(True)
                    # 画像を読み込んで保持
                    self.current_image = image_loader(self.filename, width=5000)
                    # 現在のタブのプレビューを更新
                    self.update_preview(
                        self.tab_widget.tabText(self.tab_widget.currentIndex())
                    )

    def on_tab_changed(self, index):
        """タブが切り替わった時に呼ばれる関数"""
        # 動画プレビューのタイマーを停止
        if self.movie_preview_timer is not None:
            self.movie_preview_timer.stop()
            self.movie_preview_timer = None
            self.movie_frames = None

        if self.current_image is None:
            return

        converter = self.tab_widget.tabText(index)
        self.update_preview(converter)

    def update_preview(self, converter):
        """プレビューを更新する関数"""
        self.logger.debug(f"update_preview called for {converter}")
        if self.current_image is None:
            self.logger.debug("No image loaded")
            return

        self.logger.debug(f"Current image shape: {self.current_image.shape}")
        # 現在の設定値を取得
        args = self.get_current_args(converter)
        head_right = self.btn_right.isChecked()

        # 各コンバーターに対応するプレビュー関数を呼び出す
        preview_func = getattr(self, f"preview_{converter}", None)
        self.logger.debug(f"preview_func: {preview_func} {converter} {args}")
        if preview_func:
            preview_func(self.current_image, head_right, args)

    def get_current_args(self, converter):
        """現在の設定値を取得する関数"""
        args = dict()
        for option_keyword, option in self.getters[converter].items():
            if isinstance(option, QValueSlider):
                args[option_keyword] = option.get_display_value()
            elif isinstance(option, QLineEdit):
                args[option_keyword] = option.text()
            elif isinstance(option, QCheckBox):
                args[option_keyword] = option.isChecked()
        return args

    def _create_slider_callback(self, key):
        """スライダーの値変更時のコールバック関数を作成"""

        def callback(value):
            self.logger.debug(f"Slider {key} value changed to: {value}")
            self.on_value_changed(key, value)

        return callback

    def on_value_changed(self, key, value):
        """GUI要素の値が変更された時に呼ばれる関数"""
        self.logger.debug(f"on_value_changed called with key: {key}, value: {value}")
        if self.current_image is None:
            return

        converter = self.tab_widget.tabText(self.tab_widget.currentIndex())
        self.logger.debug(f"Updating preview for converter: {converter}")
        self.update_preview(converter)

    # 以下は各コンバーターのプレビュー関数のテンプレート
    def preview_helix(self, img, head_right, args):
        """helixコンバーターのプレビュー"""
        # ここにプレビュー表示のコードを実装
        args["width"] = 300
        rectimg = helix.helicify(img, **args)
        self.preview_label.setPixmap(QPixmap.fromImage(cv2toQImage(rectimg)))

    def preview_movie(self, img, head_right, args):
        """movieコンバーターのプレビュー"""

        # 既存のタイマーを停止
        if self.movie_preview_timer is not None:
            self.movie_preview_timer.stop()
            self.movie_preview_timer = None

        preview_width = 300
        preview_height = preview_width * args["height"] // args["width"]

        # フレームイテレータを生成
        self.movie_frames = cycle(
            movie.movie_iter(
                img,
                head_right=head_right,
                duration=args["duration"],
                height=preview_height,  # プレビュー用のサイズ
                width=preview_width,
                fps=10,  # プレビュー用のフレームレート
                alternating=args["alternating"],
                accel=args["accel"],
                thumbnail=args["thumbnail"],
            )
        )

        # タイマーを作成して開始
        self.movie_preview_timer = QTimer(self)
        self.movie_preview_timer.timeout.connect(self._update_movie_preview)
        self.movie_preview_timer.start(100)  # 100msごとに更新

    def _update_movie_preview(self):
        """動画プレビューのフレームを更新"""
        try:
            frame = next(self.movie_frames)
            self.preview_label.setPixmap(QPixmap.fromImage(cv2toQImage(frame)))
        except StopIteration:
            # フレームが終了したら最初から再生
            self.movie_preview_timer.stop()
            self.movie_preview_timer = None
            # プレビューを再開
            self.update_preview(self.tab_widget.tabText(self.tab_widget.currentIndex()))

    def preview_rect(self, img, head_right, args):
        """rectコンバーターのプレビュー"""
        args["width"] = 300
        rectimg = rect.rectify(img, head_right=head_right, **args)
        self.preview_label.setPixmap(QPixmap.fromImage(cv2toQImage(rectimg)))


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
    path = os.path.dirname(trainscanner.__file__)
    logger.debug(f"Application path: {path}")

    # まずLANG環境変数を確認

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
