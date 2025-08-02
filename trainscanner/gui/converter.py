#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Core of the GUI and image process
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QApplication,
    QPushButton,
    QTabWidget,
    QLabel,
    QButtonGroup,
    QSplitter,
    QFileDialog,
    QProgressBar,
    QShortcut,
)
from PyQt5.QtGui import QKeySequence, QPixmap
from PyQt5.QtCore import Qt, QTimer
import cv2
import logging
import importlib

# File handling
import os
import shutil
from itertools import cycle

# final image tranformation
import trainscanner
from tiledimage.cachedimage import CachedImage
from trainscanner.i18n import tr

# options handler
import sys

from concurrent.futures import ThreadPoolExecutor
from trainscanner.widget import cv2toQImage
from trainscanner.widget.options import OptionsControlWidget

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


def get_converters():
    # trainscanner.converter配下のモジュールを自動で読み込む
    converters = dict()

    # 1. 組み込みのコンバーターを読み込む
    import trainscanner.converter

    for _, module_name, is_pkg in pkgutil.iter_modules(trainscanner.converter.__path__):
        if not is_pkg:  # パッケージではなくモジュールの場合のみ
            module = importlib.import_module(f"trainscanner.converter.{module_name}")
            converters[module_name] = module

    # 2. エントリーポイントを通じて登録されたコンバーターを読み込む
    try:
        from importlib import metadata

        for entry_point in metadata.entry_points().select(
            group="trainscanner.converters"
        ):
            try:
                # モジュールパスを取得（最後の:以降を除く）
                module_path = entry_point.value.split(":")[0]
                # モジュールを直接読み込む
                module = importlib.import_module(module_path)
                converters[entry_point.name] = module
            except Exception as e:
                logging.getLogger(__name__).warning(
                    f"Failed to load converter {entry_point.name}: {str(e)}"
                )
    except ImportError:
        # importlib.metadataが利用できない場合はスキップ
        pass

    return converters


