import cv2
import numpy as np
import os
from trainscanner import Region, find_subimage


def main():
    # find_subimageのテスト
    lena_path = "test/lena.png"
    img1 = cv2.imread(lena_path)
    img2 = cv2.imread(lena_path)
    print(f"{img1.shape=} {img2.shape=}")
    dx, dy = 0.1, 0.4
    affine_matrix = np.matrix(((1.0, 0.0, dx), (0.0, 1.0, dy)))
    img2 = cv2.warpAffine(img2, affine_matrix, (img1.shape[1], img1.shape[0]))
    subimage = img1[100:300, 150:350]
    region = Region(left=0, top=0, right=img1.shape[1], bottom=img1.shape[0])
    result = find_subimage(img2, subimage, region, relative=False)
    print(result)


if __name__ == "__main__":
    main()
