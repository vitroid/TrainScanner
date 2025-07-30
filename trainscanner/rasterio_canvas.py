import rasterio
import numpy as np


class RasterioCanvas:
    def __init__(
        self, mode: str, size, lefttop, tiff_filename: str, tilesize: int = 256
    ):
        self.mode = mode
        self.tilesize = tilesize
        width, height = size
        left, top = lefttop
        left -= 1
        self.transform = rasterio.Affine(1, 0, left, 0, -1, top + height)
        tiff_filename = "test.tiff"
        self.dataset = rasterio.open(
            tiff_filename,
            "r+",
            driver="GTiff",
            width=width,
            height=height,
            count=3,  # RGB
            dtype=np.uint8,
            transform=self.transform,
            tiled=True,
            blockxsize=self.tilesize,
            blockysize=self.tilesize,
            compress="lzw",
        )

    def put_image(self, xy, image, linear_alpha=None):
        x, y = xy
        xmin, ymin = x, y
        xmax, ymax = x + image.shape[1], y + image.shape[0]
        window = rasterio.windows.from_bounds(
            xmin, ymin, xmax, ymax, transform=self.transform
        )
        image_chw = np.transpose(image, (2, 0, 1))
        if linear_alpha is not None:
            linear_alpha_transposed = np.transpose(linear_alpha, (1, 0))
            original = self.dataset.read(window=window)
            original = original.astype(np.uint8)
            image_chw = image_chw * linear_alpha_transposed + original * (
                1 - linear_alpha_transposed
            )
            image_chw = image_chw.astype(np.uint8)
        # 画像をHWC(height, width, channels)からCHW(channels, height, width)に変換
        self.dataset.write(
            image_chw,
            window=window,
        )

    def get_image(self, xy, size):
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
