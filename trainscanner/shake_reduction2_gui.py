import cv2
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap, QShortcut, QKeySequence
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
                color: #000000;
                font-size: 14px;
            }
            @media (prefers-color-scheme: dark) {
                QLabel {
                    border-color: #666;
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
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


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("操作方法")

        # メインの白背景Widget
        main_widget = QWidget(self)
        main_widget.setStyleSheet(
            """
            background: #fff;
            border-radius: 16px;
            border: 1px solid #ccc;
        """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(main_widget)

        # 内部レイアウト
        inner_layout = QVBoxLayout(main_widget)
        inner_layout.setContentsMargins(32, 32, 32, 24)
        inner_layout.setSpacing(16)

        # 説明テキスト
        help_text = """
        <h2 style='margin-top:0;'>操作方法</h2>
        <ol style='font-size:15px;'>
            <li>マウスの左ボタンをドラッグして、背景(列車にかぶらない場所)に長方形を描きます</li>
            <li>車体と距離が近い場所(線路など)で、平滑でない場所が望ましいです</li>
            <li>長方形1つを指定した場合は、その部分が固定されるように画像を平行移動します</li>
            <li>長方形2つを指定した場合は、長方形0が固定され、長方形1で回転も補正します</li>
            <li>Deleteキーで長方形を消去できます</li>
            <li>「処理開始」ボタンをクリックして補正を開始します。</li>
        </ol>
        """
        help_label = QLabel(help_text)
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color:#222;font-size:15px;")
        inner_layout.addWidget(help_label)

        # 閉じるボタン
        close_button = QPushButton("閉じる")
        close_button.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 32px;
                border-radius: 6px;
                font-size: 15px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """
        )
        close_button.clicked.connect(self.close)
        inner_layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.adjustSize()


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
        self.help_shown = False  # ヘルプ表示済みフラグ

        # ウィンドウの設定
        self.setWindowTitle("画像選択")
        self.setGeometry(100, 100, 400, 300)
        self.setAcceptDrops(True)  # ここでウィンドウ自体がDropを受け付ける

        # ドロップエリアの設定
        self.drop_area = DropArea(self)
        self.setCentralWidget(self.drop_area)

        # ショートカットの設定
        close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        close_shortcut.activated.connect(self.close)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.process_video(files[0])

    def process_video(self, video_path):
        # 状態リセット
        self.rectangles = []
        self.drawing = False
        self.start_point = None
        self.current_image = None
        self.original_image = None
        self.video_path = None

        self.video_path = video_path
        video_frames = video_iter(video_path)
        frame = next(video_frames)

        # 中央ウィジェットとレイアウトの設定
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 画像表示用のラベル
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)

        # スタートボタンの追加
        self.start_button = QPushButton("処理開始")
        self.start_button.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            @media (prefers-color-scheme: dark) {
                QPushButton {
                    background-color: #45a049;
                }
                QPushButton:hover {
                    background-color: #3d8b40;
                }
                QPushButton:pressed {
                    background-color: #357935;
                }
            }
        """
        )
        self.start_button.clicked.connect(self.start_processing)
        layout.addWidget(self.start_button)

        self.original_image = frame.copy()
        self.current_image = frame.copy()
        self.display_image()
        # ヘルプは最初の1回だけ表示
        if not self.help_shown:
            help_overlay = HelpDialog(self)
            help_overlay.exec()
            self.help_shown = True

    def start_processing(self):
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
                    # 画像を保存
                    outfilename = f"{self.video_path}.dir/{i:06d}.png"
                    cv2.imwrite(outfilename, frame)

                    # 画像を表示（10フレームごと）
                    if i % 10 == 0:
                        self.current_image = frame.copy()
                        self.display_image()
                        QApplication.processEvents()  # GUIの更新を強制

            # print("処理完了")
            # 処理完了後、ドロップエリアに戻る
            self.current_image = None
            self.original_image = None
            self.rectangles = []
            self.video_path = None
            self.drop_area = DropArea(self)
            self.setCentralWidget(self.drop_area)
            # ウィンドウサイズを初期サイズに戻す
            self.resize(400, 300)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_image is not None:
            self.display_image()

    def get_image_coordinates(self, pos):
        # ラベルの位置を取得
        label_pos = self.image_label.mapFrom(self, pos)

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

        # 座標を画像の範囲内に制限
        x = max(0, min(x, self.original_image.shape[1] - 1))
        y = max(0, min(y, self.original_image.shape[0] - 1))
        return (x, y)

    def display_image(self):
        if self.current_image is None:
            return

        # 画像のアスペクト比を維持しながら、最大800pxにスケーリング
        image_height, image_width = self.current_image.shape[:2]
        max_size = 800

        # アスペクト比を計算
        if image_width > image_height:
            new_width = min(image_width, max_size)
            new_height = int(image_height * (new_width / image_width))
        else:
            new_height = min(image_height, max_size)
            new_width = int(image_width * (new_height / image_height))

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

        # ウィンドウサイズを調整（画像サイズ + 余白 + ボタンの高さ）
        window_width = new_width + 40  # 左右の余白
        window_height = new_height + 100  # 上下の余白 + ボタンの高さ
        self.resize(window_width, window_height)

    def mousePressEvent(self, event):
        if self.original_image is None:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            pos = self.get_image_coordinates(event.pos())
            if pos is not None:
                self.drawing = True
                self.start_point = pos

    def mouseMoveEvent(self, event):
        if self.original_image is None:
            return
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
                    ((rect[1][0] + rect[0][0]) // 2, (rect[1][1] + rect[0][1]) // 2),
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
        if self.original_image is None:
            return
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
                        (
                            (rect[1][0] + rect[0][0]) // 2,
                            (rect[1][1] + rect[0][1]) // 2,
                        ),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        2,  # scale
                        self.colors[i],
                        2,  # thickness
                    )
                self.current_image = display_image
                self.display_image()

    def get_rectangles(self):
        return self.rectangles

    def keyPressEvent(self, event):
        if self.original_image is None:
            return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            # 長方形を全て消去
            self.rectangles = []
            # 画像を更新
            self.current_image = self.original_image.copy()
            self.display_image()

    def closeEvent(self, event):
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
