#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass
import cv2
import numpy as np
import math
import sys
import os
import argparse
from logging import getLogger, basicConfig, WARN, DEBUG, INFO, WARNING

# from canvas import Canvas    #On-memory canvas
# from canvas2 import Canvas   #Cached canvas
# from tiledimage import cachedimage as ci
from trainscanner.image import Transformation
from trainscanner import video
from trainscanner.i18n import init_translations, tr

# from trainscanner.image.rasterio_canvas import RasterioCanvas
from pyperbox import Rect, Range
from tiffeditor import TiffEditor, ScalableTiffEditor

#  単体で実行する方法
# poetry run python -m trainscanner.stitch --file examples/sample2.mov.94839.tsconf  examples/sample2.mov


def linear_alpha(img_width: int, mixing_width: float, slit_pos: int, head_right: bool):
    """2画面を混合するアルファマスクを作成する。幅は固定。

    Args:
        img_width (int): 画像の幅
        mixing_width (float): ミキシング幅 (画面幅に対するパーセント)
        slit_pos (int): スリット位置。+500が一番前(列車が左に向かってすすみ、画像を右へ右へ重ねている場合には左端)、-500が一番うしろ。
        head_right (bool): 右向きならTrue

    Returns:
        np.ndarray: アルファマスク
    """
    # logger = getLogger()
    left_pixels = int(img_width * (500 - slit_pos) / 1000)
    mixing_pixels = int(img_width * mixing_width / 100)
    # logger.info(
    #     f"img_width: {img_width}, mixing_width: {mixing_width}, slit_pos: {slit_pos}, head_right: {head_right}, left_pixels: {left_pixels}, mixing_pixels: {mixing_pixels}"
    # )
    alpha = np.zeros(left_pixels + mixing_pixels + img_width)
    alpha[left_pixels : left_pixels + mixing_pixels] = np.linspace(
        0.0, 1.0, mixing_pixels
    )
    alpha[left_pixels + mixing_pixels :] = 1.0
    alpha = alpha[:img_width]
    if head_right:
        return alpha[::-1]
    else:
        return alpha


def prepare_parser(parser=None):
    if parser is None:
        # parser = myargparse.MyArgumentParser(description='TrainScanner stitcher')
        parser = argparse.ArgumentParser(description="TrainScanner stitcher")
    parser.add_argument(
        "-C",
        "--canvas",
        type=float,
        nargs=4,
        default=None,
        dest="canvas",
        help="Canvas size determined by pass1.",
    )
    parser.add_argument(
        "-s",
        "--slit",
        type=int,
        metavar="x",
        default=250,
        dest="slitpos",
        help="Slit position (0=center, 500=on the edge forward).",
    )
    parser.add_argument(
        "-W",
        "--length",
        type=int,
        metavar="x",
        default=0,
        dest="length",
        help="Maximum image length of the product.",
    )
    parser.add_argument(
        "-y",
        "--scale",
        type=float,
        default=1.0,
        dest="scale",
        metavar="x",
        help="Scaling ratio for the final image (ignored).",
    )
    parser.add_argument(
        "-w",
        "--width",
        type=float,
        default=1.0,
        dest="slitwidth",
        metavar="x",
        help="Slit mixing width (percent of image width).",
    )
    parser.add_argument(
        "-c",
        "--crop",
        type=int,
        nargs=2,
        default=[0, 1000],
        dest="crop",
        metavar="t,b",
        help="Crop the image (top and bottom).",
    )
    parser.add_argument(
        "-p",
        "--perspective",
        type=int,
        nargs=4,
        default=None,
        dest="perspective",
        help="Specity perspective warp.",
    )
    parser.add_argument(
        "-r", "--rotate", type=int, default=0, dest="rotate", help="Image rotation."
    )
    parser.add_argument(
        "-l",
        "--log",
        type=str,
        dest="logbase",
        default=None,
        help="TrainScanner settings (.tsconf) file name.",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        dest="debug",
        help="Debug mode.",
    )
    parser.add_argument("filename", type=str, help="Movie file name.")

    return parser


