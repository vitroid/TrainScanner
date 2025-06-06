import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QWidget,
    QScrollArea,
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QImage, QPixmap
from trainscanner.video import VideoLoader
from trainscanner.shake_reduction2 import antishake
import sys
import os


def video_iter(filename: str):
    video_loader = VideoLoader(filename)
    while True:
        frame_index, frame = video_loader.next()
        if frame_index == 0:
            break
        yield frame


class DropArea(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("ここに動画ファイルをDrag & Dropして下さい")
        self.setStyleSheet(
            """
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 5px;
                padding: 20px;
                background-color: #f0f0f0;
                font-size: 14px;
            }
        """
        )
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.parent().process_video(files[0])


class ImageWindow(QMainWindow):
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]

    def __init__(self):
        super().__init__()
        self.rectangles = []
        self.drawing = False
        self.start_point = None
        self.current_image = None
        self.original_image = None
        self.video_path = None

        # ウィンドウの設定
        self.setWindowTitle("画像選択")
        self.setGeometry(100, 100, 1200, 800)

        # ドロップエリアの設定
        self.drop_area = DropArea(self)
        self.setCentralWidget(self.drop_area)

    def process_video(self, video_path):
        self.video_path = video_path
        video_frames = video_iter(video_path)
        frame = next(video_frames)

        # スクロールエリアの設定
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.setCentralWidget(self.scroll_area)

        # 中央ウィジェットとレイアウトの設定
        central_widget = QWidget()
        self.scroll_area.setWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 画像表示用のラベル
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)

        self.original_image = frame.copy()
        self.current_image = frame.copy()
        self.display_image()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_image is not None:
            self.display_image()

    def get_image_coordinates(self, pos):
        # スクロールエリア内の相対位置を計算
        scroll_pos = self.scroll_area.mapFrom(self, pos)
        label_pos = self.image_label.mapFrom(self.scroll_area, scroll_pos)

        # ラベルのサイズと位置を取得
        label_rect = self.image_label.geometry()
        pixmap = self.image_label.pixmap()
        if pixmap is None:
            return None

        # 画像の実際の表示サイズと位置を計算
        scaled_size = pixmap.size()
        x_offset = (label_rect.width() - scaled_size.width()) // 2
        y_offset = (label_rect.height() - scaled_size.height()) // 2

        # マウス座標を画像座標に変換
        x = int(
            (label_pos.x() - x_offset)
            * self.original_image.shape[1]
            / scaled_size.width()
        )
        y = int(
            (label_pos.y() - y_offset)
            * self.original_image.shape[0]
            / scaled_size.height()
        )

        # 座標が画像の範囲内かチェック
        if (
            0 <= x < self.original_image.shape[1]
            and 0 <= y < self.original_image.shape[0]
        ):
            return (x, y)
        return None

    def display_image(self):
        if self.current_image is None:
            return

        # ウィンドウのサイズを取得
        window_size = self.size()
        label_size = self.image_label.size()

        # 画像のアスペクト比を維持しながら、ウィンドウに合わせてスケーリング
        image_height, image_width = self.current_image.shape[:2]
        window_ratio = label_size.width() / label_size.height()
        image_ratio = image_width / image_height

        # 最大表示サイズを設定（4K画像でも適切に表示）
        max_width = min(label_size.width(), 3840)
        max_height = min(label_size.height(), 2160)

        if window_ratio > image_ratio:
            # ウィンドウが横長の場合
            new_height = min(max_height, int(max_width / image_ratio))
            new_width = int(new_height * image_ratio)
        else:
            # ウィンドウが縦長の場合
            new_width = min(max_width, int(max_height * image_ratio))
            new_height = int(new_width / image_ratio)

        # OpenCVの画像をQtで表示可能な形式に変換
        bytes_per_line = 3 * image_width
        q_image = QImage(
            self.current_image.data,
            image_width,
            image_height,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        ).rgbSwapped()

        # 画像をスケーリング
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(
            new_width,
            new_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled_pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = self.get_image_coordinates(event.pos())
            if pos is not None:
                self.drawing = True
                self.start_point = pos

    def mouseMoveEvent(self, event):
        if self.drawing:
            # 元の画像をコピー
            display_image = self.original_image.copy()

            # 既存の長方形を描画
            for i, rect in enumerate(self.rectangles):
                cv2.rectangle(display_image, rect[0], rect[1], self.colors[i], 2)
                # 番号を描画
                cv2.putText(
                    display_image,
                    str(i),
                    (rect[1][0] - 20, rect[0][1] + 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    2,
                    self.colors[i],
                    2,
                )

            # 現在描画中の長方形を描画
            end_pos = self.get_image_coordinates(event.pos())
            if end_pos is not None:
                cv2.rectangle(
                    display_image, self.start_point, end_pos, (255, 255, 0), 1
                )

            # 画像を更新
            self.current_image = display_image
            self.display_image()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.drawing:
            self.drawing = False
            end_pos = self.get_image_coordinates(event.pos())

            if end_pos is not None:
                # 長方形の座標を追加
                self.rectangles.append((self.start_point, end_pos))

                # 3個以上の長方形がある場合、最初のものを削除
                if len(self.rectangles) > 2:
                    self.rectangles.pop(0)

                # 画像を更新
                display_image = self.original_image.copy()
                for i, rect in enumerate(self.rectangles):
                    cv2.rectangle(display_image, rect[0], rect[1], self.colors[i], 2)
                    # 番号を描画
                    cv2.putText(
                        display_image,
                        str(i),
                        (rect[1][0] - 20, rect[0][1] + 20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        2,  # scale
                        self.colors[i],
                        2,  # thickness
                    )
                self.current_image = display_image
                self.display_image()

    def get_rectangles(self):
        return self.rectangles

    def closeEvent(self, event):
        if self.video_path and self.rectangles:
            # ビデオをまきもどす
            video_frames = video_iter(self.video_path)
            rects = self.get_rectangles()
            rects = qt_to_cv(rects)
            os.makedirs(f"{self.video_path}.dir", exist_ok=True)
            with open(f"{self.video_path}.dir/log.txt", "w") as logfile:
                for i, frame in enumerate(
                    antishake(video_frames, rects, logfile=logfile)
                ):
                    outfilename = f"{self.video_path}.dir/{i:06d}.png"
                    print(outfilename)
                    cv2.imwrite(outfilename, frame)
        event.accept()


def qt_to_cv(rects):
    cv_rects = []
    for rect in rects:
        left = min(rect[0][0], rect[1][0])
        right = max(rect[0][0], rect[1][0])
        top = min(rect[0][1], rect[1][1])
        bottom = max(rect[0][1], rect[1][1])
        cv_rects.append((left, top, right - left, bottom - top))
    return cv_rects


def main():
    app = QApplication(sys.argv)
    window = ImageWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
