# 実数を扱えるQSliderを作成する

from PyQt6.QtWidgets import QSlider, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from trainscanner.widget.qfloatslider import QFloatSlider
from math import log10


class QLogSlider(QFloatSlider):
    valueChanged = pyqtSignal(float)  # 実数値の変更を通知するシグナル

    def __init__(
        self, min_value=0.1, max_value=100, resolution=100, value=1.0, **kwargs
    ):
        super().__init__(
            min_value=min_value, max_value=max_value, resolution=resolution, value=value
        )

    def _float_to_int(self, float_value):
        """実数値を整数値に変換"""
        return int(
            (log10(float_value) - log10(self.min_value))
            / (log10(self.max_value) - log10(self.min_value))
            * self.resolution
        )

    def _int_to_float(self, int_value):
        """整数値を実数値に変換"""
        return 10 ** (
            log10(self.min_value)
            + (log10(self.max_value) - log10(self.min_value))
            * int_value
            / self.resolution
        )
