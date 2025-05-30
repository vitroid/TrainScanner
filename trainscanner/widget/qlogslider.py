# 実数を扱えるQSliderを作成する

from PyQt6.QtWidgets import QSlider, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from trainscanner.widget.qfloatslider import QFloatSlider, FloatSliderHandle
from math import log10


class LogSliderHandle(FloatSliderHandle):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _float_to_int(self, float_value):
        return int(
            round(
                (log10(float_value) - log10(self._float_min_value))
                / (log10(self._float_max_value) - log10(self._float_min_value))
                * self.resolution
            )
        )

    def _int_to_float(self, int_value):
        return 10 ** (
            log10(self._float_min_value)
            + (log10(self._float_max_value) - log10(self._float_min_value))
            * int_value
            / self.resolution
        )


# 動作確認用テスト関数
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
    import sys

    def test():
        app = QApplication(sys.argv)
        win = QWidget()
        layout = QVBoxLayout()
        slider = QFloatSlider(
            float_min_value=0.1,
            float_max_value=100,
            float_value=10,
            sliderhandleclass=LogSliderHandle,
        )
        label = QLabel(f"value: {slider.get_display_value():.2f}")

        def on_value_changed(val):
            label.setText(f"value: {val:.2f}")

        slider.valueChanged.connect(on_value_changed)
        layout.addWidget(slider)
        layout.addWidget(label)
        win.setLayout(layout)
        win.setWindowTitle("QLogSlider Test")
        win.show()
        ret = app.exec()
        # 最後に、sliderの値を表示
        print(slider.get_display_value())
        return ret

    test()
