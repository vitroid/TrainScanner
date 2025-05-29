import cv2
import numpy as np


# Automatically extensible canvas.
class Canvas:

    def __init__(self, image=None, position=None):
        self._image = image
        self.origin = position

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

        x, y = pos
        absx, absy = self.origin  # absolute coordinate of the top left of the canvas

        # キャンバスと追加画像の境界を計算
        canvas_bounds = (
            absx,
            absy,
            self._image.shape[1] + absx,
            self._image.shape[0] + absy,
        )
        image_bounds = (x, y, add_image.shape[1] + x, add_image.shape[0] + y)

        # 新しいキャンバスの境界を計算
        xmin = min(canvas_bounds[0], image_bounds[0])
        xmax = max(canvas_bounds[2], image_bounds[2])
        ymin = min(canvas_bounds[1], image_bounds[1])
        ymax = max(canvas_bounds[3], image_bounds[3])

        # キャンバスのサイズが変更必要な場合のみ新しいキャンバスを作成
        if (xmax - xmin, ymax - ymin) != (self._image.shape[1], self._image.shape[0]):
            newcanvas = np.zeros((ymax - ymin, xmax - xmin, 3), np.uint8)
            newcanvas[
                canvas_bounds[1] - ymin : canvas_bounds[3] - ymin,
                canvas_bounds[0] - xmin : canvas_bounds[2] - xmin,
                :,
            ] = self._image
        else:
            newcanvas = self._image

        # 画像を追加
        if linear_alpha is None:
            newcanvas[
                image_bounds[1] - ymin : image_bounds[3] - ymin,
                image_bounds[0] - xmin : image_bounds[2] - xmin,
                :,
            ] = add_image
        else:
            newcanvas[
                image_bounds[1] - ymin : image_bounds[3] - ymin,
                image_bounds[0] - xmin : image_bounds[2] - xmin,
                :,
            ] = add_image * linear_alpha[:, :] + newcanvas[
                image_bounds[1] - ymin : image_bounds[3] - ymin,
                image_bounds[0] - xmin : image_bounds[2] - xmin,
                :,
            ] * (
                1 - linear_alpha[:, :]
            )

        self._image = newcanvas
        self.origin = (xmin, ymin)
