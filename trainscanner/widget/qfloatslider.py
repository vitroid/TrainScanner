# 実数を扱えるQSliderを作成する

from PyQt6.QtCore import pyqtSignal
from .qvalueslider import QValueSlider


class QFloatSlider(QValueSlider):
    valueChanged = pyqtSignal(float)  # 実数値の変更を通知するシグナル

    def __init__(
        self,
        min_value=0.0,
        max_value=1.0,
        resolution=100,
        value=0.0,
        label_format="{:.2f}",
        **kwargs
    ):
        self.min_value = min_value
        self.max_value = max_value
        self.resolution = resolution
        int_value = QFloatSlider._float_to_int(self, value)
        super().__init__(
            min_value=0,
            max_value=resolution,
            value=int_value,
            label_format=label_format,
            **kwargs
        )
        self.slider.valueChanged.disconnect()
        self.slider.valueChanged.connect(self._on_int_value_changed)
        self.setValue(value)

    def _float_to_int(self, float_value):
        """実数値を整数値に変換"""
        return int(
            round(
                (float_value - self.min_value)
                / (self.max_value - self.min_value)
                * self.resolution
            )
        )

    def _int_to_float(self, int_value):
        """整数値を実数値に変換"""
        return (
            self.min_value
            + (self.max_value - self.min_value) * int_value / self.resolution
        )

    def _on_int_value_changed(self, int_value):
        """スライダーの値が変更された時の処理"""
        float_value = self._int_to_float(int_value)
        # ラベルをfloatで再表示
        self.setLabelFormat(self.slider.label_format)
        self.valueChanged.emit(float_value)

    def value(self):
        """現在の実数値を取得"""
        return self._int_to_float(self.slider.value())

    def setValue(self, float_value):
        """実数値を設定"""
        int_value = self._float_to_int(float_value)
        self.slider.setValue(int_value)

    def setMinimum(self, min_value):
        """最小値を設定"""
        self.min_value = min_value
        self.setValue(self.value())  # 現在の値を再設定

    def setMaximum(self, max_value):
        """最大値を設定"""
        self.max_value = max_value
        self.setValue(self.value())  # 現在の値を再設定

    def setResolution(self, resolution):
        """分解能を設定"""
        self.resolution = resolution
        self.slider.setMaximum(resolution)
        self.setValue(self.value())  # 現在の値を再設定
