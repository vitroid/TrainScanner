#-*- coding: utf-8 -*-
import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import os
import cv2
import numpy as np
import math

#In GUI, only the horizontal scrolling is allowed.
#For vertical ones, apply 90 degree rotation.

#https://www.tutorialspoint.com/pyqt/pyqt_qfiledialog_widget.htm

class filedialogdemo(QWidget):
    def __init__(self, parent = None):
        super(filedialogdemo, self).__init__(parent)

        # options
        self.trailing = 10
        self.angle    = 0
        #private
        self.snapshots = []
        self.frame     = -1
        self.preview_size = 450

        # layout
        layout = QHBoxLayout()
        
        #leftmost panel for specifying options
        left_panel = QVBoxLayout()
        self.btn = QPushButton("Open a movie")
        self.btn.clicked.connect(self.getfile)
        left_panel.addWidget(self.btn)
    
        self.le = QLabel("(File name appears here)")
        left_panel.addWidget(self.le)
        
        #self.pbar = QProgressBar()
        #self.pbar.setValue(0)
        #left_panel.addWidget(self.pbar)

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
        left_panel.addWidget(gbox1)

        #Left panel, lower pane: finish
        gbox2 = QGroupBox("Finish")
        hbox = QHBoxLayout()
        
        gbox1.setLayout(hbox)
        left_panel.addWidget(gbox2)


        #second left panel for image rotation
        left2_panel = QVBoxLayout()
        self.btn = QPushButton("-1")
        self.btn.clicked.connect(self.angle_dec)
        left2_panel.addWidget(self.btn)
        self.angle_label = QLabel("0")
        left2_panel.addWidget(self.angle_label)
        self.btn = QPushButton("+1")
        self.btn.clicked.connect(self.angle_inc)
        left2_panel.addWidget(self.btn)

        center_panel = QVBoxLayout()
        gbox3 = QGroupBox("")
        box = QVBoxLayout()
        self.row_image = QLabel()
        self.row_image.setFixedWidth(self.preview_size)
        self.row_image.setFixedHeight(self.preview_size)
        box.addWidget(self.row_image)
        gbox3.setLayout(box)
        center_panel.addWidget(gbox3)
        
        right_panel = QVBoxLayout()
        gbox4 = QGroupBox("")
        box = QVBoxLayout()
        self.processed = QLabel()
        self.processed.setFixedWidth(self.preview_size)
        self.processed.setFixedHeight(self.preview_size)
        box.addWidget(self.processed)
        gbox4.setLayout(box)
        right_panel.addWidget(gbox4)
        
        #combine panels
        layout.addLayout(left_panel)
        layout.addLayout(left2_panel)
        layout.addLayout(center_panel)
        layout.addLayout(right_panel)
        self.setLayout(layout)
        self.setWindowTitle("Trainscanner GUI")
		
    def getfile(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file', 
            os.path.expanduser('~'),"Movie files (*.mov *.mp4)")
        #self.le.setPixmap(QPixmap(fname))
        #Load every 30 frames here for preview.
        self.le.setText(fname)
        fname = "sample3.mov"
        print fname
        cap = cv2.VideoCapture(fname)
        count = 0
        while True:
            ret, frame = cap.read()
            count += 1
            #self.pbar.setValue(100 - 100 / count)
            if not ret:
                break
            h,w = frame.shape[0:2]
            if h > w:
                sq = np.zeros((h,h,3),dtype=np.uint8)
                sq[0:h,(h-w)/2:(h-w)/2+w,:] = frame
            else:
                sq = np.zeros((w,w,3),dtype=np.uint8)
                sq[(w-h)/2:(w-h)/2+h,0:w,:] = frame
            self.snapshots.append(sq)
            for i in range(29):
                ret = cap.grab()
                if not ret:
                    break
            if not ret:
                break
        #self.pbar.reset()
        self.frame = 0
        self.show_snapshots()

    def angle_inc(self):
        self.angle += 1
        self.angle_label.setText(str(self.angle))
        self.show_snapshots()

    def angle_dec(self):
        self.angle -= 1
        self.angle_label.setText(str(self.angle))
        self.show_snapshots()

    def slider1_on_draw(self):
        self.trailing = self.slider1.value()
        self.slider1_label2.setText(str(self.trailing))

    def show_snapshots(self):
        """
        put the snapshots in the preview panes
        """
        if self.frame < 0:
            return
        f = self.snapshots[self.frame]
        if self.angle != 0:
            h,w = f.shape[0:2]
            a = math.cos(self.angle*math.pi/180)
            b = math.sin(self.angle*math.pi/180)
            R = np.matrix(((a,b,(1-a)*w/2 - b*h/2),(-b,a,b*w/2+(1-a)*h/2)))
            f = cv2.warpAffine(f, R, (w,h))
        #Left image: unwarped with gauge
        height, width, channel = f.shape
        bytesPerLine = 3 * width
        self.pixmap = QPixmap.fromImage(QImage(f.data, width, height, bytesPerLine, QImage.Format_RGB888))
        if height > width:
            if height > self.preview_size:
                self.row_image.setPixmap(self.pixmap.scaledToHeight(self.preview_size))
                return
        else:
            if width > self.preview_size:
                self.row_image.setPixmap(self.pixmap.scaledToWidth(self.preview_size))
                return
        self.row_image.setPixmap(self.pixmap)
        #Right image: warped
        
def main():
    app = QApplication(sys.argv)
    ex = filedialogdemo()
    ex.show()
    sys.exit(app.exec_())
	
if __name__ == '__main__':
    main()
