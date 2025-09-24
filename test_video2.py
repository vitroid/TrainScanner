import trainscanner.video
import cv2

# seek()がちゃんと動いていないことがわかった

vl1 = trainscanner.video.video_loader_factory(
    "/Users/matto/Dropbox/ArtsAndIllustrations/Stitch tmp2/Windows/IMG_0009/IMG_0009.mov"
)
for i in range(46):
    frame = vl1.next()

for i in range(46, 53):
    frame = vl1.next()
    cv2.imshow(f"frame", frame)
    print(i)
    cv2.waitKey(0)

cv2.destroyAllWindows()
