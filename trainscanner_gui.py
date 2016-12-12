#!/usr/bin/env python3
#-*- coding: utf-8 -*-

#Core of the GUI and image process
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QDialog, QApplication, QProgressBar, QVBoxLayout, QScrollArea, QHBoxLayout, QGroupBox, QGridLayout, QSlider, QCheckBox, QSpinBox, QFileDialog, QRubberBand
from PyQt5.QtGui     import QImage, QPixmap, QPainter
from PyQt5.QtCore    import QObject, pyqtSignal, QThread, Qt, QPoint, QTranslator, QRect, QSize

import cv2
import numpy as np
import math
import trainscanner
from imageselector2 import ImageSelector2
import time

#File handling
import os
import subprocess

#sub dialog windows
import pass1_gui    
import stitch_gui


#options handler
import sys
from pass1 import prepare_parser as pp1
from stitch import prepare_parser as pp2
import argparse




class AsyncImageLoader(QObject):
    """
    This works in the background as a separate thread
    to load the thumbnails for the time line
    """
    frameIncreased = pyqtSignal(list)
    
    def __init__(self, parent=None, filename="", size=0):
        super(AsyncImageLoader, self).__init__(parent)
        self.isRunning = True

        #capture the first frame ASAP to avoid "no frame" errors.
        self.size = size
        self.cap = cv2.VideoCapture(filename)
        ret, frame = self.cap.read()
        if self.size:
            frame = trainscanner.fit_to_square(frame, self.size)
        self.snapshots = [frame]


    def stop(self):
        self.isRunning = False
        #trash images
        self.snapshots = []
        #print("Thumbs trashed.")


    def task(self):
        if not self.isRunning:
            self.isRunning = True
            
        while self.isRunning:
            ret, frame = self.cap.read()
            if not ret:
                break
            if self.size:
                frame = trainscanner.fit_to_square(frame, self.size)
            self.snapshots.append(frame)
            self.frameIncreased.emit(self.snapshots)
            for i in range(9):
                ret = self.cap.grab()
                if not ret:
                    break

        #print("Finished")


