import cv2
from PyQt6.QtGui import QImage


def cv2toQImage(cv2image):
    """Convert OpenCV image to QImage"""
    if cv2image is None or cv2image.size == 0:
        return QImage()

    height, width = cv2image.shape[:2]
    # BGR to RGB conversion
    rgb_image = cv2.cvtColor(cv2image, cv2.COLOR_BGR2RGB)
    # メモリの連続性を保証するためにコピーを作成
    rgb_image = rgb_image.copy()
    return QImage(rgb_image.data, width, height, width * 3, QImage.Format.Format_RGB888)
