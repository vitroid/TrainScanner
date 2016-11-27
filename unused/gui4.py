#!/usr/bin/env python
#-*- coding: utf-8 -*-

import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import os
import subprocess
import cv2
import numpy as np
import math
import trainscanner
from imageselector import ImageSelector
import time
    

class AsyncImageLoader(QObject):
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
        self.count = 1
        self.snapshots = [frame]


    def stop(self):
        self.isRunning = False
        #trash images
        self.snapshots = []


    def task(self):
        if not self.isRunning:
            self.isRunning = True
            
        while self.isRunning:
            ret, frame = self.cap.read()
            if not ret:
                break
            if self.count % 10 == 0:  #load every 10 frames; it might be too many.
                if self.size:
                    frame = trainscanner.fit_to_square(frame, self.size)
                self.snapshots.append(frame)
                #print(len(self.snapshots))
                #these are for the preview, so we can shrink it.
                #We want to emit the snapshots itself. Can we?
                self.frameIncreased.emit(self.snapshots)
            self.count += 1

        #print("Finished")


class DrawableLabel(QLabel):
    def __init__(self, parent=None):
        super(QLabel, self).__init__(parent)
        self.pers = (0,0,1000,1000)
        self.geometry = (0,0,1000,1000)

    def paintEvent(self, event):
        QLabel.paintEvent(self, event)
        painter = QPainter(self)
        painter.setPen(Qt.red)
        #painter.setBrush(Qt.yellow)
        #painter.drawRect(10, 10, 100, 100)
        x,y,w,h = self.geometry
        painter.drawLine(x,y+self.pers[0]*h/1000,x+w,y+self.pers[1]*h/1000)
        painter.drawLine(x,y+self.pers[2]*h/1000,x+w,y+self.pers[3]*h/1000)


def draw_slitpos(f, slitpos):
    h, w = f.shape[0:2]
    slitpos1 = (slitpos+500)*w/1000
    slitpos2 = (500-slitpos)*w/1000
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
        painter.drawLine(x+w/2-self.slitpos*w/1000,y,x+w/2-self.slitpos*w/1000,y+h)
        painter.drawLine(x+w/2+self.slitpos*w/1000,y,x+w/2+self.slitpos*w/1000,y+h)
        painter.setPen(Qt.green)
        painter.drawRect(x+w*self.focus[0]/1000,y+h*self.focus[2]/1000,w*(self.focus[1]-self.focus[0])/1000,h*(self.focus[3]-self.focus[2])/1000)
        
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
        self.slitwidth_slider.setRange(5, 100)  # スライダの範囲
        self.slitwidth_slider.setValue(self.slitwidth)  # 初期値
        #スライダの目盛りを両方に出す
        self.slitwidth_slider.setTickPosition(QSlider.TicksBelow)
        self.connect(self.slitwidth_slider, SIGNAL('valueChanged(int)'), self.slitwidth_slider_on_draw)
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
        self.connect(self.antishake_slider, SIGNAL('valueChanged(int)'), self.antishake_slider_on_draw)
        settings2_layout.addWidget(self.antishake_slider, rows, 3)
        settings2_layout.addWidget(QLabel(self.tr('Large')), rows, 4)

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
        # settings2_layout.addWidget(QLabel(self.tr('Limit maximum acceleration')), rows, 0, Qt.AlignRight)
        # self.btn_accel = QCheckBox()
        # self.btn_accel.setCheckState(Qt.Checked)
        # settings2_layout.addWidget(self.btn_accel,rows, 1)
        # rows += 1
        # #####################################################################
        # #Example of a slider with a label ###################################
        # #the slider is in a Hbox

        # #settings2_layout.addWidget(QLabel(self.tr('Permit camera waggle')), rows, 0, Qt.AlignRight)
        
        # self.accel_slider_valuelabel = QLabel(str(self.accel))
        # settings2_layout.addWidget(self.accel_slider_valuelabel, rows, 1)
        
        # settings2_layout.addWidget(QLabel(self.tr('Smooth')), rows, 2)
        # self.accel_slider = QSlider(Qt.Horizontal)  # スライダの向き
        # self.accel_slider.setRange(1, 5)  # スライダの範囲
        # self.accel_slider.setValue(1)  # 初期値
        # #スライダの目盛りを両方に出す
        # self.accel_slider.setTickPosition(QSlider.TicksBelow)
        # self.connect(self.accel_slider, SIGNAL('valueChanged(int)'), self.accel_slider_on_draw)
        # settings2_layout.addWidget(self.accel_slider, rows, 3)
        # settings2_layout.addWidget(QLabel(self.tr('Jerky')), rows, 4)
        # self.btn_accel.toggled.connect(self.btn_accel_toggle)

        # rows += 1
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
        self.connect(self.trailing_slider, SIGNAL('valueChanged(int)'), self.trailing_slider_on_draw)
        settings2_layout.addWidget(self.trailing_slider, rows, 3)
        settings2_layout.addWidget(QLabel(self.tr('Long')), rows, 4)

        rows += 1
        #####################################################################


        gbox_settings.setLayout(settings2_layout)

        left_layout.addWidget(gbox_settings)

        #Left panel, lower pane: finish
        finish_layout_gbox = QGroupBox(self.tr('Finish'))
        finish_layout = QVBoxLayout()
        #https://www.tutorialspoint.com/pyqt/pyqt_qcheckbox_widget.htm
        self.btn_finish_stitch = QCheckBox(self.tr('Stitch to a long image strip'))
        self.btn_finish_stitch.setCheckState(Qt.Checked)
        #self.b2.toggled.connect(lambda:self.btnstate(self.b2))
        finish_layout.addWidget(self.btn_finish_stitch)
        self.btn_finish_perf = QCheckBox(self.tr('Add the film perforations'))
        #self.b2.toggled.connect(lambda:self.btnstate(self.b2))
        finish_layout.addWidget(self.btn_finish_perf)
        self.btn_finish_helix = QCheckBox(self.tr('Make a helical image'))
        #self.b2.toggled.connect(lambda:self.btnstate(self.b2))
        finish_layout.addWidget(self.btn_finish_helix)
        self.start_button = QPushButton(self.tr('Start'),self)
        self.connect(self.start_button,SIGNAL('clicked()'),self.start_process)
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
        if self.editor is not None:
            self.editor.close()
        self.filename = QFileDialog.getOpenFileName(self, self.tr('Open file'), 
            "","Movie files (*.mov *.mp4 *.mts)")
        if self.filename == "": # or if the file cannot be opened,
            return
        #self.le.setPixmap(QPixmap(filename))
        #Load every 30 frames here for preview.
        self.le.setText(self.filename)
        self.filename = str(self.filename)
        #dir = os.path.dirname(self.filename)
        #base = os.path.basename(self.filename)
        #self.filename = "sample3.mov"
        self.editor = EditorGUI(self, filename=self.filename)
        self.editor.show()
        


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


