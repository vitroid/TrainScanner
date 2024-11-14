import cv2
import numpy as np


# Automatically extensible canvas.
class Canvas:

    def __init__(self, image=None, position=None):
        self._image = image
        self.origin = position
        self.first = True

    def done(self):
        """
        Release memory
        """
        self._image = None

    def get_image(self):
        return self._image

    def put_image(self, pos, add_image, linear_alpha=None):
        if self._image is None:
            self._image = add_image.copy()
            self.origin = pos
            return
        if self.first:
            self.first = False
        x, y = pos
        absx, absy = self.origin  # absolute coordinate of the top left of the canvas
        cxmin = absx
        cymin = absy
        cxmax = self._image.shape[1] + absx
        cymax = self._image.shape[0] + absy
        ixmin = x
        iymin = y
        ixmax = add_image.shape[1] + x
        iymax = add_image.shape[0] + y

        xmin = min(cxmin, ixmin)
        xmax = max(cxmax, ixmax)
        ymin = min(cymin, iymin)
        ymax = max(cymax, iymax)
        if (xmax - xmin, ymax - ymin) != (self._image.shape[1], self._image.shape[0]):
            newcanvas = np.zeros((ymax - ymin, xmax - xmin, 3), np.uint8)
            newcanvas[cymin - ymin : cymax - ymin, cxmin - xmin : cxmax - xmin, :] = (
                self._image[:, :, :]
            )
        else:
            newcanvas = self._image
        if linear_alpha is None:
            newcanvas[iymin - ymin : iymax - ymin, ixmin - xmin : ixmax - xmin, :] = (
                add_image[:, :, :]
            )
        else:
            newcanvas[
                iymin - ymin : iymax - ymin, ixmin - xmin : ixmax - xmin, :
            ] = add_image[:, :, :] * linear_alpha[:, :] + newcanvas[
                iymin - ymin : iymax - ymin, ixmin - xmin : ixmax - xmin, :
            ] * (
                1 - linear_alpha[:, :]
            )
        self._image = newcanvas
        self.origin = (xmin, ymin)
