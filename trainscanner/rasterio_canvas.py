import rasterio
import numpy as np
from logging import getLogger
from rasterio.windows import Window
import cv2


def rasterio_to_cv2(image):
    return np.transpose(image, (1, 2, 0))[:, :, ::-1]


def cv2_to_rasterio(image):
    return np.transpose(image, (2, 0, 1))[::-1, :, :]


class RasterioCanvas:
    def __init__(
        self, mode: str, size, lefttop, tiff_filename: str, scale: float = 1.0
    ):
        self.mode = mode
        self.hook = None
        self.tilesize = 256
        self.scale = scale
        self.width, self.height = size[0], size[1]
        left, top = lefttop[0], lefttop[1]
        self.topleft = left, top
        self.transform = rasterio.Affine(
            1 / scale,
            0,
            left,
            0,
            -1 / scale,
            -top + self.height,
        )
        # logger = getLogger()
        # logger.info(f"{self.width=}, {self.height=}, {self.scale=}")
        self.dataset = rasterio.open(
            tiff_filename,
            "w",
            driver="GTiff",
            width=self.width * scale,
            height=self.height * scale,
            count=3,  # RGB
            dtype=np.uint8,
            tiled=True,
            blockxsize=self.tilesize,
            blockysize=self.tilesize,
            compress="lzw",
            transform=self.transform,
        )
        # canvas全体を黒く塗る。
        # self.put_image(
        #     (left, top),
        #     np.zeros(
        #         (int(self.height * scale), int(self.width * scale), 3), dtype=np.uint8
        #     ),
        # )
        self.dataset.close()
        # 再度読み書き用にひらく。
        self.dataset = rasterio.open(
            tiff_filename,
            "r+",
            transform=self.transform,
        )

    def put_image(self, xy, image, linear_alpha=None):
        logger = getLogger()
        x, y = xy
        xmin, ymin = x, y
        xmax, ymax = x + image.shape[1], y + image.shape[0]
        window = rasterio.windows.from_bounds(
            xmin, ymin, xmax, ymax, transform=self.transform
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

    def get_region(self, xy, size):
        x, y = xy
        xmin, ymin = x, y
        xmax, ymax = x + size[0], y + size[1]
        window = rasterio.windows.from_bounds(
            xmin, ymin, xmax, ymax, transform=self.transform
        )
        image = self.dataset.read(window=window)
        image = np.transpose(image, (1, 2, 0))
        return image.astype(np.uint8)

    def close(self):
        self.dataset.close()

    def set_hook(self, hook):
        self.hook = hook


# scale on the disk
def get_image(tiff_filename, dst_width=None):
    if dst_width:
        with rasterio.open(tiff_filename) as dataset:
            width, height = dataset.width, dataset.height
            scale = dst_width / width
            # transform = dataset.transform * rasterio.Affine(scale, 0, 0, 0, scale, 0)
            with rasterio.open(tiff_filename, "r") as dataset:
                image = dataset.read(
                    out_shape=(3, int(height * scale), int(width * scale)),
                    resampling=rasterio.enums.Resampling.bilinear,
                )
    else:
        with rasterio.open(tiff_filename) as dataset:
            width, height = dataset.width, dataset.height
            image = dataset.read(out_shape=(3, height, width))
    return image.astype(np.uint8).transpose(1, 2, 0)[:, :, ::-1]


# crop on the disk
def crop_image(tiff_filename, leftcut, rightcut, out_filename):
    logger = getLogger()
    # logger.info(f"{left=}, {right=}, {out_filename=}")
    with rasterio.open(tiff_filename) as dataset:
        width, height = dataset.width, dataset.height
        logger.info(f"{width=} {height=} {leftcut=} {rightcut=}")
        width -= leftcut + rightcut
        window = Window(leftcut, 0, width, height)
        transform_cropped = dataset.window_transform(window)
        profile = dataset.profile
        profile.update(
            transform=transform_cropped,
            width=width,
            height=height,
            compress="lzw",
            tiled=True,
            blockxsize=256,
            blockysize=256,
        )
        with rasterio.open(out_filename, "w", **profile) as dst:
            src = dataset.read(window=window)
            dst.write(src)


def main():
    canvas = RasterioCanvas("new", (1024, 1024), (-10, 20), "test.tiff")
    black = np.zeros((100, 100, 3), dtype=np.uint8)
    red = black.copy()
    red[:, :, 0] = 255
    canvas.put_image((15, 25), red)
    green = black.copy()
    green[:, :, 1] = 255
    canvas.put_image((25, 35), green)
    blue = black.copy()
    blue[:, :, 2] = 255
    canvas.put_image((35, 45), blue)
    canvas.put_image((45, 55), black)
    canvas.close()


if __name__ == "__main__":
    main()