##    def accel_slider_on_draw(self):
##        self.accel = self.accel_slider.value()
##        self.accel_slider_valuelabel.setText(str(self.accel))


##    def identthres_slider_on_draw(self):
##        self.identity = self.identthres_slider.value()
##        self.skipident_valuelabel.setText(str(self.identity))


    def start_process(self):
        if self.editor is None:
            return
        ###self.sefDisabled(True)
        pass1_options = " -r {0}".format(self.editor.angle_degree)
        pass1_options += " -t {0}".format(self.trailing)
        pass1_options += " -a {0}".format(self.antishake)
        pass1_options += " -S {0}".format(int(len(self.editor.asyncimageloader.snapshots)*10*self.editor.imageselector.trimmed))
        pass1_options += " -p {0}".format(",".join([str(x) for x in self.editor.pers]))
        pass1_options += " -f {0}".format(",".join([str(x) for x in self.editor.focus]))
        pass1_options += " -c {0},{1}".format(self.editor.croptop,self.editor.cropbottom)
        if self.btn_zerodrift.isChecked():
            pass1_options += " -z"
        if self.btn_stall.isChecked():
            pass1_options += " -x"
##        if self.btn_accel.isChecked():
##            pass1_options += " -m {0}".format(self.accel)
        pass1_options += " -m 1"
        #if self.btn_skipident.isChecked():
##        pass1_options += " -i {0}".format(self.identity)
        #pass1_options += " -e 5"   ##for debug
        stitch_options = " -s {0}".format(self.editor.slitpos)
        stitch_options += " -w {0}".format(self.slitwidth/100.0)
            
        file_name = self.filename
        cmd = []
        if self.btn_finish_stitch.isChecked():
            print("./pass1_gui.py {0} '{1}' >  '{1}.pass1.log'".format(pass1_options, file_name))
            ret = os.system("./pass1_gui.py {0} '{1}' >  '{1}'.pass1.log".format(pass1_options, file_name))
            if ret:  #error or terminated
                return
            log = open("{0}.pass1.log".format(file_name))
            while True:
                line = log.readline()
                #print(line)
                if line[0] == "@":
                    break
            canvas_dimen = [int(x) for x in line.split()[1:]]
            stitch_options += " -C {0},{1},{2},{3}".format(*canvas_dimen)
            cmd.append("./stitch_gui.py {0} < '{1}'.pass1.log".format(stitch_options, file_name))
        file_name += ".png"
        if self.btn_finish_perf.isChecked():
            cmd.append("./film.py '{0}'".format(file_name))
            file_name += ".film.png"
        if self.btn_finish_helix.isChecked():
            cmd.append("./helix.py '{0}'".format(file_name))
            file_name += ".helix.jpg"
        print(" && ".join(cmd))
        subprocess.Popen(" && ".join(cmd), shell=True)
        ###self.sefDisabled(False)
        

    def closeEvent(self,event):
        if self.editor is not None:
            self.editor.close()

