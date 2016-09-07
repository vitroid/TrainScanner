# TrainScanner
Convert a video to a slitscanned train image.

##Requirement
OpenCV2 for Python2 implementation.

Note: Will be updated for OpenCV3 + Python3 in the near future.
##Usage
    usage: ./trainscanner.py [-2][-a x][-d][-f xmin,xmax,ymin,ymax][-g n][-p tl,bl,tr,br][-q][-s r][-t x][-w x][-z] movie
	-2		Two pass.  Store the intermediate image fragments on the disk and do not merge them.
	-a x	Antishake.  Ignore motion smaller than x pixels (5).
	-d		Debug mode.
	-f xmin,xmax,ymin,ymax	Motion detection area relative to the image size. (0.333,0.666,0.333,0.666)
	-g n	Show guide for perspective correction at the nth frame instead of stitching the movie.
	-p a,b,c,d	Set perspective points. Note that perspective correction works for the vertically scrolling picture only.
	-q		nDo not show the snapshots.
	-s r	Set slit position to r (0.2).
	-t x	Add trailing frames after the motion is not detected. (5).
	-w r	Set slit width (1=same as the length of the interframe motion vector).
	-z		Suppress drift.

##Procedure

1. The movie must be captured with a tripod.  Otherwise the software cannot distinguish the motion of the train out of moving background.
2. Just give the movie file name.  It will work.

    `trainscanner.py    sample2.mov`

##Tips
###Small tilt fix
The train movie must be captured parallel to one of the frame edges.  For now there is no feature to adjust the tilt.
Finite tilt angle causes the image drift.  If the angle is not zero but is negligible, it can be suppressed by `-z` option.

Compare the following results.

    trainscanner.py    sample2.mov
    trainscanner.py -z sample2.mov

###Motion detection area
When the trainscanner starts stitching the train, it shows the first frame with a rectangle, that is the motion detection area.
The trainscanner start stitching then any motion is detected inside the area, and the motion vectors are shown in the console.
It ends stitching when the motion is not detected again.  Therefore, if the trainscanner fails to detect the train motion properly,
change the area position and size with `-f` option.

Compare the following results.

    trainscanner.py    sample.mov
    trainscanner.py -f 0.2,0.8,0.4,0.6 sample.mov

The first exmaple fails to get the motion because the default detection area is too narrow.

###Perspective adjustment
If the train movie is recorded with some perspective, trainscanner can fix it.  Invoking with `-g` option shows the perspective gauge.
Read the gauge.  Reinvoling with `-p` and `-g` shows the perspective guide lines.  If the line is correct, remove `-g` option for the product run.

Follow the procedure to learn how to fix the perspective distortion.

    trainscanner.py       sample3.mov
    trainscanner.py -g 20 sample3.mov
    trainscanner.py -g 20 -p 181,185,411,403 sample3.mov
    trainscanner.py       -p 181,185,411,403 sample3.mov
    
###Overlap between the frames
Trainscanner overlays the two successive video frames at a narrow
area (that is, slit).
Two images are stirtched together using a smooth alpha mask.  You can
see the position of the slit in the "snapshot" window.  You can also
change the position and width of the slit with `-s` and `-w` options.
Wider slit results in smoother image, but that may in turn cause
ghost on the moving object.

###Small memory footage
By default, the trainscanner stores all working images on memory.  If
the movie is huge or the computer's memory is not enough, it may cause
severe slow down.  In that case, use `-2` (two-pass process) option.
The intermediate canvas fragments are stored on the disk.  You can
stitch them together by another tool named `merge.py`.

###Antishake
In case the movie is taken handheld, the background also moves.
Antishake feature eliminates the small background motion.  Default
value is 5 pixels and you can cnage the threshold by `-a` option.

