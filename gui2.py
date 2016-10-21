#!/usr/bin/env python
#-*- coding: utf-8 -*-
import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import os
import cv2
import numpy as np
import math
import trainscanner

#ToDos:
#[] and thumbs
#edit focus area.
#Top and bottom crop

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
        self.slitwidth = 1.0
        self.identity = 2.0
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

        settings2_layout.addWidget(QLabel(self.tr('Trailing frames')), rows,0, Qt.AlignRight)
        
        self.trailing_slider_valuelabel = QLabel(str(self.trailing))
        settings2_layout.addWidget(self.trailing_slider_valuelabel, rows,1)

        settings2_layout.addWidget(QLabel(self.tr('Short')), rows, 2)
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

        
        #Example of a slider with a label ###################################
        #the slider is in a Hbox
        
        settings2_layout.addWidget(QLabel(self.tr('Slit mixing')), rows, 0, Qt.AlignRight)
        
        self.slitwidth_slider_valuelabel = QLabel(str(self.slitwidth))
        settings2_layout.addWidget(self.slitwidth_slider_valuelabel, rows, 1)
        
        settings2_layout.addWidget(QLabel(self.tr('Sharp')), rows, 2)
        self.slitwidth_slider = QSlider(Qt.Horizontal)  # スライダの向き
        self.slitwidth_slider.setRange(1, 30)  # スライダの範囲
        self.slitwidth_slider.setValue(10)  # 初期値
        #スライダの目盛りを両方に出す
        self.slitwidth_slider.setTickPosition(QSlider.TicksBelow)
        self.connect(self.slitwidth_slider, SIGNAL('valueChanged(int)'), self.slitwidth_slider_on_draw)
        settings2_layout.addWidget(self.slitwidth_slider, rows, 3)
        settings2_layout.addWidget(QLabel(self.tr('Diffuse')), rows, 4)

        rows += 1
        #####################################################################


        #Example of a slider with a label ###################################
        #the slider is in a Hbox

        settings2_layout.addWidget(QLabel(self.tr('Permit camera waggle')), rows, 0, Qt.AlignRight)
        
        self.antishake_slider_valuelabel = QLabel(str(self.antishake))
        settings2_layout.addWidget(self.antishake_slider_valuelabel, rows, 1)
        
        settings2_layout.addWidget(QLabel(self.tr('Small')), rows, 2)
        self.antishake_slider = QSlider(Qt.Horizontal)  # スライダの向き
        self.antishake_slider.setRange(1, 15)  # スライダの範囲
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
        #self.b2.toggled.connect(lambda:self.btnstate(self.b2))
        settings2_layout.addWidget(self.btn_zerodrift,rows, 1)
        rows += 1

        #Example of a checkbox and slider with a label
        #-i (identity)

        settings2_layout.addWidget(QLabel(self.tr('Skip identical frames')), rows, 0, Qt.AlignRight)

        #self.btn_skipident = QCheckBox(self.tr('Skip identical frames'))
        #self.b2.toggled.connect(lambda:self.btnstate(self.b2))
        #skipident_layout.addWidget(self.btn_skipident)
        
        
        self.skipident_valuelabel = QLabel(str(self.identity))
        settings2_layout.addWidget(self.skipident_valuelabel, rows, 1)
    
        settings2_layout.addWidget(QLabel(self.tr('Strict')), rows, 2)
        self.identthres_slider = QSlider(Qt.Horizontal)  # スライダの向き
        self.identthres_slider.setRange(1, 5)  # スライダの範囲
        self.identthres_slider.setValue(2)  # 初期値
        #スライダの目盛りを両方に出す
        self.identthres_slider.setTickPosition(QSlider.TicksBelow)
        self.connect(self.identthres_slider, SIGNAL('valueChanged(int)'), self.identthres_slider_on_draw)
        #the slider is in a Hbox
        settings2_layout.addWidget(self.identthres_slider, rows, 3)
        settings2_layout.addWidget(QLabel(self.tr('Loose')), rows, 4)
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
		
    def getfile(self):
        self.fname = QFileDialog.getOpenFileName(self, self.tr('Open file'), 
            "","Movie files (*.mov *.mp4)")
        #self.le.setPixmap(QPixmap(fname))
        #Load every 30 frames here for preview.
        self.le.setText(self.fname)
        self.fname = str(self.fname)
        #dir = os.path.dirname(self.fname)
        #base = os.path.basename(self.fname)
        #self.fname = "sample3.mov"
        self.editor = EditorGUI(self)
        self.editor.show()
        cap = cv2.VideoCapture(self.fname)
        count = 0
        while True:
            ret, frame = cap.read()
            count += 1
            #self.pbar.setValue(100 - 100 / count)
            if not ret:
                break
            h,w = frame.shape[0:2]
            self.editor.snapshots.append(frame)
            for i in range(29):
                ret = cap.grab()
                if not ret:
                    break
            if not ret:
                break
        #self.pbar.reset()
        self.editor.frame = 0
        self.editor.show_snapshots()
        


    def trailing_slider_on_draw(self):
        self.trailing = self.trailing_slider.value()
        self.trailing_slider_valuelabel.setText(str(self.trailing))


    def slitwidth_slider_on_draw(self):
        self.slitwidth = self.slitwidth_slider.value() / 10.0
        self.slitwidth_slider_valuelabel.setText(str(self.slitwidth))


    def antishake_slider_on_draw(self):
        self.antishake = self.antishake_slider.value() / 10.0
        self.antishake_slider_valuelabel.setText(str(self.antishake))


    def identthres_slider_on_draw(self):
        self.identity = self.identthres_slider.value()
        self.skipident_valuelabel.setText(str(self.identity))


    def start_process(self):
        pass1_options = " -r {0}".format(self.editor.angle_degree)
        pass1_options += " -t {0}".format(self.trailing)
        pass1_options += " -a {0}".format(self.antishake)
        pass1_options += " -p {0}".format(",".join([str(x) for x in self.editor.pers]))
        pass1_options += " -f {0}".format(",".join([str(x) for x in self.editor.focus]))
        pass1_options += " -c {0},{1}".format(self.editor.croptop,self.editor.cropbottom)
        if self.btn_zerodrift.isChecked():
            pass1_options += " -z"
        #if self.btn_skipident.isChecked():
        pass1_options += " -i {0}".format(self.identity)
        stitch_options = " -s {0}".format(self.editor.slitpos)
        stitch_options += " -w {0}".format(self.slitwidth)
            
        file_name = self.fname
        if self.btn_finish_stitch.isChecked():
            #print("./pass1.py {0} {1} >  {1}.pass1.log".format(pass1_options, file_name))
            os.system("./pass1.py {0} {1} >  {1}.pass1.log".format(pass1_options, file_name))
            log = open("{0}.pass1.log".format(file_name))
            while True:
                line = log.readline()
                #print(line)
                if line[0] == "@":
                    break
            canvas_dimen = [int(x) for x in line.split()[1:]]
            stitch_options += " -C {0},{1},{2},{3}".format(*canvas_dimen)
            os.system("./stitch_gui.py {0} < {1}.pass1.log".format(stitch_options, file_name))
        file_name += ".png"
        if self.btn_finish_perf.isChecked():
            os.system("./film.py {0}".format(file_name))
            file_name += ".film.png"
        if self.btn_finish_helix.isChecked():
            os.system("./helix.py {0}".format(file_name))
            file_name += ".helix.jpg"

