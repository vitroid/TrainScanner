import cv2
from trainscanner.widget import canvas


class ScaledCanvas(canvas.Canvas):

    def __init__(self, image=None, position=None, scale=1.0):
        super(ScaledCanvas, self).__init__(image=image, position=position)
        self.scale = scale

    # interface for receiving the signal emit by TiledImage class.
    # (to make a scaled preview)
    def put_image(self, pos, image):
        height, width = image.shape[0:2]
        # To avoid a hairline in the scaled stitching
        h = int(height * self.scale + 1)
        w = int(width * self.scale + 1)
        resized = cv2.resize(image, (w, h), interpolation=cv2.INTER_CUBIC)
        x = int(pos[0] * self.scale)
        y = int(pos[1] * self.scale)
        super().put_image((x, y), resized)
