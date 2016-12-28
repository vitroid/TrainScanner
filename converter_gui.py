#!/usr/bin/env python3
#-*- coding: utf-8 -*-

#Core of the GUI and image process
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication, QPushButton, QCheckBox, QFileDialog
from PyQt5.QtCore    import QTranslator
import cv2
import numpy as np
import math
import trainscanner
import time

#File handling
import os
import subprocess

#final image tranformation
import film
import helix
import rect

#options handler
import sys




#https://www.tutorialspoint.com/pyqt/pyqt_qfiledialog_widget.htm
class SettingsGUI(QWidget):
    def __init__(self, parent = None):
        super(SettingsGUI, self).__init__(parent)

        finish_layout = QVBoxLayout()
        self.btn = QPushButton(self.tr('Open an image'))
        self.btn.clicked.connect(self.getfile)
        finish_layout.addWidget(self.btn)
        self.btn_finish_perf = QCheckBox(self.tr('Add the film perforations'))
        finish_layout.addWidget(self.btn_finish_perf)
        self.btn_finish_helix = QCheckBox(self.tr('Make a helical image'))
        finish_layout.addWidget(self.btn_finish_helix)
        self.btn_finish_rect = QCheckBox(self.tr('Make a rectangular image'))
        finish_layout.addWidget(self.btn_finish_rect)
        self.start_button = QPushButton(self.tr('Start'),self)
        self.start_button.clicked.connect(self.start_process)
        finish_layout.addWidget(self.start_button)

        self.setLayout(finish_layout)
        self.setWindowTitle("Convert")
		
        
    def getfile(self):
        #OSチェック
        def os_check():
            #windows
            if os.name is 'nt':
                code = 'cp932'
                return code
            #Unix、Mac
            if os.name is not 'nt':
                code = 'utf-8'
                return code

        self.filename, types = QFileDialog.getOpenFileName(self, self.tr('Open file'), 
            "","Image files (*.png *.tif *.jpg *.jpeg *.gif)")
        if self.filename == "": # or if the file cannot be opened,
            return
        #if type(self.filename) is not str:
        #    print(type(self.filename))
        #    self.filename = unicode(self.filename.toUtf8(), encoding=os_check()).encode('utf-8')




    def start_process(self):
        file_name = self.filename
        img = cv2.imread(file_name)
        if self.btn_finish_perf.isChecked():
            img = film.filmify( img )
            file_name += ".film.png"
            cv2.imwrite(file_name, img)
        if self.btn_finish_helix.isChecked():
            himg = helix.helicify( img )
            cv2.imwrite(file_name + ".helix.png", himg)
        if self.btn_finish_rect.isChecked():
            rimg = rect.rectify( img )
            cv2.imwrite(file_name + ".rect.png", rimg)
        



def SystemLanguage():
    import platform
    ostype = platform.system()
    loc = []
    if ostype == "Darwin":
        #for macos
        import re
        output = subprocess.check_output(["defaults","read","-g","AppleLanguages"])
        output = output.decode('utf-8')
        for l in output.split("\n")[1:len(output)-2]:
            lang = re.sub(r'[ "]+', '', l)
            loc.append(lang)
        return loc[0]
        #print(loc)
    elif ostype == "Windows":
        import ctypes
        import locale
        windll = ctypes.windll.kernel32
        loc = locale.windows_locale[ windll.GetUserDefaultUILanguage() ]
        return loc
    return loc
    
#for pyinstaller
def resource_path(relative):
    return os.path.join(
        os.environ.get(
            "_MEIPASS",
            os.path.abspath(".")
        ),
        relative
    )

import pkgutil

def main():
    app = QApplication(sys.argv)
    translator = QTranslator(app)
    rpath = getattr(sys, '_MEIPASS', os.getcwd())
    loc = SystemLanguage()
    if loc[:2] == "ja":
        translator.load(rpath+"/i18n/trainscanner_ja")
    app.installTranslator(translator)
    se = SettingsGUI()
    se.show()
    se.raise_()
    sys.exit(app.exec_())
	
if __name__ == '__main__':
    main()