#https://www.tutorialspoint.com/pyqt/pyqt_qfiledialog_widget.htm
class EditorGUI(QWidget):
    def __init__(self, settings, parent = None):
        super(EditorGUI, self).__init__(parent)

        # options
        #private
        self.settings = settings
        self.angle_degree    = 0
        self.snapshots = []
        self.frame     = -1
        self.preview_size = 450
        self.pers = [0,0,1000,1000]
        self.focus = [333,666,333,666]
        self.slitpos = 250
        self.croptop = 0
        self.cropbottom = 1000
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
        nextprev_layout = QHBoxLayout()
        self.btn = QPushButton("<<")
        self.btn.clicked.connect(self.prevframe)
        nextprev_layout.addWidget(self.btn)
        self.btn = QPushButton(">>")
        self.btn.clicked.connect(self.nextframe)
        nextprev_layout.addWidget(self.btn)

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
        self.sliderTL.setRange(0, 499)  # スライダの範囲
        self.sliderTL.setValue(499)  # 初期値
        #sizepolicy = QSizePolicy()
        #sizepolicy.setVerticalPolicy(QSizePolicy.Maximum)
        #self.sliderTL.setSizePolicy(sizepolicy)
        self.connect(self.sliderTL, SIGNAL('valueChanged(int)'), self.sliderTL_on_draw)
        pers_left_layout.addWidget(self.sliderTL)
        pers_left_layout.setAlignment(self.sliderTL, Qt.AlignTop)

        self.sliderBL = QSlider(Qt.Vertical)  # スライダの向き
        self.sliderBL.setRange(0, 499)  # スライダの範囲
        self.sliderBL.setValue(0)  # 初期値 499 is top
        self.connect(self.sliderBL, SIGNAL('valueChanged(int)'), self.sliderBL_on_draw)
        pers_left_layout.addWidget(self.sliderBL)
        pers_left_layout.setAlignment(self.sliderBL, Qt.AlignBottom)
        
        pers_right_layout = QVBoxLayout()
        self.sliderTR = QSlider(Qt.Vertical)  # スライダの向き
        self.sliderTR.setRange(0, 499)  # スライダの範囲
        self.sliderTR.setValue(499)  # 初期値
        self.connect(self.sliderTR, SIGNAL('valueChanged(int)'), self.sliderTR_on_draw)
        pers_right_layout.addWidget(self.sliderTR)
        pers_right_layout.setAlignment(self.sliderTR, Qt.AlignTop)

        self.sliderBR = QSlider(Qt.Vertical)  # スライダの向き
        self.sliderBR.setRange(0, 499)  # スライダの範囲
        self.sliderBR.setValue(0)  # 初期値 499 is top
        self.connect(self.sliderBR, SIGNAL('valueChanged(int)'), self.sliderBR_on_draw)
        pers_right_layout.addWidget(self.sliderBR)
        pers_right_layout.setAlignment(self.sliderBR, Qt.AlignBottom)
        
        
        
        raw_image_layout = QVBoxLayout()
        self.raw_image_pane = QLabel()
        self.raw_image_pane.setAlignment(Qt.AlignCenter)
        self.raw_image_pane.setFixedWidth(self.preview_size)
        self.raw_image_pane.setFixedHeight(self.preview_size)
        #raw_image_layout.setAlignment(self.raw_image_pane, Qt.AlignCenter)
        raw_image_layout.addWidget(self.raw_image_pane)
        raw_image_layout.setAlignment(self.raw_image_pane, Qt.AlignHCenter)
        raw_image_layout.setAlignment(self.raw_image_pane, Qt.AlignTop)
        
        processed_edit_gbox_layout = QVBoxLayout()
        processed_edit_gbox = QGroupBox(self.tr('2. Motion Detection and Slit'))
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
        left_layout.addLayout(nextprev_layout)
        left_layout.setAlignment(nextprev_layout, Qt.AlignTop)
        left_layout.addLayout(rotation_layout)
        left_layout.setAlignment(rotation_layout, Qt.AlignTop)
        raw_edit_gbox = QGroupBox(self.tr('1. Repair deformation'))
        raw_edit_gbox.setLayout(left_layout)
        raw_edit_gbox_layout = QVBoxLayout()
        raw_edit_gbox_layout.addWidget(raw_edit_gbox)
        layout.addLayout(raw_edit_gbox_layout)
        layout.addLayout(processed_edit_gbox_layout)
        self.setLayout(layout)
        self.setWindowTitle("Editor")
		

    def angle_inc(self):
        self.angle_degree += 1
        self.angle_degree %= 360
        self.angle_label.setText(str(self.angle_degree))
        self.show_snapshots()

    def angle_dec(self):
        self.angle_degree -= 1
        self.angle_degree %= 360
        self.angle_label.setText(str(self.angle_degree))
        self.show_snapshots()

    def angle_add90(self):
        self.angle_degree += 90
        self.angle_degree %= 360
        self.angle_label.setText(str(self.angle_degree))
        self.show_snapshots()

    def angle_sub90(self):
        self.angle_degree -= 90
        self.angle_degree %= 360
        self.angle_label.setText(str(self.angle_degree))
        self.show_snapshots()

    def prevframe(self):
        self.frame -= 1
        self.frame %= len(self.snapshots)
        self.show_snapshots()

    def nextframe(self):
        self.frame += 1
        self.frame %= len(self.snapshots)
        self.show_snapshots()

    def sliderTL_on_draw(self):
        self.pers[0] = 499 - self.sliderTL.value()
        self.show_snapshots()

    def sliderBL_on_draw(self):
        self.pers[2] = 999 - self.sliderBL.value()
        self.show_snapshots()

    def sliderTR_on_draw(self):
        self.pers[1] = 499 - self.sliderTR.value()
        self.show_snapshots()

    def sliderBR_on_draw(self):
        self.pers[3] = 999 - self.sliderBR.value()
        self.show_snapshots()

    def cv2toQImage(self,image):
        tmp = np.zeros_like(image[:,:,0])
        tmp = image[:,:,0].copy()
        image[:,:,0] = image[:,:,2]
        image[:,:,2] = tmp
        
    def show_snapshots(self, region=None):
        """
        put the snapshots in the preview panes
        """
        if self.frame < 0:
            return
        image = self.snapshots[self.frame]
        h,w = image.shape[0:2]
        #Left image: unwarped
        R, width,height = trainscanner.rotate_matrix(-self.angle_degree*math.pi/180,w,h)
        image = cv2.warpAffine(image, R, (width,height))
        processed = image.copy()
        trainscanner.draw_guide(image, self.pers, gauge=False)  #second is pers
        #color order is different between cv2 and pyqt
        self.put_cv2_image(image, self.raw_image_pane)
        #Right image: warped
        M = trainscanner.warp_matrix(self.pers,width,height)
        processed = cv2.warpPerspective(processed,M,(width,height))
        processed = processed[self.croptop*height/1000:self.cropbottom*height/1000, :, :]
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
            height, width = processed.shape[0:2]
            if height > width:
                if height > self.preview_size:
                    width = width * self.preview_size / height
                    height = self.preview_size
            else:
                if width > self.preview_size:
                    height = height * self.preview_size / width
                    width  = self.preview_size
            #indicate the region size relative to the image size
            print(left,right,top,bottom)
            top    = top    * 1000 / height + 500
            bottom = bottom * 1000 / height + 500
            left   = left   * 1000 / width + 500
            right  = right  * 1000 / width + 500
            print(left,right,top,bottom)
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
            print(self.focus)
            
        trainscanner.draw_focus_area(processed, self.focus)
        draw_slitpos(processed, self.slitpos)
        self.put_cv2_image(processed, self.processed_pane)
        #self.resize(self.sizeHint())
        

    def put_cv2_image(self, image, widget):
        height, width = image.shape[0:2]
        self.cv2toQImage(image) #This breaks the image
        qImg = QImage(image.data, width, height, width*3, QImage.Format_RGB888)
        pixmap = QPixmap(qImg)
        if height > width:
            if height > self.preview_size:
                widget.setPixmap(pixmap.scaledToHeight(self.preview_size))
                return
        else:
            if width > self.preview_size:
                widget.setPixmap(pixmap.scaledToWidth(self.preview_size))
                return
        widget.setPixmap(pixmap)

    def slit_slider_on_draw(self):
        self.slitpos = self.slit_slider.value()
        self.show_snapshots()

    def croptop_slider_on_draw(self):
        self.croptop = 1000 - self.croptop_slider.value()
        self.show_snapshots()

    def cropbottom_slider_on_draw(self):
        self.cropbottom = 1000 - self.cropbottom_slider.value()
        self.show_snapshots()

            
        
def main():
    app = QApplication(sys.argv)
    translator = QTranslator(app)
    print translator.load("gui2_ja")
    app.installTranslator(translator)
    se = SettingsGUI()
    se.show()
    sys.exit(app.exec_())
	
if __name__ == '__main__':
    main()
