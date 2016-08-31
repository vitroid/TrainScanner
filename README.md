# TrainScanner
Convert a video to a slitscanned train image.

##Requirement
OpenCV2 for Python2 implementation.
##Usage
    usage: ./trainscanner.py [-p tl,bl,tr,br][-g][-d][-z][-f xmin,xmax,ymin,ymax] movie
    -p a,b,c,d	Set perspective points. Note that perspective correction works for the vertically scrolling picture only.
    -g n	Show guide for perspective correction at the nth frame.
    -z		Suppress drift.
    -f xmin,xmax,ymin,ymax  Motion detection area relative to the image size. (0.333,0.666,0.333,0.666)
    -d		Debug mode.

##Procedure

1. The movie must be captured with a tripod.  Otherwise the software cannot distinguish the motion of the train out of moving background.
2. Just give the movie file name.  It will work.

##Tips
###Small tilt fix
The train movie must be captured parallel to one of the frame edges.  For now there is no feature to adjust the tilt.
Finite tilt angle causes the image drift.  If the angle is not zero but is negligible, it can be suppressed by -z option.

Compare the following results.

    trainscanner.py    sample2.mov
    trainscanner.py -z sample2.mov

###Motion detection area
When the trainscanner start stitching the train, it shows the first frame with a rectangle, that is the motion detection area.
The trainscanner start stitching then any motion is detected inside the area, and the motion vectors are shown in the console.
It ends stitching when the motion is not detected again.  Therefore, if the trainscanner fails to detect the train motion properly,
change the area position and size with -f option.

Compare the following results.

    trainscanner.py    sample.mov
    trainscanner.py -f 0.2,0.8,0.4,0.6 sample.mov

The first exmaple fails to get the motion because the default detection area is too narrow.

###Perspective adjustment
If the train movie is recorded with some perspective, trainscanner can fix it.  Invoking with -g option shows the perspective gauge.
Read the gauge.  Reinvoling with -f and -g shows the perspective guide lines.  If the line is correct, remove -g option for product run.

Follow the procedure to learn how to fix the perspective distortion.

    trainscanner.py       sample3.mov
    trainscanner.py -g 20 sample3.mov
    trainscanner.py -g 20 -p 181,185,411,403 sample3.mov
    trainscanner.py       -p 181,185,411,403 sample3.mov
    

