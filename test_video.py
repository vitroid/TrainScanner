import trainscanner.video
import cv2

# seek()がちゃんと動いていないことがわかった

vl1 = trainscanner.video.video_loader_factory(
    "/Users/matto/Dropbox/ArtsAndIllustrations/Stitch tmp2/Windows/IMG_0009/IMG_0009.mov"
)
vl2 = trainscanner.video.video_loader_factory(
    "/Users/matto/Dropbox/ArtsAndIllustrations/Stitch tmp2/Windows/IMG_0009/IMG_0009.mov"
)
for i in range(46):
    frame = vl1.next()
    cv2.imshow(f"sequential", frame)

    ret = vl2.seek(i)
    frame = vl2.next()
    cv2.imshow(f"seeked", frame)
    print(i, ret)
    cv2.waitKey(0)

cv2.destroyAllWindows()