def overlay(image, origin, subimage, linear_alpha=None):
    origin_x, origin_y = origin
    if linear_alpha is None:
        image[
            origin_y : origin_y + subimage.shape[0],
            origin_x : origin_x + subimage.shape[1],
        ] = subimage
    else:
        alpha = linear_alpha[np.newaxis, :, np.newaxis]
        if linear_alpha.shape[0] > subimage.shape[1]:
            alpha = linear_alpha[np.newaxis, : subimage.shape[1], np.newaxis]

        original = image[
            origin_y : origin_y + subimage.shape[0],
            origin_x : origin_x + subimage.shape[1],
        ]
        image[
            origin_y : origin_y + subimage.shape[0],
            origin_x : origin_x + subimage.shape[1],
        ] = (original * (1 - alpha) + subimage * alpha).astype(np.uint8)


@dataclass
class Position:
    frame_index: int
    # frame を置く場所のtopleft
    x: float
    y: float
    # 直前のフレームからの変位。
    dx: float
    dy: float


class Stitcher:
    """
    exclude video handling
    """

    def __init__(self, argv, hook=None):
        # ロガーをインスタンス変数として初期化
        self.logger = getLogger(__name__)

        init_translations()

        parser = prepare_parser()
        # これが一番スマートなんだが、動かないので、手動で--fileをさがして処理を行う。
        # parser.add_argument('--file', type=open, action=LoadFromFile)
        for i, arg in enumerate(argv):
            if arg == "--file":
                tsconf = argv[i + 1]
                del argv[i]
                del argv[i]
                with open(tsconf, encoding="utf-8") as f:
                    argv += f.read().splitlines()
                break
        self.params, unknown = parser.parse_known_args(argv[1:])
        # 昔のpass1が計算したcanvasサイズは信用ならないので、自前で再計算する。
        del self.params.canvas

        # ログ設定をコマンドライン引数に基づいて行う
        import logging

        if self.params.debug:
            basicConfig(
                level=DEBUG,
                format="%(asctime)s %(levelname)s %(message)s",
            )
            logging.getLogger().setLevel(DEBUG)
            self.logger.info("Debug mode enabled")
        else:
            basicConfig(level=INFO, format="%(asctime)s %(levelname)s %(message)s")
            logging.getLogger().setLevel(INFO)
            # サードパーティライブラリのDEBUGメッセージを抑制
            logging.getLogger("rasterio").setLevel(WARNING)

        # Decide the paths
        moviepath = self.params.filename
        import os

        moviedir = os.path.dirname(moviepath)
        moviebase = os.path.basename(moviepath)
        self.tsposfile = ""

        if self.tsposfile == "" or not os.path.exists(self.tsposfile):
            tsconfdir = os.path.dirname(self.params.logbase)
            if tsconfdir == "":
                tsconfdir = "."
            tsconfbase = os.path.basename(self.params.logbase)
            self.tsposfile = tsconfdir + "/" + tsconfbase + ".tspos"
        moviefile = tsconfdir + "/" + moviebase
        self.outfilename = tsconfdir + "/" + tsconfbase + ".tiff"
        if not os.path.exists(moviefile):
            moviefile = moviepath
        self.logger.info("TSPos  {0}".format(self.tsposfile))
        self.logger.info("Movie  {0}".format(moviefile))
        self.logger.info("Output {0}".format(self.outfilename))

        self.firstFrame = True
        self.currentFrame = 0  # 1 is the first frame

        # self.R = None
        # self.M = None
        self.transform = Transformation(
            self.params.rotate, self.params.perspective, self.params.crop
        )

        # 1フレームだけ読んで、キャンバスの大きさを決定する。
        self.vl = video.video_loader_factory(moviefile)
        frame = self.vl.next()
        _, _, cropped = self.transform.process_image(frame)
        height, width = cropped.shape[:2]

        # ファイルから位置を読み込む。
        # canvasを正確に再定義する。
        locations = []
        absx = 0
        absy = 0
        canvas_rect = Rect.from_bounds(0, width, 0, height)
        tspos = open(self.tsposfile)
        for line in tspos.readlines():
            if len(line) > 0 and line[0] != "@":
                cols = [float(x) for x in line.split()]
                if len(cols) > 0:
                    # この計算順序は正しい。まず変位を足してから、画像を置く。
                    absx += cols[1]
                    absy += cols[2]
                    canvas_rect |= Rect.from_bounds(
                        int(absx), int(absx + width), int(absy), int(absy + height)
                    )
                    locations.append(
                        Position(
                            frame_index=int(cols[0]),
                            x=absx * self.params.scale,
                            y=absy * self.params.scale,
                            dx=cols[1] * self.params.scale,
                            dy=cols[2] * self.params.scale,
                        )
                    )
        self.locations = locations
        self.total_frames = len(locations)

        # scaleオプションは無視する。
        del self.params.scale
        scale = 1.0
        if self.params.length > 0:
            # product length is specified.
            # scale is overridden
            scale = self.params.length / canvas_rect.width
            if scale > 1:
                scale = 1  # do not allow stretching
            # for GUI
        self.dimen = canvas_rect
        self.hook = hook
        self.lefttop = (canvas_rect.left, canvas_rect.top)
        # the canvas behaves like an image
        if scale == 1:
            self.canvas = TiffEditor(
                filepath=self.outfilename,
                mode="w",
                shape=(canvas_rect.height, canvas_rect.width, 3),
                dtype=np.uint8,
            )
        else:
            self.canvas = ScalableTiffEditor(
                filepath=self.outfilename,
                mode="w",
                virtual_shape=(canvas_rect.height, canvas_rect.width, 3),
                dtype=np.uint8,
                scale_factor=scale,
            )
        # 新規ファイル作成時のバグ対応：ハンドルが開かれていない場合は明示的に開く
        if self.canvas._rasterio_handle is None and self.canvas._tiff_handle is None:
            self.canvas._open_file()

        self.vl = video.video_loader_factory(moviefile)

    def before(self):
        """
        is a generator.
        """
        if len(self.locations) == 0:
            return
        # initial seek

        # self.vl.seek(self.locations[0][0])
        # while self.currentFrame + 1 < self.locations[0][0]:
        #     self.logger.debug((self.currentFrame, self.locations[0][0]))
        #     # このyieldは要るのか?
        #     yield self.currentFrame, self.locations[0][0]
        #     self.currentFrame = self.vl.skip()

    def set_hook(self, hook):
        self.hook = hook

    def add_image(self, frame, absx, absy, idx, idy):
        _, _, cropped = self.transform.process_image(frame)
        origin_x = int(absx - self.lefttop[0])
        origin_y = int(absy - self.lefttop[1])
        height, width = cropped.shape[:2]
        if self.firstFrame:
            self.canvas[origin_y : origin_y + height, origin_x : origin_x + width] = (
                cropped
            )
            self.firstFrame = False
        elif idx != 0:
            alpha = linear_alpha(
                img_width=width,
                mixing_width=self.params.slitwidth,
                # defaultは1.0で、これは画面幅の1%に相当する。
                slit_pos=self.params.slitpos,
                head_right=idx < 0,
            )
            # canvasの左上を(0、0)とした場合の、cropped画像を貼る座標を計算
            origin_x = int(absx - self.lefttop[0])
            origin_y = int(absy - self.lefttop[1])
            overlay(self.canvas, (origin_x, origin_y), cropped, linear_alpha=alpha)
            # self.canvas.put_image((absx, absy), cropped, linear_alpha=alpha)
        # this sends a signal to the observers
        if self.hook:
            self.hook(
                (origin_x, origin_y),
                self.canvas[origin_y : origin_y + height, origin_x : origin_x + width],
            )

    def stitch(self):
        self.before()
        # for num, den in self.before():
        #     pass
        for num, den in self.loop():
            pass
        self.canvas.close()

    def loop(self):
        den = len(self.locations)
        for num, location in enumerate(self.locations):
            if self.vl.head != location.frame_index:
                self.vl.seek(location.frame_index)
            frame = self.vl.next()
            # assert False
            if frame is None:
                return False
            self.add_image(frame, location.x, location.y, location.dx, location.dy)

            yield (num, den)


if __name__ == "__main__":
    st = Stitcher(argv=sys.argv)

    st.stitch()
    # st.make_a_big_picture()
