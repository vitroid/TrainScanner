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


#https://www.tutorialspoint.com/pyqt/pyqt_qfiledialog_widget.htm
class SettingsGUI(QWidget):
    def __init__(self, parent = None):
        super(SettingsGUI, self).__init__(parent)

        # options
        self.trailing = 10
        self.editor = None
        #private
        # layout
        layout = QHBoxLayout()
        
        #leftmost panel for specifying options
        left_layout = QVBoxLayout()
        self.btn = QPushButton("Open a movie")
        self.btn.clicked.connect(self.getfile)
        left_layout.addWidget(self.btn)
    
        self.le = QLabel("(File name appears here)")
        left_layout.addWidget(self.le)
        
        #self.pbar = QProgressBar()
        #self.pbar.setValue(0)
        #left_layout.addWidget(self.pbar)

        #Left panel, upper pane: settings
        gbox1 = QGroupBox("Settings")
        #http://myenigma.hatenablog.com/entry/2016/01/24/113413
        slider1_label1 = QLabel('Trailing frames:')
        self.slider1_label2 = QLabel('10')
        self.slider1 = QSlider(Qt.Horizontal)  # スライダの向き
        self.slider1.setRange(1, 30)  # スライダの範囲
        self.slider1.setValue(10)  # 初期値
        #スライダの目盛りを両方に出す
        self.slider1.setTickPosition(QSlider.TicksBelow)
        self.connect(self.slider1, SIGNAL('valueChanged(int)'), self.slider1_on_draw)
        #the slider is in a Hbox
        hbox = QHBoxLayout()
        hbox.addWidget(slider1_label1)
        hbox.setAlignment(slider1_label1, Qt.AlignTop)
        hbox.addWidget(self.slider1_label2)
        hbox.setAlignment(self.slider1_label2, Qt.AlignTop)
        hbox.addWidget(self.slider1)
        hbox.setAlignment(self.slider1, Qt.AlignTop)
        gbox1.setLayout(hbox)
        left_layout.addWidget(gbox1)

        #Left panel, lower pane: finish
        finish_layout_gbox = QGroupBox("Finish")
        finish_layout = QVBoxLayout()
        #https://www.tutorialspoint.com/pyqt/pyqt_qcheckbox_widget.htm
        self.btn_finish_stitch = QCheckBox("Stitch to a long image strip")
        #self.b2.toggled.connect(lambda:self.btnstate(self.b2))
        finish_layout.addWidget(self.btn_finish_stitch)
        self.btn_finish_perf = QCheckBox("Add the film perforations")
        #self.b2.toggled.connect(lambda:self.btnstate(self.b2))
        finish_layout.addWidget(self.btn_finish_perf)
        self.btn_finish_helix = QCheckBox("Make a helical image")
        #self.b2.toggled.connect(lambda:self.btnstate(self.b2))
        finish_layout.addWidget(self.btn_finish_helix)
        self.start_button = QPushButton('Start',self)
        self.connect(self.start_button,SIGNAL('clicked()'),self.start_process)
        finish_layout.addWidget(self.start_button)

       
        finish_layout_gbox.setLayout(finish_layout)
        left_layout.addWidget(finish_layout_gbox)


        
        #combine panels
        layout.addLayout(left_layout)
        self.setLayout(layout)
        self.setWindowTitle("Settings")
		
    def getfile(self):
        self.fname = QFileDialog.getOpenFileName(self, 'Open file', 
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
        


    def slider1_on_draw(self):
        self.trailing = self.slider1.value()
        self.slider1_label2.setText(str(self.trailing))


    def start_process(self):
        pass1_options = " -r {0}".format(self.editor.angle_degree)
        pass1_options += " -p {0}".format(",".join([str(x) for x in self.editor.pers]))
        stitch_options = " -s {0}".format(self.editor.slitpos)
        if self.btn_finish_helix.isChecked():
            stitch_options += " -H"
        if self.btn_finish_perf.isChecked():
            stitch_options += " -F"
        if self.btn_finish_stitch.isChecked():
            os.system("./pass1.py {0} {1} | tee {1}.pass1.log | ./stitch.py {2}".format(pass1_options, self.fname, stitch_options))
        else:
            os.system("./stitch.py {0} < {1}.pass1.log".format(stitch_options, self.fname))
                      


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
        rotation_layout.addWidget(QLabel("rotation"))
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

        
        pers_left_layout = QVBoxLayout()
        self.sliderTL = QSlider(Qt.Vertical)  # スライダの向き
        self.sliderTL.setRange(0, 499)  # スライダの範囲
        self.sliderTL.setValue(499)  # 初期値
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
        
        
        
        row_image_layout = QVBoxLayout()
        #gbox3 = QGroupBox("")
        #box = QVBoxLayout()
        self.row_image_pane = QLabel()
        #self.row_image_pane.setFixedWidth(self.preview_size)
        #self.row_image_pane.setFixedHeight(self.preview_size)
        #box.addWidget(self.row_image_pane)
        #gbox3.setLayout(box)
        row_image_layout.addWidget(self.row_image_pane)
        
        processed_edit_gbox_layout = QVBoxLayout()
        processed_edit_gbox = QGroupBox("2. Motion Detection and Slit")
        box = QVBoxLayout()
        self.processed_pane = QLabel()
        box.addWidget(self.processed_pane)
        processed_edit_gbox.setLayout(box)
        processed_edit_gbox_layout.addWidget(processed_edit_gbox)

        slit_slider_label = QLabel('Slit position:')
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

        
        #combine panels
        topleft_layout = QHBoxLayout()
        topleft_layout.addLayout(pers_left_layout)
        topleft_layout.addLayout(row_image_layout)
        topleft_layout.addLayout(pers_right_layout)
        left_layout = QVBoxLayout()
        left_layout.addLayout(topleft_layout)
        left_layout.addLayout(nextprev_layout)
        left_layout.addLayout(rotation_layout)
        row_edit_gbox = QGroupBox("1.Repair deformation")
        row_edit_gbox.setLayout(left_layout)
        row_edit_gbox_layout = QVBoxLayout()
        row_edit_gbox_layout.addWidget(row_edit_gbox)
        layout.addLayout(row_edit_gbox_layout)
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
        
    def show_snapshots(self):
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
        self.put_cv2_image(image, self.row_image_pane)
        #Right image: warped
        M = trainscanner.warp_matrix(self.pers,width,height)
        processed = cv2.warpPerspective(processed,M,(width,height))
        trainscanner.draw_focus_area(processed, self.focus)
        draw_slitpos(processed, self.slitpos)
        self.put_cv2_image(processed, self.processed_pane)
        

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

            
        
def main():
    app = QApplication(sys.argv)
    se = SettingsGUI()
    se.show()
    sys.exit(app.exec_())
	
if __name__ == '__main__':
    main()
