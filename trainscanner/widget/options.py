import argparse
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QApplication,
    QGroupBox,
    QGridLayout,
)
from PyQt6.QtCore import Qt
from trainscanner.widget.qfloatslider import QFloatSlider
from trainscanner.widget.qvalueslider import QValueSlider
from trainscanner.widget.qlogslider import LogSliderHandle
import logging


def list_cli_options(parser: argparse.ArgumentParser):
    """
    コマンドラインオプションの一覧をリストで返すAPI

    Returns:
        list: 各オプションの情報を含む辞書のリスト
        [
            {
                "option_strings": ["--option", "-o"],  # オプション名
                "dest": "option_name",                # 変数名
                "help": "ヘルプテキスト",             # ヘルプメッセージ
                "required": True/False,               # 必須かどうか
                "nargs": None/1/2/.../"+"/"*",       # 引数の数
                "default": None/値,                   # デフォルト値
                "type": "str"/"int"/.../None,        # 型
            },
            ...
        ]
    """
    options = []
    for action in parser._actions:
        opt = {
            "option_strings": action.option_strings,
            "dest": action.dest,
            "help": action.help,
            "required": action.required,
            "nargs": action.nargs,
            "default": action.default,
            "type": action.type if action.type else None,
        }
        try:
            # ヘルプテキストからオプションの値の範囲を取得
            # specの解釈はここでは行わない。
            help, spec = opt["help"].split("--")
            opt["help"] = help
            opt["spec"] = spec
        except ValueError:
            pass
        options.append(opt)
    return options, parser.description


class OptionsControlWidget(QWidget):
    def __init__(
        self,
        parser: argparse.ArgumentParser,
        on_value_changed: callable = None,
        ignore_options: list[str] = ["help"],
        disable_options: list[str] = [],
        parent=None,
    ):
        super().__init__(parent)
        logger = logging.getLogger()
        options, description = list_cli_options(parser)

        main_layout = QVBoxLayout()
        gbox = QGroupBox(description)
        layout = QGridLayout()
        gbox.setLayout(layout)
        main_layout.addWidget(gbox)

        self.widgets = dict()

        # オプションの表示
        for row, option in enumerate(options):
            # オプションのキーワードを取得
            for option_keyword in option["option_strings"]:
                if option_keyword[:2] == "--":
                    option_keyword = option_keyword[2:]
                    break
            else:
                continue

            if option_keyword in ignore_options:
                continue

            if "spec" in option:
                help = option["help"]
                spec = option["spec"]
                if "|" in spec:
                    # "|"で仕切られた値の場合は、selectorを作成する。
                    items = [x.strip() for x in spec.split("|")]
                    # hbox = QHBoxLayout()
                    label = QLabel(help)
                    layout.addWidget(label, row, 0, Qt.AlignmentFlag.AlignRight)
                    selector = QComboBox()
                    for value in items:
                        selector.addItem(str(value))
                    if on_value_changed is not None:
                        selector.currentIndexChanged.connect(
                            lambda v, k=option_keyword: on_value_changed(k, items[v])
                        )
                    layout.addWidget(selector, row, 2, Qt.AlignmentFlag.AlignCenter)
                    self.widgets[option_keyword] = selector
                else:
                    assert ":" in spec, f"spec: {spec}"
                    assert option["type"] in (int, float)

                    min, max = [float(x) for x in spec.split(":")]
                    # hbox = QHBoxLayout()
                    label = QLabel(help)
                    layout.addWidget(label, row, 0, Qt.AlignmentFlag.AlignRight)
                    if option["type"] == int:
                        slider = QValueSlider()
                        slider.setMinimum(int(min))
                        slider.setMaximum(int(max))
                        if option["default"] is not None:
                            slider.setValue(int(option["default"]))
                        else:
                            slider.setValue(int(min))
                        logger.debug(
                            f"Connecting valueChanged signal for {option_keyword}"
                        )
                        if on_value_changed is not None:
                            slider.valueChanged.connect(
                                lambda v, k=option_keyword: on_value_changed(k, v)
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
                        logger.debug(
                            f"Connecting valueChanged signal for {option_keyword}"
                        )
                        if on_value_changed is not None:
                            slider.valueChanged.connect(
                                lambda v, k=option_keyword: on_value_changed(k, v)
                            )
                        min_label = QLabel(f"{min}")
                        max_label = QLabel(f"{max}")
                    hbox = QHBoxLayout()
                    hbox.addWidget(min_label)
                    hbox.addWidget(slider)
                    hbox.addWidget(max_label)
                    layout.addLayout(hbox, row, 2, Qt.AlignmentFlag.AlignCenter)
                    self.widgets[option_keyword] = slider
            elif option["type"] is None and option["nargs"] == 0:
                label = QLabel(option["help"])
                layout.addWidget(label, row, 0, Qt.AlignmentFlag.AlignRight)
                checkbox = QCheckBox()
                logger.debug(f"Connecting stateChanged signal for {option_keyword}")
                if on_value_changed is not None:
                    checkbox.stateChanged.connect(
                        lambda state, k=option_keyword: on_value_changed(k, state)
                    )
                layout.addWidget(checkbox, row, 1, Qt.AlignmentFlag.AlignCenter)
                self.widgets[option_keyword] = checkbox
            elif option["type"] == str:
                label = QLabel(option["help"])
                layout.addWidget(label, row, 0, Qt.AlignmentFlag.AlignRight)
                lineedit = QLineEdit(option["default"])
                logger.debug(f"Connecting textChanged signal for {option_keyword}")
                if on_value_changed is not None:
                    lineedit.textChanged.connect(
                        lambda text, k=option_keyword: on_value_changed(k, text)
                    )
                layout.addWidget(lineedit, row, 2, Qt.AlignmentFlag.AlignCenter)
                self.widgets[option_keyword] = lineedit
            if option_keyword in disable_options:
                self.widgets[option_keyword].setEnabled(False)
        self.setLayout(main_layout)

    def get_values(self):
        values = dict()
        for key, widget in self.widgets.items():
            if isinstance(widget, QLineEdit):
                values[key] = widget.text()
            elif isinstance(widget, QCheckBox):
                values[key] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                values[key] = widget.currentText()
            elif hasattr(widget, "get_display_value"):  # QValueSlider, QFloatSlider
                values[key] = widget.get_display_value()
            elif hasattr(widget, "value"):
                values[key] = widget.value()
            else:
                values[key] = None
        return values


if __name__ == "__main__":
    import trainscanner.converter.movie

    app = QApplication([])
    parser = trainscanner.converter.movie.get_parser()
    widget = OptionsControlWidget(parser, lambda k, v: print(k, v))
    widget.show()
    app.exec()

    values = widget.get_values()  # 各オプションの現在値が辞書で得られる
    print(values)