#https://www.tutorialspoint.com/pyqt/pyqt_qfiledialog_widget.htm
class EditorGUI(QWidget):
    thread_invoker = pyqtSignal()

    def __init__(self, settings, parent = None, filename=None):
        super(EditorGUI, self).__init__(parent)
        

        # options
        #private
        self.settings = settings
        self.angle_degree    = 0
        #self.snapshots = []
        self.frame     = 0
        self.preview_size = 500
        self.pers = [0,0,1000,1000]
        self.focus = [333,666,333,666]
        self.slitpos = 250
        self.croptop = 0
        self.cropbottom = 1000
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
        self.imageselector = ImageSelector()
        self.imageselector.connect(self.imageselector.slider, SIGNAL('valueChanged(int)'), self.frameChanged)
        imageselector_layout = QHBoxLayout()
        imageselector_layout.addWidget(self.imageselector)
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
        self.imageselector.imagebar.setTransformer(self.thumbtransformer)
        self.imageselector.setThumbs(cv2thumbs)
        self.lastupdatethumbs = time.time()
        
    def make_layout(self):
        # layout
        layout = QHBoxLayout()
        
        #second left panel for image rotation
        rotation_layout = QHBoxLayout()
        self.btn = QPushButton("-90")
        self.btn.clicked.connect(self.angle_sub90)
        rotation_layout.addWidget(self.btn)
        self.btn = QPushButton("-1")
        self.btn.clicked.connect(self.angle_dec)
        rotation_layout.addWidget(self.btn)
        rotation_layout.addWidget(QLabel(self.tr('rotation')))
        self.angle_label = QLabel("0")
        rotation_layout.addWidget(self.angle_label)
        self.btn = QPushButton("+1")
        self.btn.clicked.connect(self.angle_inc)
        rotation_layout.addWidget(self.btn)
        self.btn = QPushButton("+90")
        self.btn.clicked.connect(self.angle_add90)
        rotation_layout.addWidget(self.btn)

        #
        crop_layout = QVBoxLayout()
        self.croptop_slider = QSlider(Qt.Vertical)  # スライダの向き
        self.croptop_slider.setRange(0, 1000)  # スライダの範囲
        self.croptop_slider.setValue(1000)  # 初期値
        self.connect(self.croptop_slider, SIGNAL('valueChanged(int)'), self.croptop_slider_on_draw)
        crop_layout.addWidget(self.croptop_slider)
        crop_layout.setAlignment(self.croptop_slider, Qt.AlignTop)

        self.cropbottom_slider = QSlider(Qt.Vertical)  # スライダの向き
        self.cropbottom_slider.setRange(0, 1000)  # スライダの範囲
        self.cropbottom_slider.setValue(0)  # 初期値 499 is top
        self.connect(self.cropbottom_slider, SIGNAL('valueChanged(int)'), self.cropbottom_slider_on_draw)
        crop_layout.addWidget(self.cropbottom_slider)
        crop_layout.setAlignment(self.cropbottom_slider, Qt.AlignBottom)

        
        pers_left_layout = QVBoxLayout()
        self.sliderTL = QSlider(Qt.Vertical)  # スライダの向き
        self.sliderTL.setRange(0, 1000)  # スライダの範囲
        self.sliderTL.setValue(1000)  # 初期値
        #sizepolicy = QSizePolicy()
        #sizepolicy.setVerticalPolicy(QSizePolicy.Maximum)
        #self.sliderTL.setSizePolicy(sizepolicy)
        self.connect(self.sliderTL, SIGNAL('valueChanged(int)'), self.sliderTL_on_draw)
        pers_left_layout.addWidget(self.sliderTL)
        pers_left_layout.setAlignment(self.sliderTL, Qt.AlignTop)

        self.sliderBL = QSlider(Qt.Vertical)  # スライダの向き
        self.sliderBL.setRange(0, 1000)  # スライダの範囲
        self.sliderBL.setValue(0)  # 初期値 499 is top
        self.connect(self.sliderBL, SIGNAL('valueChanged(int)'), self.sliderBL_on_draw)
        pers_left_layout.addWidget(self.sliderBL)
        pers_left_layout.setAlignment(self.sliderBL, Qt.AlignBottom)
        
        pers_right_layout = QVBoxLayout()
        self.sliderTR = QSlider(Qt.Vertical)  # スライダの向き
        self.sliderTR.setRange(0, 1000)  # スライダの範囲
        self.sliderTR.setValue(1000)  # 初期値
        self.connect(self.sliderTR, SIGNAL('valueChanged(int)'), self.sliderTR_on_draw)
        pers_right_layout.addWidget(self.sliderTR)
        pers_right_layout.setAlignment(self.sliderTR, Qt.AlignTop)

        self.sliderBR = QSlider(Qt.Vertical)  # スライダの向き
        self.sliderBR.setRange(0, 1000)  # スライダの範囲
        self.sliderBR.setValue(0)  # 初期値 499 is top
        self.connect(self.sliderBR, SIGNAL('valueChanged(int)'), self.sliderBR_on_draw)
        pers_right_layout.addWidget(self.sliderBR)
        pers_right_layout.setAlignment(self.sliderBR, Qt.AlignBottom)
        
        
        
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
        self.slit_slider.setRange(0, 500)  # スライダの範囲
        self.slit_slider.setValue(self.slitpos)  # 初期値
        #スライダの目盛りを両方に出す
        self.slit_slider.setTickPosition(QSlider.TicksBelow)
        self.connect(self.slit_slider, SIGNAL('valueChanged(int)'), self.slit_slider_on_draw)
        slit_slider_layout = QHBoxLayout()
        slit_slider_layout.addWidget(slit_slider_label)
        slit_slider_layout.addWidget(self.slit_slider)
        box.addLayout(slit_slider_layout)
        box.setAlignment(slit_slider_layout, Qt.AlignTop)

        
        #combine panels
        topleft_layout = QHBoxLayout()
        topleft_layout.addLayout(pers_left_layout)
        topleft_layout.addLayout(raw_image_layout)
        topleft_layout.addLayout(pers_right_layout)
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
        if value < self.imageselector.firstFrame:
            value = self.imageselector.firstFrame
        self.frame = value
        self.show_snapshots()

    def sliderTL_on_draw(self):
        self.pers[0] = 1000 - self.sliderTL.value()
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def sliderBL_on_draw(self):
        self.pers[2] = 1000 - self.sliderBL.value()
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def sliderTR_on_draw(self):
        self.pers[1] = 1000 - self.sliderTR.value()
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def sliderBR_on_draw(self):
        self.pers[3] = 1000 - self.sliderBR.value()
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
        self.transform = trainscanner.transformation(self.angle_degree, self.pers, [self.croptop, self.cropbottom])
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
            top    -= self.preview_size/2
            bottom -= self.preview_size/2
            left   -= self.preview_size/2
            right  -= self.preview_size/2
            #expected image size in the window
            height, width = cropped.shape[0:2]
            if height > width:
                if height > self.preview_size:
                    width = width * self.preview_size / height
                    height = self.preview_size
            else:
                if width > self.preview_size:
                    height = height * self.preview_size / width
                    width  = self.preview_size
            #indicate the region size relative to the image size
            #print(left,right,top,bottom)
            top    = top    * 1000 / height + 500
            bottom = bottom * 1000 / height + 500
            left   = left   * 1000 / width + 500
            right  = right  * 1000 / width + 500
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
        widget.pers = self.pers
        widget.focus = self.focus
        widget.slitpos = self.slitpos
        w = pixmap.width()
        h = pixmap.height()
        x = ( self.preview_size - w ) / 2
        y = ( self.preview_size - h ) / 2
        widget.geometry = x,y,w,h

        
    def slit_slider_on_draw(self):
        self.slitpos = self.slit_slider.value()
        self.show_snapshots()

    def croptop_slider_on_draw(self):
        self.croptop = 1000 - self.croptop_slider.value()
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def cropbottom_slider_on_draw(self):
        self.cropbottom = 1000 - self.cropbottom_slider.value()
        self.updateTimeLine(self.asyncimageloader.snapshots)
        self.show_snapshots()

    def closeEvent(self,event):
        self.settings.reset_input()
        self.stop_thread()
    #    self.asyncimageloader.stop()
            
    #This will be the trigger for the first rendering
    #def resizeEvent(self, event):
    #    self.asyncimageloader.render()

        
def main():
    app = QApplication(sys.argv)
    translator = QTranslator(app)
    translator.load("gui4_ja")
    app.installTranslator(translator)
    se = SettingsGUI()
    se.show()
    se.raise_()
    sys.exit(app.exec_())
	
if __name__ == '__main__':
    main()
