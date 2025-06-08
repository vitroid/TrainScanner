# 実数を扱えるQSliderを作成する

from PyQt6.QtCore import (
    pyqtSignal,
    Qt,
    QSize,
    QRectF,
)
from .qvalueslider import QValueSlider, ValueSliderHandle
from PyQt6.QtWidgets import (
    QSlider,
    QWidget,
    QHBoxLayout,
    QLabel,
    QStyle,
    QStyleOptionSlider,
)
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QPainterPath


class FloatSliderHandle(ValueSliderHandle):
    def __init__(
        self,
        float_min_value=0.0,
        float_max_value=100.0,
        float_value=0.0,
        label_format="{:.2f}",
        **kwargs,
    ):
        self._float_min_value = float_min_value
        self._float_max_value = float_max_value
        self.resolution = 100
        super().__init__(
            min_value=0,
            max_value=self.resolution,
            value=self._float_to_int(float_value),
            label_format=label_format,
            **kwargs,
        )

    def get_display_value(self):
        return self._int_to_float(self.value())

    def _float_to_int(self, float_value):
        return int(
            round(
                (float_value - self._float_min_value)
                / (self._float_max_value - self._float_min_value)
                * self.resolution
            )
        )

    def _int_to_float(self, int_value):
        return (
            self._float_min_value
            + (self._float_max_value - self._float_min_value)
            * int_value
            / self.resolution
        )


class QFloatSlider(QValueSlider):
    valueChanged = pyqtSignal(float)  # 実数値の変更を通知するシグナル

    def __init__(
        self,
        float_min_value=0.0,
        float_max_value=100.0,
        float_value=1.0,
        sliderhandleclass=FloatSliderHandle,
        **kwargs,
    ):
        self._float_min_value = float_min_value
        self._float_max_value = float_max_value
        self.resolution = 100
        super().__init__(
            min_value=0,
            max_value=self.resolution,
            value=int(
                (float_value - float_min_value)
                / (float_max_value - float_min_value)
                * self.resolution
            ),
            **kwargs,
        )
        # スライダーをFloatSliderHandleに置き換え
        self.slider = sliderhandleclass(
            float_min_value=float_min_value,
            float_max_value=float_max_value,
            float_value=float_value,
            **kwargs,
        )
        self.slider.valueChanged.connect(self._on_slider_value_changed)
        self.layout().replaceWidget(self.layout().itemAt(0).widget(), self.slider)

    def _on_slider_value_changed(self, value):
        """スライダーの値が変更された時の処理"""
        float_value = self.slider._int_to_float(value)
        self.valueChanged.emit(float_value)

    def get_display_value(self):
        """現在の値を取得"""
        return self.slider.get_display_value()

    def setValue(self, value):
        """値を設定"""
        self.slider.setValue(self.slider._float_to_int(value))

    def setMinimum(self, value):
        """最小値を設定"""
        self._float_min_value = value
        self.setValue(self.get_display_value())  # 現在の値を再設定

    def setMaximum(self, value):
        """最大値を設定"""
        self._float_max_value = value
        self.setValue(self.get_display_value())  # 現在の値を再設定

    def setLabelFormat(self, format_str):
        """ラベルの表示フォーマットを設定"""
        self.slider.label_format = format_str
        self.slider.update()  # 再描画

    def setEnabled(self, enabled):
        """有効/無効を設定"""
        super().setEnabled(enabled)
        self.slider.setEnabled(enabled)


# 動作確認用テスト関数
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
    import sys

    def test():
        app = QApplication(sys.argv)
        win = QWidget()
        layout = QVBoxLayout()
        slider = QFloatSlider(
            float_min_value=3.0,
            float_max_value=7.0,
            float_value=4.0,
            label_format="{:.2f}",
        )
        label = QLabel(f"value: {slider.get_display_value():.2f}")

        def on_value_changed(val):
            label.setText(f"value: {val:.2f}")

        slider.valueChanged.connect(on_value_changed)
        layout.addWidget(slider)
        layout.addWidget(label)
        win.setLayout(layout)
        win.setWindowTitle("QFloatSlider Test")
        win.show()
        ret = app.exec()
        # 最後に、sliderの値を表示
        print(slider.get_display_value())
        return ret

    test()
