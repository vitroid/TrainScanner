#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
tsposファイルをドラッグ&ドロップしてプロットするツール
"""

import sys
import os
from pathlib import Path
import numpy as np

# GUIバックエンドを事前に設定
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = ''

import matplotlib
matplotlib.use("QtAgg")  # PyQt6用のバックエンドを設定
import matplotlib.pyplot as plt

# matplotlibの設定を早期に初期化
plt.ioff()  # インタラクティブモードをオフ

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QLabel,
    QFileDialog,
    QMessageBox,
    QCheckBox,
    QGroupBox,
    QGridLayout,
    QSpinBox,
    QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent
from logging import getLogger


class TsposPlotter(QWidget):
    """tsposファイルをプロットするウィジェット"""

    def __init__(self):
        super().__init__()
        self.data = None
        self.file_path = None
        self.init_ui()

    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout()

        # ファイル選択エリア
        file_area = self.create_file_area()
        layout.addWidget(file_area)

        # プロット設定エリア
        settings_area = self.create_settings_area()
        layout.addWidget(settings_area)

        # プロットエリア
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # ボタンエリア
        button_area = self.create_button_area()
        layout.addWidget(button_area)

        self.setLayout(layout)

    def create_file_area(self):
        """ファイル選択エリアを作成"""
        group = QGroupBox("ファイル選択")
        layout = QVBoxLayout()

        # ドラッグ&ドロップエリア
        self.drop_label = QLabel(
            "tsposファイルをここにドラッグ&ドロップするか、\n「ファイルを開く」ボタンをクリックしてください"
        )
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setStyleSheet(
            """
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                padding: 20px;
                background-color: #f9f9f9;
                color: #666;
                font-size: 14px;
            }
        """
        )
        self.drop_label.setAcceptDrops(True)
        self.drop_label.dragEnterEvent = self.drag_enter_event
        self.drop_label.dropEvent = self.drop_event
        layout.addWidget(self.drop_label)

        # ファイル選択ボタンとファイル名表示
        file_layout = QHBoxLayout()
        self.open_button = QPushButton("ファイルを開く")
        self.open_button.clicked.connect(self.open_file)
        file_layout.addWidget(self.open_button)

        self.file_label = QLabel("ファイルが選択されていません")
        self.file_label.setStyleSheet("color: #666;")
        file_layout.addWidget(self.file_label)
        file_layout.addStretch()

        layout.addLayout(file_layout)
        group.setLayout(layout)
        return group

    def create_settings_area(self):
        """プロット設定エリアを作成"""
        group = QGroupBox("プロット設定")
        layout = QGridLayout()

        # X軸の設定
        layout.addWidget(QLabel("X軸:"), 0, 0)
        self.x_combo = QComboBox()
        self.x_combo.addItems(["フレーム番号 (第1カラム)", "時間 (フレーム番号/30fps)"])
        layout.addWidget(self.x_combo, 0, 1)

        # Y軸の設定
        layout.addWidget(QLabel("Y軸:"), 1, 0)
        self.y_dx_check = QCheckBox("X方向変位 (第2カラム)")
        self.y_dx_check.setChecked(True)
        layout.addWidget(self.y_dx_check, 1, 1)

        self.y_dy_check = QCheckBox("Y方向変位 (第3カラム)")
        self.y_dy_check.setChecked(True)
        layout.addWidget(self.y_dy_check, 1, 2)

        # 累積変位の表示
        self.cumsum_check = QCheckBox("累積変位を表示")
        self.cumsum_check.setChecked(True)
        layout.addWidget(self.cumsum_check, 2, 1)

        # フレーム間隔の設定
        layout.addWidget(QLabel("フレーム間隔:"), 3, 0)
        self.frame_interval_spin = QSpinBox()
        self.frame_interval_spin.setMinimum(1)
        self.frame_interval_spin.setMaximum(100)
        self.frame_interval_spin.setValue(1)
        self.frame_interval_spin.setSuffix(" フレーム")
        layout.addWidget(self.frame_interval_spin, 3, 1)

        group.setLayout(layout)
        return group

    def create_button_area(self):
        """ボタンエリアを作成"""
        layout = QHBoxLayout()

        self.plot_button = QPushButton("プロット")
        self.plot_button.clicked.connect(self.plot_data)
        self.plot_button.setEnabled(False)
        layout.addWidget(self.plot_button)

        self.save_button = QPushButton("画像として保存")
        self.save_button.clicked.connect(self.save_plot)
        self.save_button.setEnabled(False)
        layout.addWidget(self.save_button)

        layout.addStretch()

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.stats_label)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def drag_enter_event(self, event: QDragEnterEvent):
        """ドラッグエンターイベント"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def drop_event(self, event: QDropEvent):
        """ドロップイベント"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.load_file(files[0])

    def open_file(self):
        """ファイルを開く"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "tsposファイルを選択", "", "tspos files (*.tspos);;All files (*)"
        )
        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path: str):
        """ファイルを読み込む"""
        try:
            self.file_path = file_path
            self.data = np.loadtxt(file_path)

            if self.data.shape[1] < 3:
                raise ValueError("tsposファイルには最低3列のデータが必要です")

            # UIを更新
            self.file_label.setText(f"ファイル: {Path(file_path).name}")
            self.file_label.setStyleSheet("color: #000;")
            self.drop_label.setText(
                f"✓ {Path(file_path).name} が読み込まれました\n({len(self.data)}行のデータ)"
            )
            self.drop_label.setStyleSheet(
                """
                QLabel {
                    border: 2px solid #4CAF50;
                    border-radius: 10px;
                    padding: 20px;
                    background-color: #e8f5e8;
                    color: #2e7d2e;
                    font-size: 14px;
                }
            """
            )

            self.plot_button.setEnabled(True)
            self.update_stats()

            # 自動的にプロット
            self.plot_data()

        except Exception as e:
            QMessageBox.critical(
                self, "エラー", f"ファイルの読み込みに失敗しました:\n{str(e)}"
            )
            getLogger().error(f"ファイル読み込みエラー: {e}")

    def update_stats(self):
        """統計情報を更新"""
        if self.data is None:
            return

        frame_count = len(self.data)
        dx_total = np.sum(np.abs(self.data[:, 1]))
        dy_total = np.sum(np.abs(self.data[:, 2]))

        stats_text = f"フレーム数: {frame_count}, X変位合計: {dx_total:.1f}px, Y変位合計: {dy_total:.1f}px"
        self.stats_label.setText(stats_text)

    def plot_data(self):
        """データをプロット"""
        if self.data is None:
            return

        try:
            self.figure.clear()

            # X軸データの準備
            if self.x_combo.currentIndex() == 0:
                x_data = self.data[:, 0]  # フレーム番号
                x_label = "フレーム番号"
            else:
                x_data = self.data[:, 0] / 30.0  # 時間（30fpsと仮定）
                x_label = "時間 (秒)"

            # フレーム間隔による間引き
            interval = self.frame_interval_spin.value()
            if interval > 1:
                indices = np.arange(0, len(self.data), interval)
                x_data = x_data[indices]
                plot_data = self.data[indices]
            else:
                plot_data = self.data

            # プロットの作成
            if self.cumsum_check.isChecked():
                # 累積変位をプロット
                ax = self.figure.add_subplot(111)

                if self.y_dx_check.isChecked():
                    cumsum_x = np.cumsum(plot_data[:, 1])
                    ax.plot(x_data, cumsum_x, "b-", label="X方向累積変位", linewidth=2)

                if self.y_dy_check.isChecked():
                    cumsum_y = np.cumsum(plot_data[:, 2])
                    ax.plot(x_data, cumsum_y, "r-", label="Y方向累積変位", linewidth=2)

                ax.set_ylabel("累積変位 (ピクセル)")
                ax.set_title("tspos累積変位プロット")

            else:
                # フレーム間変位をプロット
                if self.y_dx_check.isChecked() and self.y_dy_check.isChecked():
                    # 2つのサブプロット
                    ax1 = self.figure.add_subplot(211)
                    ax1.plot(x_data, plot_data[:, 1], "b-", linewidth=1)
                    ax1.set_ylabel("X方向変位 (ピクセル)")
                    ax1.set_title("tspos変位プロット")
                    ax1.grid(True, alpha=0.3)

                    ax2 = self.figure.add_subplot(212)
                    ax2.plot(x_data, plot_data[:, 2], "r-", linewidth=1)
                    ax2.set_ylabel("Y方向変位 (ピクセル)")
                    ax2.set_xlabel(x_label)
                    ax2.grid(True, alpha=0.3)

                else:
                    # 1つのプロット
                    ax = self.figure.add_subplot(111)

                    if self.y_dx_check.isChecked():
                        ax.plot(
                            x_data,
                            plot_data[:, 1],
                            "b-",
                            label="X方向変位",
                            linewidth=2,
                        )

                    if self.y_dy_check.isChecked():
                        ax.plot(
                            x_data,
                            plot_data[:, 2],
                            "r-",
                            label="Y方向変位",
                            linewidth=2,
                        )

                    ax.set_ylabel("変位 (ピクセル)")
                    ax.set_title("tspos変位プロット")

            # 共通の設定
            if "ax" in locals():
                ax.set_xlabel(x_label)
                ax.grid(True, alpha=0.3)
                if len(ax.get_legend_handles_labels()[0]) > 0:
                    ax.legend()

            self.figure.tight_layout()
            self.canvas.draw()

            self.save_button.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(
                self, "エラー", f"プロットの作成に失敗しました:\n{str(e)}"
            )
            getLogger().error(f"プロットエラー: {e}")

    def save_plot(self):
        """プロットを画像として保存"""
        if self.file_path is None:
            return

        default_name = Path(self.file_path).stem + "_plot.png"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "プロットを保存",
            default_name,
            "PNG files (*.png);;PDF files (*.pdf);;SVG files (*.svg);;All files (*)",
        )

        if file_path:
            try:
                self.figure.savefig(file_path, dpi=300, bbox_inches="tight")
                QMessageBox.information(
                    self, "保存完了", f"プロットを保存しました:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"保存に失敗しました:\n{str(e)}")


class TsposPlotterWindow(QMainWindow):
    """tsposプロッターのメインウィンドウ"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """UIを初期化"""
        self.setWindowTitle("TrainScanner tspos プロッター")
        self.setGeometry(100, 100, 1000, 800)

        # メインウィジェット
        self.plotter = TsposPlotter()
        self.setCentralWidget(self.plotter)

        # ドラッグ&ドロップを有効にする
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """ドラッグエンターイベント"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """ドロップイベント"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.plotter.load_file(files[0])


def main():
    """メイン関数"""
    app = QApplication(sys.argv)
    app.setApplicationName("TrainScanner tspos プロッター")

    # 日本語フォントの設定
    try:
        plt.rcParams["font.family"] = [
            "DejaVu Sans",
            "Hiragino Sans",
            "Yu Gothic",
            "Meiryo",
            "Takao",
            "IPAexGothic",
            "IPAPGothic",
            "VL PGothic",
            "Noto Sans CJK JP",
        ]
    except:
        pass

    window = TsposPlotterWindow()
    window.show()

    # コマンドライン引数でファイルが指定された場合
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            window.plotter.load_file(file_path)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
