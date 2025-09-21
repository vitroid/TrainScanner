import rasterio
import numpy as np
from logging import getLogger
from rasterio.windows import Window
import cv2
from rasterio_tiff import Rect, Range


def rasterio_to_cv2(image):
    """Rasterio画像（RGB, CHW）をOpenCV形式（BGR, HWC）に変換"""
    # CHW → HWC に変換してから RGB → BGR に変換
    hwc_image = np.transpose(image, (1, 2, 0))  # CHW → HWC
    return hwc_image[:, :, ::-1]  # RGB → BGR


def cv2_to_rasterio(image):
    """OpenCV画像（BGR, HWC）をRasterio形式（RGB, CHW）に変換"""
    # BGR → RGB に変換してから HWC → CHW に変換
    rgb_image = image[:, :, ::-1]  # BGR → RGB
    return np.transpose(rgb_image, (2, 0, 1))  # HWC → CHW


class RasterioCanvas:
    def __init__(
        self,
        mode: str,  # "new" or otherwise
        tiff_filename: str,
        rect: Rect = None,
        scale: float = 1.0,
    ):
        self.hook = None
        self.tilesize = 256
        if mode == "new":
            assert rect is not None
            self.scale = scale
            self.rect = rect
            width, height = rect.width, rect.height

            # Preview互換モード: 地理空間情報を除外
            self.transform = rasterio.Affine(
                1 / scale,
                0,
                rect.left,
                0,
                -1 / scale,
                rect.bottom,
            )

            self.dataset = rasterio.open(
                tiff_filename,
                "w",
                driver="GTiff",
                width=int(width * scale),
                height=int(height * scale),
                count=3,  # RGB
                dtype=np.uint8,
                tiled=False,  # タイル化を無効にしてより互換性を向上
                compress="lzw",
                photometric="RGB",
                # transformを指定しない（GeoTIFFタグを回避）
            )
            self.dataset.close()

            # 再度読み書き用にひらく。
            self.dataset = rasterio.open(
                tiff_filename,
                "r+",
                transform=self.transform,
            )

        else:
            assert scale == 1.0 and rect is None
            # 読み書き用にひらく。
            self.dataset = rasterio.open(
                tiff_filename,
                "r+",
            )
            width, height = self.dataset.width, self.dataset.height
            self.rect = Rect(
                x_range=Range(min_val=0, max_val=width),
                y_range=Range(min_val=0, max_val=height),
            )
            self.scale = 1.0
            self.transform = rasterio.Affine(
                1.0,
                0.0,
                0.0,
                0.0,
                -1.0,
                height,
            )

    def put_image(self, xy, image, linear_alpha=None):
        logger = getLogger()
        # x, y = xy

        # left, top = self.region.left, self.region.top
        # width, height = (
        #     self.region.right - self.region.left,
        #     self.region.bottom - self.region.top,
        # )
        # # ワールド座標からピクセル座標への変換
        # pixel_x = int((x - left) * self.scale)
        # pixel_y = int((y - top) * self.scale)

        # # キャンバス範囲内でクリッピング
        # x_start = max(0, pixel_x)
        # y_start = max(0, pixel_y)
        # x_end = min(int(width * self.scale), pixel_x + image.shape[1])
        # y_end = min(int(height * self.scale), pixel_y + image.shape[0])

        # if x_end <= x_start or y_end <= y_start:
        #     return  # 画像が範囲外

        left = xy[0]
        top = xy[1]
        right = left + image.shape[1]
        bottom = top + image.shape[0]

        # window = rasterio.windows.Window(
        #     x_start, y_start, x_end - x_start, y_end - y_start
        # )
        print(f"{left=}, {top=}, {right=}, {bottom=}, {self.transform=}")
        window = rasterio.windows.from_bounds(
            left, top, right, bottom, transform=self.transform
        )
        # windowの幅は実数で、それをつかって切りだしたoriginalの大きさは予測不能。
        # logger.info(f"{window=}, {window.height=}, {image.shape=}")
        if linear_alpha is not None:
            original = self.dataset.read(window=window).astype(np.uint8)
            scaled_image = cv2.resize(
                image,
                (original.shape[2], original.shape[1]),
            )
            scaled_image_rasterio = cv2_to_rasterio(scaled_image)
            height, width = original.shape[1:3]
            new_range = np.linspace(0, len(linear_alpha) - 1, width)
            scaled_linear_alpha = np.interp(
                new_range, np.arange(len(linear_alpha)), linear_alpha
            )
            alpha = scaled_linear_alpha[np.newaxis, np.newaxis, :]
            mixed_image_rasterio = scaled_image_rasterio * alpha + original * (
                1 - alpha
            )
            # logger.info(f"{image_chw.shape=}, {alpha.shape=}, {original.shape=}")
            mixed_image = rasterio_to_cv2(mixed_image_rasterio)
        else:
            mixed_image = cv2.resize(
                image,
                (int(window.width), int(window.height)),
            )
            mixed_image_rasterio = cv2_to_rasterio(mixed_image)
        # 画像をHWC(height, width, channels)からCHW(channels, height, width)に変換
        self.dataset.write(
            mixed_image_rasterio,
            window=window,
        )
        if self.hook:
            self.hook((xy[0] * self.scale, xy[1] * self.scale), mixed_image)

    def get_region(self, subregion: Rect):
        x, y = subregion.left, subregion.top
        width = subregion.width
        height = subregion.height
        xmin, ymin = x, y
        xmax, ymax = (
            xmin + width,
            ymin + height,
        )
        window = rasterio.windows.from_bounds(
            xmin, ymin, xmax, ymax, transform=self.transform
        )
        return rasterio_to_cv2(self.dataset.read(window=window))

    def close(self):
        self.dataset.close()

    def set_hook(self, hook):
        self.hook = hook

    # scale on the disk
    def get_image(self, dst_width=None):
        dataset = self.dataset
        if dst_width:
            width, height = dataset.width, dataset.height
            scale = dst_width / width
            # transform = dataset.transform * rasterio.Affine(scale, 0, 0, 0, scale, 0)
            image = dataset.read(
                out_shape=(3, int(height * scale), int(width * scale)),
                resampling=rasterio.enums.Resampling.bilinear,
            )
        else:
            width, height = dataset.width, dataset.height
            image = dataset.read(out_shape=(3, height, width))
        return rasterio_to_cv2(image)


