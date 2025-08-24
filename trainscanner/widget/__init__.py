import cv2
from PyQt6.QtGui import QImage


def cv2toQImage(cv2image):
    """Convert OpenCV image to QImage"""
    height, width = cv2image.shape[:2]
    # BGR to RGB conversion
    rgb_image = cv2.cvtColor(cv2image, cv2.COLOR_BGR2RGB)
    return QImage(rgb_image.data, width, height, width * 3, QImage.Format.Format_RGB888)
