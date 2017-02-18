#TrainScanner tutorial

This document is outdated. [README_ja.md](https://github.com/vitroid/TrainScanner/blob/master/README_ja.md) is more frequently updated.

##Installation
###Requirements
Install `PyQt5`, `OpenCV3`, `Python3` packages.  On installing OpenCV3, specify `--with-ffmpeg --with-tbb --with-python3 --HEAD` options.
###Install by pip 
Install the trainscanner from the PyPI with pip3 command:

    % pip3 install trainscanner
    % trainscanner
###Install by homebrew (mac)
It installs everything required. (PyQt5, OpenCV3 with options, Python3)

    % brew tap vitroid/homebrew-TrainScanner
    % brew install trainscanner
    % trainscanner

##How to capture the video
Capture the whole train from the side with a video camera.

* Tripod is necessary.
* Pay attention to use tripod on the station platform.

Other advises are listed in the last section.
##Open in TrainScanner
1. Open the video file by pressing the "Open the movie" button.  If you fail to open the movie, try conversion with ffmpeg etc.

![settings](https://github.com/vitroid/TrainScanner/blob/master/images_ja/settings.png?raw=true)

1. When file is successfully opened, a large dialog window appears.  There are three panels in the window.  Top panel is the frame selector, left panel is for the deformation, and right panel is for specifying the motion detection window.

![edit1](https://github.com/vitroid/TrainScanner/blob/master/images_ja/edit1.png?raw=true)

1. First of all, find the first frame, that is, the frame in which the train is about to enter in the sight, by clicking the thumbnail bar. 

![edit1a](https://github.com/vitroid/TrainScanner/blob/master/images_ja/edit1a.png?raw=true)

1. Select a frame by the slider below the thumbnail bar.

![edit1b](https://github.com/vitroid/TrainScanner/blob/master/images_ja/edit1b.png?raw=true)

1. If the video is captured in portrait, or the camera is a little bit slanted, rotate the photo using the buttons below the left panel.

![edit2a](https://github.com/vitroid/TrainScanner/blob/master/images_ja/edit2a.png?raw=true)

1. Four sliders at the four corners of the left panel is the perspective correction.  (You can skip this step).

![edit2b](https://github.com/vitroid/TrainScanner/blob/master/images_ja/edit2b.png?raw=true)

1. In the right panel, specify the location of the motion detection window.  By default, the window is at the central one third of the image.  
1. Red lines in the right panel indicates the positions of the slit.  That is, the long image strip is made from the thin image at this red line of each video frame.  You can move the slid with the slider at the bottom.

![edit2c](https://github.com/vitroid/TrainScanner/blob/master/images_ja/edit2c.png?raw=true)


##Stitch in TrainScanner
When you finished editing the frames, let's go stitching.

1. Go back to the first, small dialog.  (Do not close the large window.)  Just press the "Start" button.  Firstly, a motion detection dialog window appears, in which interframe difference is shown.  If the two successive frames are identical, the window becomes white, while difference is indicated in colors.  If the software detect the train motion correctly, the image region of the train becomes white and the background becomes colored. (Note: it takes fairly long time for now because the seeking feature in OpenCV2 is very inaccurate. Sorry for convenience.)
1. After the motion detection is completed, a stitching dialog appears.  In the window, you can watch the making process of the long train image strip.  After completing the stitch, the product image is saved at the same folder where the original video resides.

##For better product photo
...

##Advises

...

##Revision History

* 2016-11-11 GUI Version 0.1 is released.