# https://www.tutorialspoint.com/pyqt/pyqt_qfiledialog_widget.htm
class SettingsGUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.current_image = None  # 現在の画像を保持
        self.logger = logging.getLogger(__name__)  # クラス固有のロガーを作成
        self.movie_preview_timer = None  # 動画プレビュー用のタイマー
        self.movie_frames = None  # 動画フレームのイテレータ

        # メインレイアウト
        main_layout = QVBoxLayout()

        # ファイル選択ボタンとラベルのレイアウト
        file_layout = QHBoxLayout()
        self.btn = QPushButton(tr("Open a movie"))
        self.btn.clicked.connect(self.getfile)
        file_layout.addWidget(self.btn)

        self.le = QLabel(tr("(File name appears here)"))
        file_layout.addWidget(self.le)
        main_layout.addLayout(file_layout)

        # タブウィジェットの作成
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # 左側の設定用ウィジェット
        left_widget = QWidget()
        finish_layout = QVBoxLayout()

        # # ファイルパス表示用のラベルを追加
        # self.file_path_label = QLabel(tr("No file selected"))
        # self.file_path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # finish_layout.addWidget(self.file_path_label)

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

        self.has_ffmpeg = shutil.which("ffmpeg") is not None

        self.converters = get_converters()
        self.controlpanels = dict()

        for converter, module in self.converters.items():
            # module = contents["module"]
            if not self.has_ffmpeg:
                disable_options = ["crf", "encoder"]
            else:
                disable_options = []
            widget = OptionsControlWidget(
                module.get_parser(),
                on_value_changed=self.on_value_changed,
                ignore_options=["help", "head-right"],
                disable_options=disable_options,
            )
            self.controlpanels[converter] = widget
            self.tab_widget.addTab(widget, tr(converter))

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

        # プログレスバーを追加
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)  # 初期状態は非表示
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        finish_layout.addWidget(self.progress_bar)

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

        args = self.get_current_args(converter)

        # スタートボタンを無効化
        self.start_button.setEnabled(False)
        self.start_button.setText(tr("Converting..."))

        try:
            # 同期的に処理を実行
            self.process_image(converter, img, file_name, head_right, args)
            logger.info(f"Conversion completed: {file_name}")
        except Exception as e:
            logger.error(f"Conversion failed: {str(e)}")
        finally:
            # スタートボタンを再度有効化
            self.start_button.setEnabled(True)
            self.start_button.setText(tr("Start Conversion"))

    def process_image(self, tab, img, file_name, head_right, args):
        module = self.converters[tab]
        if hasattr(module, "convert"):
            rimg = module.convert(img, head_right=head_right, **args)
            cv2.imwrite(f"{file_name}.{tab}.png", rimg)
        elif hasattr(module, "make_movie"):
            # プログレスバーを表示
            self.show_progress(True)

            # 進捗コールバック関数を作成
            def progress_callback(progress):
                self.update_progress(progress)
                # GUIの更新を強制
                QApplication.processEvents()

            # make_movieに進捗コールバックを渡す
            module.make_movie(
                img,
                basename=file_name,
                head_right=head_right,
                progress_callback=progress_callback,
                **args,
            )

            # プログレスバーを非表示
            self.show_progress(False)
        else:
            raise ValueError(f"Converter {tab} has no convert method")

    def getfile(self):
        filename, types = QFileDialog.getOpenFileName(
            self,
            tr("Open a movie file"),
            "",
            "Movie files (*.mov *.mp4 *.m4v *.mts *.png *.jpg *.jpeg)",
        )
        if filename:
            self.filename = filename
            self.le.setText(filename)
            self.start_button.setEnabled(True)
            self.current_image = image_loader(filename)
            self.update_preview(self.tab_widget.tabText(self.tab_widget.currentIndex()))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.filename = files[0]
            self.le.setText(self.filename)
            self.start_button.setEnabled(True)
            self.current_image = image_loader(self.filename)
            self.update_preview(self.tab_widget.tabText(self.tab_widget.currentIndex()))

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

        # ffmpegがインストールされていない場合にmovieタブでの変換を防ぐ
        if converter == "movie" and not self.has_ffmpeg:
            self.start_button.setEnabled(False)
        else:
            self.start_button.setEnabled(True)

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
        self.preview(converter, self.current_image, head_right, args)

    def get_current_args(self, converter):
        """現在の設定値を取得する関数"""
        controlpanel = self.controlpanels[converter]
        values = controlpanel.get_values()
        return values

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

    def preview(self, tab, img, head_right, args):
        module = self.converters[tab]
        controlpanel = self.controlpanels[tab]
        args = controlpanel.get_values()
        if hasattr(module, "convert"):
            # image converter
            args["head_right"] = head_right
            args["width"] = 300
            rimg = module.convert(img, **args)
            self.preview_label.setPixmap(QPixmap.fromImage(cv2toQImage(rimg)))
        elif hasattr(module, "make_movie"):
            # movie converter

            # 既存のタイマーを停止
            if self.movie_preview_timer is not None:
                self.movie_preview_timer.stop()
                self.movie_preview_timer = None

            preview_width = 300
            if "height" in args:
                preview_height = preview_width * args["height"] // args["width"]
            else:
                preview_height = preview_width
            args["head_right"] = head_right
            args["width"] = preview_width
            args["height"] = preview_height
            args["fps"] = 10

            # フレームイテレータを生成
            self.movie_frames = cycle(
                module.movie_iter(
                    img,
                    **args,
                )
            )
            # タイマーを作成して開始
            self.movie_preview_timer = QTimer(self)
            self.movie_preview_timer.timeout.connect(self._update_movie_preview)
            self.movie_preview_timer.start(100)  # 100msごとに更新
        else:
            raise ValueError(f"Converter {tab} has no preview method")

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

    def show_progress(self, visible=True):
        """プログレスバーの表示/非表示を制御"""
        self.progress_bar.setVisible(visible)
        if not visible:
            self.progress_bar.setValue(0)

    def update_progress(self, value):
        """プログレスバーの値を更新"""
        self.progress_bar.setValue(value)

    def set_progress_range(self, minimum, maximum):
        """プログレスバーの範囲を設定"""
        self.progress_bar.setMinimum(minimum)
        self.progress_bar.setMaximum(maximum)


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
