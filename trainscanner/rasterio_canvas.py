import rasterio
import numpy as np
from logging import getLogger
from rasterio.windows import Window


class RasterioCanvas:
    def __init__(self, mode: str, size, lefttop, tiff_filename: str):
        self.mode = mode
        self.hook = None
        self.tilesize = 256
        width, height = size
        self.topleft = lefttop
        left, top = lefttop
        self.transform = rasterio.Affine(1, 0, left, 0, -1, top + height)
        self.dataset = rasterio.open(
            tiff_filename,
            "w",
            driver="GTiff",
            width=width,
            height=height,
            count=3,  # RGB
            dtype=np.uint8,
            tiled=True,
            blockxsize=self.tilesize,
            blockysize=self.tilesize,
            compress="lzw",
            transform=self.transform,
        )
        # canvas全体を黒く塗る。
        self.put_image((left, top), np.zeros((height, width, 3), dtype=np.uint8))
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
        # windowがself.datasetからはみ出ている可能性がある。
        # その場合は、windowを修正する。
        if (
            window.col_off < 0
            or window.row_off < 0
            or window.col_off + window.width > self.dataset.width
            or window.row_off + window.height > self.dataset.height
        ):
            logger.warning(f"window is out of dataset: {window=}")
            # おさまるようにxmin,xmax,ymin,ymaxを修正する。
            if window.col_off < 0:
                xmin -= window.col_off
            if window.row_off < 0:
                ymin -= window.row_off
            if window.col_off + window.width > self.dataset.width:
                xmax -= window.col_off + window.width - self.dataset.width
            if window.row_off + window.height > self.dataset.height:
                ymax -= window.row_off + window.height - self.dataset.height
            if xmin > xmax or ymin > ymax:
                logger.warning(f"window is out of dataset: {window=}")
                return

            window = rasterio.windows.from_bounds(
                xmin,
                ymin,
                xmax,
                ymax,
                transform=self.transform,
            )

            logger.info(f"window is corrected: {window=}")
        image_chw = np.transpose(image, (2, 0, 1))[::-1, :, :]
        if linear_alpha is not None:
            original = self.dataset.read(window=window)
            original = original.astype(np.uint8)
            # logger.info(f"{original.shape=}")
            # originalの幅が足りない場合がある
            height, width = original.shape[1:3]
            logger.info(f"{width=}, {height=}, {image.shape[1]=}, {image.shape[0]=}")
            if width < image.shape[1] or height < image.shape[0]:
                logger.warning(f"image is too large for canvas: {image.shape=}")
                return
            alpha = linear_alpha[np.newaxis, np.newaxis, :]
            image_chw = image_chw * alpha + original * (1 - alpha)
            image_chw = image_chw.astype(np.uint8)
            # windowを修正する。
            window = rasterio.windows.from_bounds(
                xmin, ymin, xmin + width, ymax, transform=self.transform
            )
        # 画像をHWC(height, width, channels)からCHW(channels, height, width)に変換
        self.dataset.write(
            image_chw,
            window=window,
        )
        if self.hook:
            self.hook(xy, image_chw[::-1].transpose(1, 2, 0))

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
        window = Window(leftcut, 0, width - rightcut, height)
        transform_cropped = dataset.window_transform(window)
        profile = dataset.profile
        profile.update(
            transform=transform_cropped,
            width=width - rightcut - leftcut,
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
