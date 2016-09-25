# TrainScanner
Convert a video to a slitscanned train image.

##Requirement
OpenCV2 for Python2 implementation.  Portable Python will be the best
choice for Windows users.

Note: Will be updated for OpenCV3 + Python3 in the near future.
##Usage
    usage: ./trainscanner.py [-2][-a x][-d][-f xmin,xmax,ymin,ymax][-g n][-p tl,bl,tr,br][-q][-s r][-t x][-w x][-z] movie
	-2		Two pass.  Store the intermediate image fragments on the disk and do not merge them.
	-a x	Antishake.  Ignore motion smaller than x pixels (5).
	-d		Debug mode.
	-f xmin,xmax,ymin,ymax	Motion detection area relative to the image size. (0.333,0.666,0.333,0.666)
	-g n	Show guide for perspective correction at the nth frame
	instead of stitching the movie.
	-m x	Interframe motion prediction.  x is the maximal
	acceleration between the frames.  Deactivated if 0 is given.(0)
	-p a,b,c,d	Set perspective points. Note that perspective correction works for the vertically scrolling picture only.
	-q		Do not show the snapshots.
	-s r	Set slit position to r (1).
	-t x	Add trailing frames after the motion is not detected. (5).
	-w r	Set slit width (1=same as the length of the interframe motion vector).
	-z		Suppress drift.

##Procedure

1. The movie must be captured with a tripod.  Otherwise the software cannot distinguish the motion of the train out of moving background.
2. Just give the movie file name.  It will work.

        trainscanner.py    sample2.mov

##Tips
###Seek and interval

By default, the trainscanner processes every 1 frame from the first
frame.  Use `-S x` option to skip the first x frames, and `-e y`
option to read every y frame.

###Small tilt fix

The train movie must be captured parallel to one of the frame edges.
Finite tilt angle causes the image drift.  If the angle is not zero but is negligible, it can be suppressed by `-z` option.

Compare the following results.

    trainscanner.py    sample2.mov
    trainscanner.py -z sample2.mov

For more slanted images, use "-r" (rotation) option.

###Motion detection area

When the trainscanner starts stitching the train, it shows the first frame with a rectangle, that is the motion detection area.
The trainscanner start stitching then any motion is detected inside the area, and the motion vectors are shown in the console.
It ends stitching when the motion is not detected again.  Therefore, if the trainscanner fails to detect the train motion properly,
change the area position and size with `-f` option.

Compare the following results.

    trainscanner.py sample4.mov
    trainscanner.py -f 0.2,0.5,0.3,0.7 sample4.mov

The first command fails to capture the whole train because of the
reflection of the glass windows. `-f` option avoid the window area to
be matched.

###Perspective adjustment
If the train movie is recorded with some perspective, trainscanner can fix it.  Invoking with `-g` option shows the perspective gauge.
Read the gauge.  Reinvoling with `-p` and `-g` shows the perspective guide lines.  If the line is correct, remove `-g` option for the product run.

Follow the procedure to learn how to fix the perspective distortion.

    trainscanner.py       sample3.mov
    trainscanner.py -g 20 sample3.mov
    trainscanner.py -g 20 -p 181,185,411,403 sample3.mov
    trainscanner.py       -p 181,185,411,403 sample3.mov
    
###Overlap between the frames
Two images are stirtched together using a gradated alpha mask.  You can
see the position and the diffuseness (width) of the gradation as a red
mask in the "snapshot" window.  The position and width of the
gradation area can be changed with `-s` and `-w` options.
Larger `-s` value moves the slit forward.  `-s 0` places the slit at
the center of the frame.  Smaller width results in the sharper image.

Compare the following results.

    trainscanner.py -z -s 1 -w 1 sample2.mov
    trainscanner.py -z -s 2 -w 0.1 sample2.mov

###Small memory footage
By default, the trainscanner stores all working images on memory.  If
the movie is huge or the computer's memory is not enough, it may cause
severe slow down.  In that case, use `-2` (two-pass process) option.
The intermediate canvas fragments are stored on the disk.  You can
stitch them together by another tool named `merger.py`.

    trainscanner.py -2 -m 1 sample.mov
    merger.py sample.mov.log

###Antishake and motion prediction
In case the movie is taken handheld, the background also moves.
Antishake feature eliminates the small background motion.  Default
value is 5 pixels and you can cnage the threshold by `-a` option.  You
may want to specify a smaller value when the train moves too slow.

If the velocity is assumed to be almost constant (that is common
case), the image region ot be matched can be predicted more precisely.  In such a case, use '-m' option to improve the matching
precision.  It will also improve processing speed.

Compare the following results.

    trainscanner.py -z sample2.mov
    trainscanner.py -z -m 2 sample2.mov

###Skip identical frames

Identical frames will be detected by global image comparison and are
skipped automatically.  The threshold value is `2` by default and can
be changed with `-i x` option.  In case the scene is too dark, you may
want to change the threshold.