class DrawableLabel(QLabel):
    def __init__(self, parent=None):
        super(QLabel, self).__init__(parent)
        self.perspective = (0,0,1000,1000)
        self.geometry = (0,0,1000,1000)

    def paintEvent(self, event):
        QLabel.paintEvent(self, event)
        painter = QPainter(self)
        painter.setPen(Qt.red)
        #painter.setBrush(Qt.yellow)
        #painter.drawRect(10, 10, 100, 100)
        x,y,w,h = self.geometry
        painter.drawLine(x,y+self.perspective[0]*h//1000,x+w,y+self.perspective[1]*h//1000)
        painter.drawLine(x,y+self.perspective[2]*h//1000,x+w,y+self.perspective[3]*h//1000)


def draw_slitpos(f, slitpos):
    h, w = f.shape[0:2]
    slitpos1 = (slitpos+500)*w//1000
    slitpos2 = (500-slitpos)*w//1000
    cv2.line(f, (slitpos1,0),(slitpos1,h), (0, 0, 255), 1)
    cv2.line(f, (slitpos2,0),(slitpos2,h), (0, 0, 255), 1)

class MyLabel(QLabel):

    def __init__(self, parent = None, func=None):

        self.func = func
        QLabel.__init__(self, parent)
        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)
        self.origin = QPoint()
        self.slitpos = 250
        self.focus = (333,666,333,666)  #xs,xe,ys,ye
        self.geometry = (0,0,1000,1000) #x,y,w,h

    def paintEvent(self, event):
        QLabel.paintEvent(self, event)
        painter = QPainter(self)
        painter.setPen(Qt.red)
        x,y,w,h = self.geometry
        d = 20
        painter.drawLine(x+w//2-self.slitpos*w//1000,y,
                         x+w//2-self.slitpos*w//1000,y+h)
        painter.drawLine(x+w//2-self.slitpos*w//1000-d,y+h/2,
                         x+w//2-self.slitpos*w//1000,  y+h/2-d)
        painter.drawLine(x+w//2-self.slitpos*w//1000-d,y+h/2,
                         x+w//2-self.slitpos*w//1000,  y+h/2+d)
        painter.drawLine(x+w//2+self.slitpos*w//1000,y,
                         x+w//2+self.slitpos*w//1000,y+h)
        painter.drawLine(x+w//2+self.slitpos*w//1000+d,y+h//2,
                         x+w//2+self.slitpos*w//1000,  y+h//2-d)
        painter.drawLine(x+w//2+self.slitpos*w//1000+d,y+h//2,
                         x+w//2+self.slitpos*w//1000,  y+h//2+d)
        painter.setPen(Qt.green)
        painter.drawRect(x+w*self.focus[0]//1000,y+h*self.focus[2]//1000,w*(self.focus[1]-self.focus[0])//1000,h*(self.focus[3]-self.focus[2])//1000)
        
    def mousePressEvent(self, event):
    
        if event.button() == Qt.LeftButton:
        
            self.origin = QPoint(event.pos())
            self.rubberBand.setGeometry(QRect(self.origin, QSize()))
            self.rubberBand.show()
    
    def mouseMoveEvent(self, event):
    
        if not self.origin.isNull():
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())
    
    def mouseReleaseEvent(self, event):
    
        if event.button() == Qt.LeftButton:
            self.rubberBand.hide()
            self.region = QRect(self.origin, event.pos()).normalized()
            if self.func is not None:
                self.func(self.region)

#https://www.tutorialspoint.com/pyqt/pyqt_qfiledialog_widget.htm
class SettingsGUI(QWidget):
    def __init__(self, parent = None):
        super(SettingsGUI, self).__init__(parent)

        # options
        self.trailing = 10
        self.editor = None
        self.antishake = 5
        self.estimate = 10
        self.slitwidth = 50
        self.identity = 2.0
        self.accel    = 1

        #private
        # layout
        layout = QHBoxLayout()
        
        #leftmost panel for specifying options
        left_layout = QVBoxLayout()
        self.btn = QPushButton(self.tr('Open a movie'))
        self.btn.clicked.connect(self.getfile)
        left_layout.addWidget(self.btn)
    
        self.le = QLabel(self.tr('(File name appears here)'))
        #self.le = QLabel()
        left_layout.addWidget(self.le)
        
        #self.pbar = QProgressBar()
        #self.pbar.setValue(0)
        #left_layout.addWidget(self.pbar)

        #Left panel, upper pane: settings
        gbox_settings = QGroupBox(self.tr('Settings'))
        settings2_layout = QGridLayout()
        rows = 0
        #http://myenigma.hatenablog.com/entry/2016/01/24/113413


        
        #Example of a slider with a label ###################################
        #the slider is in a Hbox
        
        settings2_layout.addWidget(QLabel(self.tr('Slit mixing')), rows, 0, Qt.AlignRight)
        
        self.slitwidth_slider_valuelabel = QLabel("{0}%".format(self.slitwidth))
        settings2_layout.addWidget(self.slitwidth_slider_valuelabel, rows, 1, Qt.AlignCenter)
        
        settings2_layout.addWidget(QLabel(self.tr('Sharp')), rows, 2, Qt.AlignRight)
        self.slitwidth_slider = QSlider(Qt.Horizontal)  # スライダの向き
        self.slitwidth_slider.setRange(5, 300)  # スライダの範囲
        self.slitwidth_slider.setValue(self.slitwidth)  # 初期値
        self.slitwidth_slider.setTickPosition(QSlider.TicksBelow)
        self.slitwidth_slider.valueChanged.connect(self.slitwidth_slider_on_draw)
        settings2_layout.addWidget(self.slitwidth_slider, rows, 3)
        settings2_layout.addWidget(QLabel(self.tr('Diffuse')), rows, 4)

        rows += 1
        #####################################################################


        #Example of a slider with a label ###################################
        #the slider is in a Hbox

        settings2_layout.addWidget(QLabel(self.tr('Minimal displacement between the frames')), rows, 0, Qt.AlignRight)
        
        self.antishake_slider_valuelabel = QLabel("{0} ".format(self.antishake)+self.tr("pixels"))
        settings2_layout.addWidget(self.antishake_slider_valuelabel, rows, 1, Qt.AlignCenter)
        
        settings2_layout.addWidget(QLabel(self.tr('Small')), rows, 2, Qt.AlignRight)
        self.antishake_slider = QSlider(Qt.Horizontal)  # スライダの向き
        self.antishake_slider.setRange(0, 15)  # スライダの範囲
        self.antishake_slider.setValue(5)  # 初期値
        #スライダの目盛りを両方に出す
        self.antishake_slider.setTickPosition(QSlider.TicksBelow)
        self.antishake_slider.valueChanged.connect(self.antishake_slider_on_draw)
        settings2_layout.addWidget(self.antishake_slider, rows, 3)
        settings2_layout.addWidget(QLabel(self.tr('Large')), rows, 4)

        rows += 1
        #####################################################################

        #Example of a slider with a label ###################################
        #the slider is in a Hbox

        settings2_layout.addWidget(QLabel(self.tr('Number of frames to estimate the velocity')), rows, 0, Qt.AlignRight)
        
        self.estimate_slider_valuelabel = QLabel("{0} ".format(self.estimate)+self.tr("frames"))
        settings2_layout.addWidget(self.estimate_slider_valuelabel, rows, 1, Qt.AlignCenter)
        
        settings2_layout.addWidget(QLabel(self.tr('Short')), rows, 2, Qt.AlignRight)
        self.estimate_slider = QSlider(Qt.Horizontal)  # スライダの向き
        self.estimate_slider.setRange(5, 50)  # スライダの範囲
        self.estimate_slider.setValue(10)  # 初期値
        #スライダの目盛りを両方に出す
        self.estimate_slider.setTickPosition(QSlider.TicksBelow)
        self.estimate_slider.valueChanged.connect(self.estimate_slider_on_draw)
        settings2_layout.addWidget(self.estimate_slider, rows, 3)
        settings2_layout.addWidget(QLabel(self.tr('Long')), rows, 4)

        rows += 1
        #####################################################################

        #####################################################################
        #Example of a checkbox
        settings2_layout.addWidget(QLabel(self.tr('Ignore vertical displacements')), rows, 0, Qt.AlignRight)
        self.btn_zerodrift = QCheckBox()
        self.btn_zerodrift.setCheckState(Qt.Checked)
        #self.b2.toggled.connect(lambda:self.btnstate(self.b2))
        settings2_layout.addWidget(self.btn_zerodrift,rows, 1, Qt.AlignCenter)
        rows += 1
        #####################################################################


        #####################################################################
        #Example of a checkbox
        settings2_layout.addWidget(QLabel(self.tr('The train is initially stalling in the motion detection area.')), rows, 0, Qt.AlignRight)
        self.btn_stall = QCheckBox()
        #self.btn_stall.setCheckState(Qt.Checked)
        #self.b2.toggled.connect(lambda:self.btnstate(self.b2))
        settings2_layout.addWidget(self.btn_stall,rows, 1, Qt.AlignCenter)
        rows += 1
        #####################################################################


        # #####################################################################
        # #Example of a checkbox
        settings2_layout.addWidget(QLabel(self.tr('Max acceleration')), rows, 0, Qt.AlignRight)
        # self.btn_accel = QCheckBox()
        # self.btn_accel.setCheckState(Qt.Checked)
        # settings2_layout.addWidget(self.btn_accel,rows, 1)
        # rows += 1
        # #####################################################################
        # #Example of a slider with a label ###################################
        # #the slider is in a Hbox

        # #settings2_layout.addWidget(QLabel(self.tr('Permit camera waggle')), rows, 0, Qt.AlignRight)
        
        self.accel_slider_valuelabel = QLabel(str(self.accel))
        settings2_layout.addWidget(self.accel_slider_valuelabel, rows, 1)
        
        settings2_layout.addWidget(QLabel(self.tr('Tripod')), rows, 2)
        self.accel_slider = QSlider(Qt.Horizontal)  # スライダの向き
        self.accel_slider.setRange(1, 15)  # スライダの範囲
        self.accel_slider.setValue(1)  # 初期値
        self.accel_slider.setTickPosition(QSlider.TicksBelow)
        self.accel_slider.valueChanged.connect(self.accel_slider_on_draw)
        settings2_layout.addWidget(self.accel_slider, rows, 3)
        settings2_layout.addWidget(QLabel(self.tr('Handheld')), rows, 4)
        #self.btn_accel.toggled.connect(self.btn_accel_toggle)

        rows += 1
        # #####################################################################







        
        # #Example of a checkbox and slider with a label
        # #-i (identity)

        # settings2_layout.addWidget(QLabel(self.tr('Skip identical frames')), rows, 0, Qt.AlignRight)

        # #self.btn_skipident = QCheckBox(self.tr('Skip identical frames'))
        # #self.b2.toggled.connect(lambda:self.btnstate(self.b2))
        # #skipident_layout.addWidget(self.btn_skipident)
        
        
        # self.skipident_valuelabel = QLabel(str(self.identity))
        # settings2_layout.addWidget(self.skipident_valuelabel, rows, 1)
    
        # settings2_layout.addWidget(QLabel(self.tr('Strict')), rows, 2)
        # self.identthres_slider = QSlider(Qt.Horizontal)  # スライダの向き
        # self.identthres_slider.setRange(1, 5)  # スライダの範囲
        # self.identthres_slider.setValue(2)  # 初期値
        # #スライダの目盛りを両方に出す
        # self.identthres_slider.setTickPosition(QSlider.TicksBelow)
        # self.connect(self.identthres_slider, SIGNAL('valueChanged(int)'), self.identthres_slider_on_draw)
        # #the slider is in a Hbox
        # settings2_layout.addWidget(self.identthres_slider, rows, 3)
        # settings2_layout.addWidget(QLabel(self.tr('Loose')), rows, 4)
        # rows += 1
        # #####################################################################


        #Example of a slider with a label ###################################
        #the slider is in a Hbox

        settings2_layout.addWidget(QLabel(self.tr('Trailing frames')), rows,0, Qt.AlignRight)
        
        self.trailing_slider_valuelabel = QLabel("{0} ".format(self.trailing)+self.tr("frames"))
        settings2_layout.addWidget(self.trailing_slider_valuelabel, rows,1, Qt.AlignCenter)

        settings2_layout.addWidget(QLabel(self.tr('Short')), rows, 2, Qt.AlignRight)
        self.trailing_slider = QSlider(Qt.Horizontal)  # スライダの向き
        self.trailing_slider.setRange(1, 30)  # スライダの範囲
        self.trailing_slider.setValue(10)  # 初期値
        #スライダの目盛りを両方に出す
        self.trailing_slider.setTickPosition(QSlider.TicksBelow)
        self.trailing_slider.valueChanged.connect(self.trailing_slider_on_draw)
        settings2_layout.addWidget(self.trailing_slider, rows, 3)
        settings2_layout.addWidget(QLabel(self.tr('Long')), rows, 4)

        rows += 1
        #####################################################################


        gbox_settings.setLayout(settings2_layout)

        left_layout.addWidget(gbox_settings)

        #Left panel, lower pane: finish
        
        finish_layout_gbox = QGroupBox(self.tr('Finish'))
        finish_layout = QVBoxLayout()

        length_layout = QHBoxLayout()
        length_layout.addWidget(QLabel(self.tr('Set the upper bound of the product image width')))
        self.btn_length = QCheckBox()
        length_layout.addWidget(self.btn_length)
        spin = QSpinBox()
        spin.setMinimum(100)
        spin.setMaximum(500000)
        spin.setValue(10000)
        spin.setMinimumWidth(50)
        self.spin_length = spin
        length_layout.addWidget(spin)
        length_layout.addWidget(QLabel(self.tr('pixels')))

        finish_layout.addLayout(length_layout)
        #https://www.tutorialspoint.com/pyqt/pyqt_qcheckbox_widget.htm
        self.start_button = QPushButton(self.tr('Start'),self)
        self.start_button.clicked.connect(self.start_process)
        finish_layout.addWidget(self.start_button)

       
        finish_layout_gbox.setLayout(finish_layout)
        left_layout.addWidget(finish_layout_gbox)


        
        #combine panels
        layout.addLayout(left_layout)
        self.setLayout(layout)
        self.setWindowTitle("Settings")
		
    def reset_input(self):
        self.filename = ""
        self.editor = None
        self.le.setText(self.tr('(File name appears here)'))
        
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

        if self.editor is not None:
            self.editor.close()
        self.filename, types = QFileDialog.getOpenFileName(self, self.tr('Open file'), 
            "","Movie files (*.mov *.mp4 *.mts *.tsconf)")
        if self.filename == "": # or if the file cannot be opened,
            return
        #for py2
        #if type(self.filename) is not str:
        #    self.filename = unicode(self.filename.toUtf8(), encoding=os_check()).encode('utf-8')
        #for py3 self.filename is a str
        #print(type(self.filename))
        if self.filename.rfind(".tsconf") + 7 == len(self.filename):
            #read all initial values from the file.
            ap = argparse.ArgumentParser(fromfile_prefix_chars='@',
                                        description='TrainScanner')
            parser_stitch = pp2(ap)
            tsconf = self.filename
            params,unknown = parser_stitch.parse_known_args(["@"+tsconf])
            print(3,params,unknown)
            unknown += [params.filename] #supply filename for pass1 parser
            #print(params.filename,"<<<")
            self.filename = params.filename
            parser_pass1 = pp1()
            #params2,unknown2 = parser_pass1.parse_known_args(unknown)
            params2,unknown2 = parser_pass1.parse_known_args(["@"+tsconf])
            print(4,params2,unknown2)
            #Only non-default values should overwrite the pp2 result.
            p1 = vars(params)
            p2 = vars(params2)
            for key in p2:
                p1[key] = p2[key]
            print(p1)
            #set variables in self
            #and make the editor also.
            self.editor = EditorGUI(self, params=p1)
            self.slitwidth_slider.setValue(int(p1["slitwidth"]*100))
            self.antishake_slider.setValue(p1["antishake"])
            self.estimate_slider.setValue(p1["estimate"])
            if p1["zero"]:
                self.btn_zerodrift.setCheckState(Qt.Checked)
            else:
                self.btn_zerodrift.setCheckState(Qt.Unchecked)
            if p1["stall"]:
                self.btn_stall.setCheckState(Qt.Checked)
            else:
                self.btn_stall.setCheckState(Qt.Unchecked)
            self.trailing_slider.setValue(p1["trailing"])
            
        else:
            self.editor = EditorGUI(self, filename=self.filename)
        #dir = os.path.dirname(self.filename)
        #base = os.path.basename(self.filename)
        #self.filename = "sample3.mov"
        self.editor.setMaximumHeight(500)
        self.editor.setMaximumWidth(500)
        self.editor.show()
        self.le.setText(self.filename)
        


##    def btn_accel_toggle(self, state):
##        self.accel_slider.setEnabled(state)

        
    def trailing_slider_on_draw(self):
        self.trailing = self.trailing_slider.value()
        self.trailing_slider_valuelabel.setText("{0} ".format(self.trailing)+self.tr("frames"))


    def slitwidth_slider_on_draw(self):
        self.slitwidth = self.slitwidth_slider.value()
        self.slitwidth_slider_valuelabel.setText("{0}%".format(self.slitwidth))


    def antishake_slider_on_draw(self):
        self.antishake = self.antishake_slider.value()
        self.antishake_slider_valuelabel.setText("{0} ".format(self.antishake)+self.tr("pixels"))


    def estimate_slider_on_draw(self):
        self.estimate = self.estimate_slider.value()
        self.estimate_slider_valuelabel.setText("{0} ".format(self.estimate)+self.tr("frames"))


    def accel_slider_on_draw(self):
        self.accel = self.accel_slider.value()
        self.accel_slider_valuelabel.setText(str(self.accel))


##    def identthres_slider_on_draw(self):
##        self.identity = self.identthres_slider.value()
##        self.skipident_valuelabel.setText(str(self.identity))


    def start_process(self):
        if self.editor is None:
            return
        now = int(time.time()) % 100000
        logfilenamebase = self.filename+".{0}".format(now)
        stitch_options = []
        stitch_options += ["slit={0}".format(self.editor.slitpos)]
        stitch_options += ["width={0}".format(self.slitwidth/100.0)]
        if self.btn_length.isChecked():
            stitch_options += ["length={0}".format(self.spin_length.value())]

        common_options = []
        common_options += ["--perspective",] + [str(x) for x in self.editor.perspective]
        common_options += ["--rotate", "{0}".format(self.editor.angle_degree)]
        common_options += ["--crop",] + [str(x) for x in (self.editor.croptop,self.editor.cropbottom)]
        pass1_options = []
        pass1_options += ["--trail", "{0}".format(self.trailing)]
        pass1_options += ["--antishake", "{0}".format(self.antishake)]
        pass1_options += ["--estimate", "{0}".format(self.estimate)]
        pass1_options += ["--skip", "{0}".format(self.editor.imageselector2.slider.value()*10)]
        pass1_options += ["--focus",] + [str(x) for x in self.editor.focus]
        if self.btn_zerodrift.isChecked():
            pass1_options += ["--zero",]
        if self.btn_stall.isChecked():
            pass1_options += ["--stall",]
        pass1_options += ["--maxaccel","{0}".format(self.accel)]
        pass1_options += ["--log", logfilenamebase]

        #wrap the options to record in the tsconf file
        #THIS IS WEIRD. FIND BETTER WAY.
        #LOG FILE MADE BY PASS1_GUI IS DIFFERENT FROM THAT BY GUI5.PY..
        #IT IS ALSO WEIRD.
        #PASS1 must write the options and settings in the tsconf by itself.
        argv = ["pass1", ] + common_options + pass1_options
        for op in stitch_options:
            argv += ["-2", op]
        argv += [self.filename,]
        #print(argv)
        
        self.matcher = pass1_gui.MatcherUI(argv, False)  #do not terminate
        self.matcher.exec_()
        if self.matcher.terminated:
            return
        argv = ["stitch"]
        argv += [ "@"+logfilenamebase+".tsconf",]
            
        self.stitcher = stitch_gui.StitcherUI(argv, False)
        file_name = self.stitcher.st.outfilename
        self.stitcher.setMaximumHeight(500)
        self.stitcher.showMaximized()
        #self.stitcher.show()
        

    def closeEvent(self,event):
        if self.editor is not None:
            self.editor.close()

    #def focusInEvent(self, event):
    #    #clear precede input

#https://www.tutorialspoint.com/pyqt/pyqt_qfiledialog_widget.htm
class EditorGUI(QWidget):
    thread_invoker = pyqtSignal()

    def __init__(self, settings, parent = None, filename=None, params=None):
        super(EditorGUI, self).__init__(parent)
        
        # options
        #self.skip       = 0
        self.perspective = [0,0,1000,1000]
        self.angle_degree    = 0
        self.focus = [333,666,333,666]
        self.croptop = 0
        self.cropbottom = 1000
        self.slitpos = 250
        if params is not None:
            print(params)
            self.angle_degree = params["rotate"]
            if params["perspective"] is not None:
                self.perspective     = params["perspective"]
            self.focus        = params["focus"]
            self.slitpos      = params["slitpos"]
            self.croptop, self.cropbottom = params["crop"]
            #self.skip         = params["skip"] #no use
            filename          = params["filename"]
        #private
        self.preview_size = 500
        self.frame        = 0
        self.settings = settings
        #make the threaded loader
        self.thread = QThread()
        self.thread.start()
        self.lastupdatethumbs = 0 #from epoch
        
        self.asyncimageloader = AsyncImageLoader(filename=filename, size=self.preview_size)
        self.asyncimageloader.moveToThread(self.thread)
        self.thread_invoker.connect(self.asyncimageloader.task)
        self.thread_invoker.emit()
        #self.destroyed.connect(self.stop_thread)  #does not work
        self.asyncimageloader.frameIncreased.connect(self.updateTimeLine)

        #close on quit
        #http://stackoverflow.com/questions/27420338/how-to-clear-child-window-reference-stored-in-parent-application-when-child-wind
        #self.setAttribute(Qt.WA_DeleteOnClose)
        layout = self.make_layout()
        self.imageselector2 = ImageSelector2()
        self.imageselector2.slider.valueChanged.connect(self.frameChanged)
        imageselector_layout = QHBoxLayout()
        imageselector_layout.addWidget(self.imageselector2)
        imageselector_gbox = QGroupBox(self.tr('1. Seek the first video frame'))
        imageselector_gbox.setLayout(imageselector_layout)
        glayout = QVBoxLayout()
        glayout.addWidget(imageselector_gbox)
        glayout.addLayout(layout)
        self.setLayout(glayout)
        self.setWindowTitle("Editor")
        self.show_snapshots()



    def thumbtransformer(self, cv2image):
        rotated,warped,cropped = self.transform.process_image(cv2image)
        h,w = cropped.shape[0:2]
        thumbh = 100
        thumbw = 50# w*thumbh/h
        thumb = cv2.resize(cropped,(thumbw,thumbh),interpolation = cv2.INTER_CUBIC)
        return self.cv2toQImage(thumb)
        
    def updateTimeLine(self, cv2thumbs):
        #count time and limit update
        now = time.time()
        if now - self.lastupdatethumbs < 0.2:
            return
        #transformation filter
        self.imageselector2.imagebar.setTransformer(self.thumbtransformer)
        self.imageselector2.setThumbs(cv2thumbs)
        self.lastupdatethumbs = time.time()
        
    def make_layout(self):
        # layout
        layout = QHBoxLayout()
        
        #second left panel for image rotation
        rotation_layout = QHBoxLayout()
        self.btn = QPushButton(self.tr("-90"))
        self.btn.clicked.connect(self.angle_sub90)
        rotation_layout.addWidget(self.btn)
        self.btn = QPushButton(self.tr("-1"))
        self.btn.clicked.connect(self.angle_dec)
        rotation_layout.addWidget(self.btn)
        rotation_layout.addWidget(QLabel(self.tr('rotation')))
        self.angle_label = QLabel("0 "+self.tr("degrees"))
        rotation_layout.addWidget(self.angle_label)
        self.btn = QPushButton(self.tr("+1"))
        self.btn.clicked.connect(self.angle_inc)
        rotation_layout.addWidget(self.btn)
        self.btn = QPushButton(self.tr("+90"))
        self.btn.clicked.connect(self.angle_add90)
        rotation_layout.addWidget(self.btn)

        #
        crop_layout = QVBoxLayout()
        self.croptop_slider = QSlider(Qt.Vertical)  # スライダの向き
        self.croptop_slider.setRange(0, 1000)  # スライダの範囲
        self.croptop_slider.setValue(1000)  # 初期値
        self.croptop_slider.valueChanged.connect(self.croptop_slider_on_draw)
        self.croptop_slider.setMinimumHeight(240)
        #print(self.croptop_slider.size())
        crop_layout.addWidget(self.croptop_slider)
        crop_layout.setAlignment(self.croptop_slider, Qt.AlignTop)

        self.cropbottom_slider = QSlider(Qt.Vertical)  # スライダの向き
        self.cropbottom_slider.setRange(0, 1000)  # スライダの範囲
        self.cropbottom_slider.setValue(0)  # 初期値 499 is top
        self.cropbottom_slider.valueChanged.connect(self.cropbottom_slider_on_draw)
        self.cropbottom_slider.setMinimumHeight(240)
        crop_layout.addWidget(self.cropbottom_slider)
        crop_layout.setAlignment(self.cropbottom_slider, Qt.AlignBottom)

        
        perspective_left_layout = QVBoxLayout()
        self.sliderTL = QSlider(Qt.Vertical)  # スライダの向き
        self.sliderTL.setRange(0, 1000)  # スライダの範囲
        self.sliderTL.setValue(1000)  # 初期値
        #sizepolicy = QSizePolicy()
        #sizepolicy.setVerticalPolicy(QSizePolicy.Maximum)
        #self.sliderTL.setSizePolicy(sizepolicy)
        self.sliderTL.valueChanged.connect(self.sliderTL_on_draw)
        self.sliderTL.setMinimumHeight(240)
        perspective_left_layout.addWidget(self.sliderTL)
        perspective_left_layout.setAlignment(self.sliderTL, Qt.AlignTop)

        self.sliderBL = QSlider(Qt.Vertical)  # スライダの向き
        self.sliderBL.setRange(0, 1000)  # スライダの範囲
        self.sliderBL.setValue(0)  # 初期値 499 is top
        self.sliderBL.valueChanged.connect(self.sliderBL_on_draw)
        self.sliderBL.setMinimumHeight(240)
        perspective_left_layout.addWidget(self.sliderBL)
        perspective_left_layout.setAlignment(self.sliderBL, Qt.AlignBottom)
        
        perspective_right_layout = QVBoxLayout()
        self.sliderTR = QSlider(Qt.Vertical)  # スライダの向き
        self.sliderTR.setRange(0, 1000)  # スライダの範囲
        self.sliderTR.setValue(1000)  # 初期値
        self.sliderTR.valueChanged.connect(self.sliderTR_on_draw)
        self.sliderTR.setMinimumHeight(240)
        perspective_right_layout.addWidget(self.sliderTR)
        perspective_right_layout.setAlignment(self.sliderTR, Qt.AlignTop)

        self.sliderBR = QSlider(Qt.Vertical)  # スライダの向き
        self.sliderBR.setRange(0, 1000)  # スライダの範囲
        self.sliderBR.setValue(0)  # 初期値 499 is top
        self.sliderBR.valueChanged.connect(self.sliderBR_on_draw)
        self.sliderBR.setMinimumHeight(240)
        perspective_right_layout.addWidget(self.sliderBR)
        perspective_right_layout.setAlignment(self.sliderBR, Qt.AlignBottom)
        
        
        
        raw_image_layout = QVBoxLayout()
        self.raw_image_pane = DrawableLabel()
        self.raw_image_pane.setAlignment(Qt.AlignCenter)
        self.raw_image_pane.setFixedWidth(self.preview_size)
        self.raw_image_pane.setFixedHeight(self.preview_size)
        #raw_image_layout.setAlignment(self.raw_image_pane, Qt.AlignCenter)
        raw_image_layout.addWidget(self.raw_image_pane)
        raw_image_layout.setAlignment(self.raw_image_pane, Qt.AlignHCenter)
        raw_image_layout.setAlignment(self.raw_image_pane, Qt.AlignTop)
        
        processed_edit_gbox_layout = QVBoxLayout()
        processed_edit_gbox = QGroupBox(self.tr('3. Motion Detection and Slit'))
        box = QVBoxLayout()
        processed_image_layout = QVBoxLayout()
        self.processed_pane = MyLabel(func=self.show_snapshots)
        self.processed_pane.setAlignment(Qt.AlignCenter)
        self.processed_pane.setFixedWidth(self.preview_size)
        self.processed_pane.setFixedHeight(self.preview_size)
        processed_image_layout.addWidget(self.processed_pane)
        processed_image_layout.setAlignment(self.processed_pane, Qt.AlignTop)

        hbox = QHBoxLayout()
        hbox.addLayout(processed_image_layout)
        hbox.addLayout(crop_layout)
        box.addLayout(hbox)
        processed_edit_gbox.setLayout(box)
        processed_edit_gbox_layout.addWidget(processed_edit_gbox)

        slit_slider_label = QLabel(self.tr('Slit position'))
        self.slit_slider = QSlider(Qt.Horizontal)  # スライダの向き
        self.slit_slider.setRange(-500, 500)  # スライダの範囲
        self.slit_slider.setValue(self.slitpos)  # 初期値
        #スライダの目盛りを両方に出す
        self.slit_slider.setTickPosition(QSlider.TicksBelow)
        self.slit_slider.valueChanged.connect(self.slit_slider_on_draw)
        slit_slider_layout = QHBoxLayout()
        slit_slider_layout.addWidget(slit_slider_label)
        slit_slider_layout.addWidget(self.slit_slider)
        box.addLayout(slit_slider_layout)
        box.setAlignment(slit_slider_layout, Qt.AlignTop)

        
        #combine panels
        topleft_layout = QHBoxLayout()
        topleft_layout.addLayout(perspective_left_layout)
        topleft_layout.addLayout(raw_image_layout)
        topleft_layout.addLayout(perspective_right_layout)
        left_layout = QVBoxLayout()
        left_layout.addLayout(topleft_layout)
        left_layout.addLayout(rotation_layout)
        left_layout.setAlignment(rotation_layout, Qt.AlignTop)
        raw_edit_gbox = QGroupBox(self.tr('2. Repair deformation'))
        raw_edit_gbox.setLayout(left_layout)
        raw_edit_gbox_layout = QVBoxLayout()
        raw_edit_gbox_layout.addWidget(raw_edit_gbox)
        layout.addLayout(raw_edit_gbox_layout)
        layout.addLayout(processed_edit_gbox_layout)
        return layout

    def stop_thread(self):
        self.asyncimageloader.stop()
        self.thread.quit()
        self.thread.wait()
        
    def angle_inc(self):
        self.angle_degree += 1
        self.angle_degree %= 360
        self.angle_label.setText("{0} ".format(self.angle_degree)+self.tr("degrees"))
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def angle_dec(self):
        self.angle_degree -= 1
        self.angle_degree %= 360
        self.angle_label.setText("{0} ".format(self.angle_degree)+self.tr("degrees"))
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def angle_add90(self):
        self.angle_degree += 90
        self.angle_degree %= 360
        self.angle_label.setText("{0} ".format(self.angle_degree)+self.tr("degrees"))
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def angle_sub90(self):
        self.angle_degree -= 90
        self.angle_degree %= 360
        self.angle_label.setText("{0} ".format(self.angle_degree)+self.tr("degrees"))
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def frameChanged(self, value):
        #if value < self.imageselector2.firstFrame:
        #    value = self.imageselector2.firstFrame
        self.frame = value
        self.show_snapshots()

    def sliderTL_on_draw(self):
        self.perspective[0] = 1000 - self.sliderTL.value()
        if self.perspective[2] - self.perspective[0] < 2:
            self.perspective[0] = self.perspective[2] - 2
            self.sliderTL.setValue(1000 - self.perspective[0])
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def sliderBL_on_draw(self):
        self.perspective[2] = 1000 - self.sliderBL.value()
        if self.perspective[2] - self.perspective[0] < 2:
            self.perspective[2] = self.perspective[0] + 2
            self.sliderBL.setValue(1000 - self.perspective[2])
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def sliderTR_on_draw(self):
        self.perspective[1] = 1000 - self.sliderTR.value()
        if self.perspective[3] - self.perspective[1] < 2:
            self.perspective[1] = self.perspective[3] - 2
            self.sliderTR.setValue(1000 - self.perspective[1])
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def sliderBR_on_draw(self):
        self.perspective[3] = 1000 - self.sliderBR.value()
        if self.perspective[3] - self.perspective[1] < 2:
            self.perspective[3] = self.perspective[1] + 2
            self.sliderBR.setValue(1000 - self.perspective[3])
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def cv2toQImage(self,cv2image):
        tmp = cv2image[:,:,0].copy()
        cv2image[:,:,0] = cv2image[:,:,2]
        cv2image[:,:,2] = tmp
        height,width = cv2image.shape[:2]
        return QImage(cv2image.data, width, height, width*3, QImage.Format_RGB888)
        

    def show_snapshots(self, region=None):
        """
        put the snapshots in the preview panes
        """
        if self.frame < 0:
            return
        image = self.asyncimageloader.snapshots[self.frame]
        self.transform = trainscanner.transformation(self.angle_degree, self.perspective, [self.croptop, self.cropbottom])
        rotated, warped, cropped = self.transform.process_first_image(image)
        self.put_cv2_image(rotated, self.raw_image_pane)
        if region is not None:
            print(region)
            #assume the QLabel size is square preview_size x preview_size
            top, left, bottom, right = region.top(), region.left(), region.bottom(), region.right()
            if top < 0:
                top = 0
            if left < 0:
                left = 0
            if right > self.preview_size:
                right = self.preview_size
            if bottom > self.preview_size:
                bottom = self.preview_size
            #and also assume that the cropped image is centered and sometimes shrinked.
            top    -= self.preview_size//2
            bottom -= self.preview_size//2
            left   -= self.preview_size//2
            right  -= self.preview_size//2
            #expected image size in the window
            height, width = cropped.shape[0:2]
            if height > width:
                if height > self.preview_size:
                    width = width * self.preview_size // height
                    height = self.preview_size
            else:
                if width > self.preview_size:
                    height = height * self.preview_size // width
                    width  = self.preview_size
            #indicate the region size relative to the image size
            #print(left,right,top,bottom)
            top    = top    * 1000 // height + 500
            bottom = bottom * 1000 // height + 500
            left   = left   * 1000 // width + 500
            right  = right  * 1000 // width + 500
            #print(left,right,top,bottom)
            if top < 0:
                top = 0
            if top > 1000:
                top = 1000
            if bottom < 0:
                bottom = 0
            if bottom > 1000:
                bottom = 1000
            if left < 0:
                left = 0
            if left > 1000:
                left = 1000
            if right < 0:
                right = 0
            if right > 1000:
                right = 1000
            self.focus = left,right,top,bottom
            #print(self.focus)
            
        self.put_cv2_image(cropped, self.processed_pane)
        

    def put_cv2_image(self, image, widget):
        height, width = image.shape[0:2]
        qImg = self.cv2toQImage(image)
        pixmap = QPixmap(qImg)
        if height > width:
            if height > self.preview_size:
                pixmap = pixmap.scaledToHeight(self.preview_size)
        else:
            if width > self.preview_size:
                pixmap = pixmap.scaledToWidth(self.preview_size)
        widget.setPixmap(pixmap)
        #give hints to DrawableLabel() and MyLabel()
        widget.perspective = self.perspective
        widget.focus = self.focus
        widget.slitpos = self.slitpos
        w = pixmap.width()
        h = pixmap.height()
        x = ( self.preview_size - w ) // 2
        y = ( self.preview_size - h ) // 2
        widget.geometry = x,y,w,h

        
    def slit_slider_on_draw(self):
        self.slitpos = self.slit_slider.value()
        self.show_snapshots()

    def croptop_slider_on_draw(self):
        self.croptop = 1000 - self.croptop_slider.value()
        if self.cropbottom - self.croptop < 2:
            self.croptop = self.cropbottom - 2
            self.croptop_slider.setValue(1000 - self.croptop)
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def cropbottom_slider_on_draw(self):
        self.cropbottom = 1000 - self.cropbottom_slider.value()
        if self.cropbottom - self.croptop < 2:
            self.cropbottom = self.croptop + 2
            self.cropbottom_slider.setValue(1000 - self.cropbottom)
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def closeEvent(self,event):
        self.settings.reset_input()
        self.stop_thread()
    #    self.asyncimageloader.stop()
            
    #This will be the trigger for the first rendering
    #def resizeEvent(self, event):
    #    self.asyncimageloader.render()


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

#import pkgutil

## def pyqt_set_trace():
##     '''Set a tracepoint in the Python debugger that works with Qt'''
##     from PyQt5.QtCore import pyqtRemoveInputHook
##     import pdb
##     import sys
##     pyqtRemoveInputHook()
##     # set up the debugger
##     debugger = pdb.Pdb()
##     debugger.reset()
##     # custom next to get outside of function scope
##     debugger.do_next(None) # run the next command
##     users_frame = sys._getframe().f_back # frame where the user invoked `pyqt_set_trace()`
##     debugger.interaction(users_frame, None)


def main():
    #pyqt_set_trace()
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
