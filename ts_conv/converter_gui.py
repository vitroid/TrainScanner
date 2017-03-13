#!/usr/bin/env python3
#-*- coding: utf-8 -*-

#Core of the GUI and image process
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication, QPushButton, QCheckBox, QFileDialog, QProgressBar
from PyQt5.QtGui     import QPalette, QPainter
from PyQt5.QtCore    import QTranslator, QLocale, Qt
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
from tiledimage.cachedimage import CachedImage
#options handler
import sys


#Drag and drop work. Buttons would not be necessary.



#https://www.tutorialspoint.com/pyqt/pyqt_qfiledialog_widget.htm
class SettingsGUI(QWidget):
    def __init__(self, parent = None):
        super(SettingsGUI, self).__init__(parent)
        self.setAcceptDrops(True)

        finish_layout = QVBoxLayout()
        self.btn_finish_perf = QCheckBox(self.tr('Add the film perforations'))
        finish_layout.addWidget(self.btn_finish_perf)
        self.btn_finish_helix = QCheckBox(self.tr('Make a helical image'))
        finish_layout.addWidget(self.btn_finish_helix)
        self.btn_finish_rect = QCheckBox(self.tr('Make a rectangular image'))
        finish_layout.addWidget(self.btn_finish_rect)
        self.pbar = QProgressBar()
        self.pbar.setValue(0)
        self.pbar.setRange(0,8)
        finish_layout.addWidget(self.pbar)

        self.setLayout(finish_layout)
        self.setWindowTitle("Drag&Drop files")
		
        
    def start_process(self):
        logger = logging.getLogger()
        self.pbar.setValue(0)
        if self.filename[-6:] == ".pngs/":
            self.filename = self.filename[:-1]
            cachedimage = CachedImage("inherit",
                                      dir=self.filename,
                                      disposal=False)
            logger.debug(":: {0}".format(cachedimage))
            img = cachedimage.get_region(None)
        else:
            img = cv2.imread(self.filename)
        file_name = self.filename
        self.pbar.setValue(1)
        if self.btn_finish_perf.isChecked():
            img = film.filmify( img )
            self.pbar.setValue(2)
            file_name += ".film.png"
            cv2.imwrite(file_name, img)
            self.pbar.setValue(3)
        if self.btn_finish_helix.isChecked():
            self.pbar.setValue(4)
            himg = helix.helicify( img )
            self.pbar.setValue(5)
            cv2.imwrite(file_name + ".helix.png", himg)
        if self.btn_finish_rect.isChecked():
            self.pbar.setValue(6)
            rimg = rect.rectify( img )
            self.pbar.setValue(7)
            cv2.imwrite(file_name + ".rect.png", rimg)
        self.pbar.setValue(8)



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
                        #Start immediately
                        self.start_process()
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
    logging.basicConfig(level=logging.WARN,
                        format="%(asctime)s %(levelname)s %(message)s")
    app = QApplication(sys.argv)
    translator = QTranslator(app)
    path = os.path.dirname(rect.__file__)
    if QLocale.system().language() == QLocale.Japanese:
        translator.load(path+"/i18n/trainscanner_ja")
    app.installTranslator(translator)
    se = SettingsGUI()
    se.show()
    se.raise_()
    sys.exit(app.exec_())
	
if __name__ == '__main__':
    main()
