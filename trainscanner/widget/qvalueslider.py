from PyQt6.QtWidgets import (
    QSlider,
    QWidget,
    QHBoxLayout,
    QLabel,
    QStyle,
    QStyleOptionSlider,
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QSize, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QPainterPath


class ValueSliderHandle(QSlider):
    valueChanged = pyqtSignal(int)  # 値の変更を通知するシグナル

    def __init__(
        self, min_value=0, max_value=100, value=0, label_format="{}", **kwargs
    ):
        super().__init__(Qt.Orientation.Horizontal)
        self.setMinimum(min_value)
        self.setMaximum(max_value)
        self.setValue(value)
        self.label_format = label_format

        # その他の設定
        for key, value in kwargs.items():
            setattr(self, key, value)

    def sizeHint(self):
        """推奨サイズを返す"""
        return QSize(100, 20)  # デフォルトのサイズ

    def paintEvent(self, event):
        """スライダーを描画"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # スライダーの基本部分を描画
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        opt.subControls = QStyle.SubControl.SC_SliderGroove
        self.style().drawComplexControl(
            QStyle.ComplexControl.CC_Slider, opt, painter, self
        )

        # 現在の値を取得
        value = self.value()
        text = self.label_format.format(value)

        # テキストのサイズを計算
        font = QFont()
        # font.setPointSize(8)
        painter.setFont(font)
        text_rect = painter.fontMetrics().boundingRect(text)

        # ハンドルのサイズを計算（テキストの幅 + 余白）
        handle_width = text_rect.width() + 20  # 左右に10pxずつ余白
        handle_height = 20  # 固定高さ

        # ハンドルの位置を計算
        slider_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider,
            opt,
            QStyle.SubControl.SC_SliderGroove,
            self,
        )

        # スライダーの位置に基づいてハンドルの位置を計算
        pos = self.style().sliderPositionFromValue(
            self.minimum(), self.maximum(), value, slider_rect.width()
        )

        # ハンドルの矩形を作成
        handle_rect = QRectF(
            pos - handle_width // 2,  # 中央揃え
            (self.height() - handle_height) // 2,
            handle_width,
            handle_height,
        )

        # 角丸長方形のパスを作成
        path = QPainterPath()
        radius = handle_height // 2  # 角の半径
        path.addRoundedRect(handle_rect, radius, radius)

        # ハンドルを描画
        if self.isEnabled():
            painter.fillPath(path, QColor(200, 200, 200))  # 薄いグレー
            painter.setPen(QPen(Qt.GlobalColor.black))
        else:
            painter.fillPath(path, QColor(240, 240, 240))  # より薄いグレー
            painter.setPen(QPen(Qt.GlobalColor.gray))

        # テキストを描画
        painter.drawText(handle_rect, Qt.AlignmentFlag.AlignCenter, text)


class QValueSlider(QWidget):
    valueChanged = pyqtSignal(int)  # 値の変更を通知するシグナル

    def __init__(
        self, min_value=0, max_value=100, value=0, label_format="{}", **kwargs
    ):
        super().__init__()

        # レイアウトの設定
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # マージンを0に設定
        self.setLayout(layout)

        # スライダーの作成
        self.slider = ValueSliderHandle(
            min_value=min_value,
            max_value=max_value,
            value=value,
            label_format=label_format,
            **kwargs
        )
        self.slider.valueChanged.connect(self._on_slider_value_changed)

        # ウィジェットをレイアウトに追加
        layout.addWidget(self.slider)

    def _on_slider_value_changed(self, value):
        """スライダーの値が変更された時の処理"""
        self.valueChanged.emit(value)

    def value(self):
        """現在の値を取得"""
        return self.slider.value()

    def setValue(self, value):
        """値を設定"""
        self.slider.setValue(value)

    def setMinimum(self, value):
        """最小値を設定"""
        self.slider.setMinimum(value)

    def setMaximum(self, value):
        """最大値を設定"""
        self.slider.setMaximum(value)

    def setLabelFormat(self, format_str):
        """ラベルの表示フォーマットを設定"""
        self.slider.label_format = format_str
        self.slider.update()  # 再描画

    def setEnabled(self, enabled):
        """有効/無効を設定"""
        super().setEnabled(enabled)
        self.slider.setEnabled(enabled)
