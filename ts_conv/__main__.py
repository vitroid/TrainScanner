#!/usr/bin/env python3
#-*- coding: utf-8 -*-

#Core of the GUI and image process
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication, QPushButton, QCheckBox, QFileDialog
from PyQt5.QtCore    import QTranslator, QLocale
import cv2
import numpy as np
import math
import time
import logging

#File handling
import os
import subprocess

#final image tranformation
from ts_conv import film
from ts_conv import helix
from ts_conv import rect

#options handler
import sys




#https://www.tutorialspoint.com/pyqt/pyqt_qfiledialog_widget.htm
class SettingsGUI(QWidget):
    def __init__(self, parent = None):
        super(SettingsGUI, self).__init__(parent)
        self.setAcceptDrops(True)

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
        self.filename, types = QFileDialog.getOpenFileName(self, self.tr('Open file'), 
            "","Image files (*.png *.tif *.jpg *.jpeg *.gif)")
        if self.filename == "": # or if the file cannot be opened,
            return


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



    def dragEnterEvent(self, event):
        logger = logging.getLogger()
        event.accept()
        mimeData = event.mimeData()
        logger.debug('dragEnterEvent')
        for mimetype in mimeData.formats():
            logger.debug('MIMEType: {0}'.format(mimetype))
            logger.debug('Data: {0}'.format(mimeData.data(mimetype)))

    def dropEvent(self, event):
        logger = logging.getLogger()
        event.accept()
        mimeData = event.mimeData()
        logger.debug('dropEvent')
        for mimetype in mimeData.formats():
            logger.debug('MIMEType: {0}'.format(mimetype))
            logger.debug('Data: {0}'.format(mimeData.data(mimetype)))
        #Open only when:
        #1. Only file is given
        #3. and the mimetipe is text/uri-list
        #2. That has the regular extension.
        logger.debug("len:{0}".format(len(mimeData.formats())))
        if len(mimeData.formats()) == 1:
            mimetype = mimeData.formats()[0]
            if mimetype == "text/uri-list":
                data = mimeData.data(mimetype)
                from urllib.parse import urlparse, unquote
                for line in bytes(data).decode('utf8').splitlines():
                    parsed = urlparse(unquote(line))
                    logger.debug('Data: {0}'.format(parsed))
                    if parsed.scheme == 'file':
                        self.filename = parsed.path
                        return
        #or just ignore




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
    if QLocale.system().language() == QLocale.Japanese:
        translator.load(rpath+"/i18n/trainscanner_ja")
    app.installTranslator(translator)
    se = SettingsGUI()
    se.show()
    se.raise_()
    sys.exit(app.exec_())
	
if __name__ == '__main__':
    main()
