#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse

# File handling
import os
from dataclasses import dataclass

# options handler
import sys
import time
from logging import DEBUG, WARN, basicConfig, getLogger, root

# external modules
from PyQt6.QtCore import (
    QLocale,
    Qt,
    QTranslator,
)

# Core of the GUI and image process
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)
from PyQt6.QtGui import QImage, QPixmap, QPainter, QKeySequence, QShortcut

#
# sub dialog windows
# private modules
from trainscanner.gui import pass1, stitch
from trainscanner import trainscanner
from trainscanner.pass1 import prepare_parser as pp1
from trainscanner.stitch import prepare_parser as pp2
from trainscanner.gui.preprocess import EditorGUI
from trainscanner.i18n import tr


# https://www.tutorialspoint.com/pyqt/pyqt_qfiledialog_widget.htm
class SettingsGUI(QWidget):
    def __init__(self, parent=None):
        super(SettingsGUI, self).__init__(parent)
        self.setAcceptDrops(True)

        # ショートカットの設定
        close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        close_shortcut.activated.connect(self.close)

        # options
        self.trailing = 30
        self.editor = None
        self.antishake = 5
        self.estimate = 10
        self.slitwidth = 50
        self.identity = 0.5
        self.accel = 1

        # private
        # layout
        layout = QHBoxLayout()

        # leftmost panel for specifying options
        left_layout = QVBoxLayout()
        self.btn = QPushButton(tr("Open a movie"))
        self.btn.clicked.connect(self.getfile)
        left_layout.addWidget(self.btn)

        self.le = QLabel(tr("(File name appears here)"))
        # self.le = QLabel()
        left_layout.addWidget(self.le)

        # self.pbar = QProgressBar()
        # self.pbar.setValue(0)
        # left_layout.addWidget(self.pbar)

        # Left panel, upper pane: settings
        gbox_settings = QGroupBox(tr("Settings"))
        settings2_layout = QGridLayout()
        rows = 0
        # http://myenigma.hatenablog.com/entry/2016/01/24/113413

        # Example of a slider with a label ###################################
        # the slider is in a Hbox

        settings2_layout.addWidget(
            QLabel(tr("Slit mixing")), rows, 0, Qt.AlignmentFlag.AlignRight
        )

        self.slitwidth_slider_valuelabel = QLabel(f"{self.slitwidth}%")
        settings2_layout.addWidget(
            self.slitwidth_slider_valuelabel, rows, 1, Qt.AlignmentFlag.AlignCenter
        )

        settings2_layout.addWidget(
            QLabel(tr("Sharp")), rows, 2, Qt.AlignmentFlag.AlignRight
        )
        self.slitwidth_slider = QSlider(Qt.Orientation.Horizontal)  # スライダの向き
        self.slitwidth_slider.setRange(5, 300)  # スライダの範囲
        self.slitwidth_slider.setValue(self.slitwidth)  # 初期値
        self.slitwidth_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slitwidth_slider.valueChanged.connect(self.slitwidth_slider_on_draw)
        settings2_layout.addWidget(self.slitwidth_slider, rows, 3)
        settings2_layout.addWidget(QLabel(tr("Diffuse")), rows, 4)

        rows += 1
        #####################################################################

        # Example of a slider with a label ###################################
        # the slider is in a Hbox

        settings2_layout.addWidget(
            QLabel(tr("Minimal displacement between the frames")),
            rows,
            0,
            Qt.AlignmentFlag.AlignRight,
        )

        self.antishake_slider_valuelabel = QLabel(f"{self.antishake} " + tr("pixels"))
        settings2_layout.addWidget(
            self.antishake_slider_valuelabel, rows, 1, Qt.AlignmentFlag.AlignCenter
        )

        settings2_layout.addWidget(
            QLabel(tr("Small")), rows, 2, Qt.AlignmentFlag.AlignRight
        )
        self.antishake_slider = QSlider(Qt.Orientation.Horizontal)  # スライダの向き
        self.antishake_slider.setRange(0, 15)  # スライダの範囲
        self.antishake_slider.setValue(5)  # 初期値
        # スライダの目盛りを両方に出す
        self.antishake_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.antishake_slider.valueChanged.connect(self.antishake_slider_on_draw)
        settings2_layout.addWidget(self.antishake_slider, rows, 3)
        settings2_layout.addWidget(QLabel(tr("Large")), rows, 4)

        rows += 1
        #####################################################################

        # Example of a slider with a label ###################################
        # the slider is in a Hbox

        settings2_layout.addWidget(
            QLabel(tr("Number of frames to estimate the velocity")),
            rows,
            0,
            Qt.AlignmentFlag.AlignRight,
        )

        self.estimate_slider_valuelabel = QLabel(f"{self.estimate} " + tr("frames"))
        settings2_layout.addWidget(
            self.estimate_slider_valuelabel, rows, 1, Qt.AlignmentFlag.AlignCenter
        )

        settings2_layout.addWidget(
            QLabel(tr("Short")), rows, 2, Qt.AlignmentFlag.AlignRight
        )
        self.estimate_slider = QSlider(Qt.Orientation.Horizontal)  # スライダの向き
        self.estimate_slider.setRange(5, 50)  # スライダの範囲
        self.estimate_slider.setValue(10)  # 初期値
        # スライダの目盛りを両方に出す
        self.estimate_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.estimate_slider.valueChanged.connect(self.estimate_slider_on_draw)
        settings2_layout.addWidget(self.estimate_slider, rows, 3)
        settings2_layout.addWidget(QLabel(tr("Long")), rows, 4)

        rows += 1
        #####################################################################

        #####################################################################
        # Example of a checkbox
        settings2_layout.addWidget(
            QLabel(tr("Ignore vertical displacements")),
            rows,
            0,
            Qt.AlignmentFlag.AlignRight,
        )
        self.btn_zerodrift = QCheckBox()
        self.btn_zerodrift.setCheckState(Qt.CheckState.Checked)
        # self.b2.toggled.connect(lambda:self.btnstate(self.b2))
        settings2_layout.addWidget(
            self.btn_zerodrift, rows, 1, Qt.AlignmentFlag.AlignCenter
        )
        rows += 1
        #####################################################################

        #####################################################################
        # Example of a checkbox
        settings2_layout.addWidget(
            QLabel(tr("The train is initially stalling in the motion detection area.")),
            rows,
            0,
            Qt.AlignmentFlag.AlignRight,
        )
        self.btn_stall = QCheckBox()
        # self.btn_stall.setCheckState(Qt.CheckState.Checked)
        # self.b2.toggled.connect(lambda:self.btnstate(self.b2))
        settings2_layout.addWidget(
            self.btn_stall, rows, 1, Qt.AlignmentFlag.AlignCenter
        )
        rows += 1
        #####################################################################

        # #####################################################################
        # #Example of a checkbox
        settings2_layout.addWidget(
            QLabel(tr("Max acceleration")), rows, 0, Qt.AlignmentFlag.AlignRight
        )
        # self.btn_accel = QCheckBox()
        # self.btn_accel.setCheckState(Qt.CheckState.Checked)
        # settings2_layout.addWidget(self.btn_accel,rows, 1)
        # rows += 1
        # #####################################################################
        # #Example of a slider with a label ###################################
        # #the slider is in a Hbox

        # #settings2_layout.addWidget(QLabel(tr('Permit camera waggle')), rows, 0, Qt.AlignmentFlag.AlignRight)

        self.accel_slider_valuelabel = QLabel(str(self.accel))
        settings2_layout.addWidget(self.accel_slider_valuelabel, rows, 1)

        settings2_layout.addWidget(QLabel(tr("Tripod")), rows, 2)
        self.accel_slider = QSlider(Qt.Orientation.Horizontal)  # スライダの向き
        self.accel_slider.setRange(1, 100)  # スライダの範囲
        self.accel_slider.setValue(1)  # 初期値
        self.accel_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.accel_slider.valueChanged.connect(self.accel_slider_on_draw)
        settings2_layout.addWidget(self.accel_slider, rows, 3)
        settings2_layout.addWidget(QLabel(tr("Handheld")), rows, 4)
        # self.btn_accel.toggled.connect(self.btn_accel_toggle)

        rows += 1
        # #####################################################################

        # Example of a slider with a label ###################################
        # the slider is in a Hbox

        settings2_layout.addWidget(
            QLabel(tr("Trailing frames")), rows, 0, Qt.AlignmentFlag.AlignRight
        )

        self.trailing_slider_valuelabel = QLabel(f"{self.trailing} " + tr("frames"))
        settings2_layout.addWidget(
            self.trailing_slider_valuelabel, rows, 1, Qt.AlignmentFlag.AlignCenter
        )

        settings2_layout.addWidget(
            QLabel(tr("Short")), rows, 2, Qt.AlignmentFlag.AlignRight
        )
        self.trailing_slider = QSlider(Qt.Orientation.Horizontal)  # スライダの向き
        self.trailing_slider.setRange(1, 150)  # スライダの範囲
        self.trailing_slider.setValue(10)  # 初期値
        # スライダの目盛りを両方に出す
        self.trailing_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.trailing_slider.valueChanged.connect(self.trailing_slider_on_draw)
        settings2_layout.addWidget(self.trailing_slider, rows, 3)
        settings2_layout.addWidget(QLabel(tr("Long")), rows, 4)

        rows += 1
        #####################################################################

        #####################################################################
        # Example of a checkbox
        settings2_layout.addWidget(
            QLabel(tr("Debug")), rows, 0, Qt.AlignmentFlag.AlignRight
        )
        self.btn_debug = QCheckBox()
        # self.btn_stall.setCheckState(Qt.CheckState.Checked)
        self.btn_debug.toggled.connect(self.toggle_debug)
        settings2_layout.addWidget(
            self.btn_debug, rows, 1, Qt.AlignmentFlag.AlignCenter
        )
        rows += 1
        #####################################################################

        gbox_settings.setLayout(settings2_layout)

        left_layout.addWidget(gbox_settings)

        # Left panel, lower pane: finish

        finish_layout_gbox = QGroupBox(tr("Finish"))
        finish_layout = QVBoxLayout()

        length_layout = QHBoxLayout()
        length_layout.addWidget(
            QLabel(tr("Set the upper bound of the product image width"))
        )
        self.btn_length = QCheckBox()
        length_layout.addWidget(self.btn_length)
        spin = QSpinBox()
        spin.setMinimum(100)
        spin.setMaximum(500000)
        spin.setValue(10000)
        spin.setMinimumWidth(50)
        self.spin_length = spin
        length_layout.addWidget(spin)
        length_layout.addWidget(QLabel(tr("pixels")))

        finish_layout.addLayout(length_layout)
        # https://www.tutorialspoint.com/pyqt/pyqt_qcheckbox_widget.htm
        # self.start_button = QPushButton(tr("Start"), self)
        # self.start_button.clicked.connect(self.start_process)
        # finish_layout.addWidget(self.start_button)

        finish_layout_gbox.setLayout(finish_layout)
        left_layout.addWidget(finish_layout_gbox)

        # combine panels
        layout.addLayout(left_layout)
        self.setLayout(layout)
        self.setWindowTitle("Settings")

    def dragEnterEvent(self, event):
        logger = getLogger()
        event.accept()
        mimeData = event.mimeData()
        logger.debug("dragEnterEvent")
        for mimetype in mimeData.formats():
            logger.debug(f"MIMEType: {mimetype}")
            logger.debug(f"Data: {mimeData.data(mimetype)}")

    def dropEvent(self, event):
        logger = getLogger()
        event.accept()
        mimeData = event.mimeData()
        logger.debug("dropEvent")
        for mimetype in mimeData.formats():
            logger.debug(f"MIMEType: {mimetype}")
            logger.debug(f"Data: {mimeData.data(mimetype)}")
        # Open only when:
        # 1. Only file is given
        # 3. and the mimetipe is text/uri-list
        # 2. That has the regular extension.
        logger.debug(f"len:{len(mimeData.formats())}")
        if len(mimeData.formats()) == 1:
            mimetype = mimeData.formats()[0]
            if mimetype == "text/uri-list":
                data = mimeData.data(mimetype)
                from urllib.parse import unquote, urlparse

                for line in bytes(data).decode("utf8").splitlines():
                    parsed = urlparse(unquote(line))
                    logger.debug(f"Data: {parsed}")
                    if parsed.scheme == "file":
                        if self.editor is not None:
                            self.editor.close()
                        self.fileparser(parsed.path)
                        return
        # or just ignore

    def reset_input(self):
        self.filename = ""
        self.editor = None
        self.le.setText(tr("(File name appears here)"))

    def getfile(self):
        logger = getLogger()
        if self.editor is not None:
            self.editor.close()
        logger.debug("Let's select a file")
        filename, types = QFileDialog.getOpenFileName(
            self,
            tr("Open a movie file"),
            "",
            "Movie files (*.mov *.mp4 *.m4v *.mts *.tsconf *.mkv)",
        )
        logger.debug(f"File: {filename}")
        if filename == "":  # or if the file cannot be opened,
            return
        self.fileparser(filename)

    def fileparser(self, filename):
        logger = getLogger()
        self.filename = filename
        if self.filename.rfind(".tsconf") + 7 == len(self.filename):
            # read all initial values from the file.
            ap = argparse.ArgumentParser(description="TrainScanner")
            parser_stitch = pp2(ap)
            # Set priority to the path of the given tsconf
            tsconf = self.filename
            tsconfdir = os.path.dirname(tsconf)
            if tsconfdir == "":
                tsconfdir = "."

            ## modified params,unknown = parser_stitch.parse_known_args(["@"+tsconf])
            with open(tsconf) as f:
                args = f.read().splitlines()
            params, unknown = parser_stitch.parse_known_args(args)
            logger.debug(f"Params1 {params} {unknown}")
            unknown += [params.filename]  # supply filename for pass1 parser
            # Assume the movie file is in the same dir as the tsconf
            self.filename = tsconfdir + "/" + os.path.basename(params.filename)
            # Otherwise use the path written in the tsconf file. (original location)
            if not os.path.exists(self.filename):
                self.filename = params.filename
            logger.debug(f"Movie  {self.filename}")
            parser_pass1 = pp1()
            ## modified params2,unknown2 = parser_pass1.parse_known_args(["@"+tsconf])
            params2, unknown2 = parser_pass1.parse_known_args(args)
            logger.debug(f"Params2 {params2} {unknown2}")
            # Only non-default values should overwrite the pp2 result.
            p1 = vars(params)
            p2 = vars(params2)
            for key in p2:
                p1[key] = p2[key]
            # set variables in self
            # and make the editor also.
            # Overwrite the filename
            p1["filename"] = self.filename
            self.editor = EditorGUI(self, params=p1)
            self.slitwidth_slider.setValue(int(p1["slitwidth"] * 100))
            self.antishake_slider.setValue(p1["antishake"])
            self.estimate_slider.setValue(p1["estimate"])
            if p1["zero"]:
                self.btn_zerodrift.setCheckState(Qt.CheckState.Checked)
            else:
                self.btn_zerodrift.setCheckState(Qt.CheckState.Unchecked)
            if p1["stall"]:
                self.btn_stall.setCheckState(Qt.CheckState.Checked)
            else:
                self.btn_stall.setCheckState(Qt.CheckState.Unchecked)
            self.trailing_slider.setValue(p1["trailing"])

        else:
            # self.filenameがディレクトリの場合も処理は同じ。
            self.filename = self.filename.rstrip("/")
            self.editor = EditorGUI(self, filename=self.filename)

        self.editor.show()

        # we shall set editor's values here.
        self.editor.sliderL.setMin(0)
        self.editor.sliderL.setMax(1000)
        self.editor.sliderL.setRange(
            self.editor.perspective[0], self.editor.perspective[2], 10
        )
        self.editor.sliderR.setMin(0)
        self.editor.sliderR.setMax(1000)
        self.editor.sliderR.setRange(
            self.editor.perspective[1], self.editor.perspective[3], 10
        )
        logger.debug(f"setRange crop {self.editor.croptop} {self.editor.cropbottom}")
        self.editor.crop_slider.setMin(0)
        self.editor.crop_slider.setMax(1000)
        self.editor.crop_slider.setRange(
            self.editor.croptop, self.editor.cropbottom, 10
        )
        self.editor.slit_slider.setValue(self.editor.slitpos)
        self.editor.angle_label.setText(f"{self.editor.angle_degree} " + tr("degrees"))
        self.le.setText(self.filename)

    def toggle_debug(self):
        # Once remove all the handlers
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        if self.btn_debug.isChecked():
            print("!!!")
            basicConfig(
                level=DEBUG,
                # filename='log.txt',
                format="%(asctime)s %(levelname)s %(message)s",
            )
        else:
            basicConfig(level=WARN, format="%(asctime)s %(levelname)s %(message)s")

    def trailing_slider_on_draw(self):
        self.trailing = self.trailing_slider.value()
        self.trailing_slider_valuelabel.setText(f"{self.trailing} " + tr("frames"))

    def slitwidth_slider_on_draw(self):
        self.slitwidth = self.slitwidth_slider.value()
        self.slitwidth_slider_valuelabel.setText(f"{self.slitwidth}%")

    def antishake_slider_on_draw(self):
        self.antishake = self.antishake_slider.value()
        self.antishake_slider_valuelabel.setText(f"{self.antishake} " + tr("pixels"))

    def estimate_slider_on_draw(self):
        self.estimate = self.estimate_slider.value()
        self.estimate_slider_valuelabel.setText(f"{self.estimate} " + tr("frames"))

    def accel_slider_on_draw(self):
        self.accel = self.accel_slider.value()
        self.accel_slider_valuelabel.setText(str(self.accel))

    ##    def identthres_slider_on_draw(self):
    ##        self.identity = self.identthres_slider.value()
    ##        self.skipident_valuelabel.setText(str(self.identity))

    def start_process(self):
        logger = getLogger()
        if self.editor is None:
            return
        now = int(time.time()) % 100000
        logfilenamebase = self.filename + f".{now}"
        stitch_options = []
        stitch_options += [f"slit={self.editor.slitpos}"]
        stitch_options += [f"width={self.slitwidth / 100.0}"]
        if self.btn_length.isChecked():
            stitch_options += [f"length={self.spin_length.value()}"]

        common_options = []
        common_options += [
            "--perspective",
        ] + [str(x) for x in self.editor.perspective]
        common_options += ["--rotate", f"{self.editor.angle_degree}"]
        common_options += [
            "--crop",
        ] + [str(x) for x in (self.editor.croptop, self.editor.cropbottom)]
        pass1_options = []
        pass1_options += ["--trail", f"{self.trailing}"]
        pass1_options += ["--antishake", f"{self.antishake}"]
        pass1_options += ["--estimate", f"{self.estimate}"]
        pass1_options += ["--identity", f"{self.identity}"]
        pass1_options += [
            "--skip",
            f"{self.editor.imageselector2.slider.start() * self.editor.every_n_frames}",
        ]
        pass1_options += [
            "--last",
            f"{self.editor.imageselector2.slider.end() * self.editor.every_n_frames}",
        ]
        pass1_options += [
            "--focus",
        ] + [str(x) for x in self.editor.focus]
        if self.btn_zerodrift.isChecked():
            pass1_options += [
                "--zero",
            ]
        if self.btn_stall.isChecked():
            pass1_options += [
                "--stall",
            ]
        pass1_options += ["--maxaccel", f"{self.accel}"]
        pass1_options += ["--log", logfilenamebase]

        # wrap the options to record in the tsconf file
        # THIS IS WEIRD. FIND BETTER WAY.
        # LOG FILE MADE BY PASS1_GUI IS DIFFERENT FROM THAT BY GUI5.PY..
        # IT IS ALSO WEIRD.
        # PASS1 must write the options and settings in the tsconf by itself.
        argv = (
            [
                "pass1",
            ]
            + common_options
            + pass1_options
        )
        for op in stitch_options:
            argv += ["-2", op]
        argv += [
            self.filename,
        ]

        matcher = pass1.MatcherUI(argv, False)  # do not terminate
        matcher.exec()
        if matcher.terminated or not matcher.success:
            matcher = None
            return
        matcher = None
        argv = ["stitch"]
        ## modified argv += [ "@"+logfilenamebase+".tsconf",]
        argv += [
            "--file",
            logfilenamebase + ".tsconf",
        ]

        stitcher = stitch.StitcherUI(argv, False)
        file_name = stitcher.stitcher.outfilename
        stitcher.setMaximumHeight(500)
        stitcher.showMaximized()
        stitcher.exec()
        stitcher = None

    def closeEvent(self, event):
        if self.editor is not None:
            self.editor.close()


# for pyinstaller
def resource_path(relative):
    return os.path.join(os.environ.get("_MEIPASS", os.path.abspath(".")), relative)


def main():
    # pyqt_set_trace()
    basicConfig(level=WARN, format="%(asctime)s %(levelname)s %(message)s")
    app = QApplication(sys.argv)
    # translator = QTranslator(app)
    path = os.path.dirname(trainscanner.__file__)

    # まずLANG環境変数を確認
    lang = os.environ.get("LANG", "").split("_")[0]

    # LANGが設定されていない場合はQLocaleを使用
    if not lang:
        locale = QLocale()
        lang = locale.name().split("_")[0]

    from trainscanner.i18n import init_translations

    init_translations()

    # if lang == "ja":
    #     translator.load(path + "/i18n/trainscanner_ja")
    # elif lang == "fr":
    #     translator.load(path + "/i18n/trainscanner_fr")
    # app.installTranslator(translator)
    se = SettingsGUI()
    se.show()
    se.raise_()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