# # scale on the disk
# def get_image(tiff_filename, dst_width=None):
#     if dst_width:
#         with rasterio.open(tiff_filename) as dataset:
#             width, height = dataset.width, dataset.height
#             scale = dst_width / width
#             # transform = dataset.transform * rasterio.Affine(scale, 0, 0, 0, scale, 0)
#             with rasterio.open(tiff_filename, "r") as dataset:
#                 image = dataset.read(
#                     out_shape=(3, int(height * scale), int(width * scale)),
#                     resampling=rasterio.enums.Resampling.bilinear,
#                 )
#     else:
#         with rasterio.open(tiff_filename) as dataset:
#             width, height = dataset.width, dataset.height
#             image = dataset.read(out_shape=(3, height, width))
#     return rasterio_to_cv2(image.astype(np.uint8))


def main():
    # Preview互換モードでTIFFファイルを作成
    canvas = RasterioCanvas(
        "new",
        Rect.from_bounds(left=-100, right=-100 + 500, top=-200, bottom=-200 + 500),
        "test.tiff",
        scale=2.0,
    )
    black = np.zeros((100, 100, 3), dtype=np.uint8)

    # 赤色の矩形（BGR順序で青色成分に値を設定）
    red = black.copy()
    red[:, :, 2] = 255  # BGRの赤色成分
    canvas.put_image((-100, -200), red)

    # 緑色の矩形
    green = black.copy()
    green[:, :, 1] = 255  # BGRの緑色成分
    canvas.put_image((-50, -150), green)

    # 青色の矩形
    blue = black.copy()
    blue[:, :, 0] = 255  # BGRの青色成分
    canvas.put_image((50, -50), blue)

    # 黒色の矩形
    gray = black.copy()
    gray[:, :, :] = 128
    canvas.put_image((200, 200), gray)

    cropped = canvas.get_region(Region(left=-100, right=100, top=-200, bottom=0))
    print(cropped.shape)
    cv2.imwrite("cropped.png", cropped)

    canvas.close()


if __name__ == "__main__":
    main()
