#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import math
import sys
import os
import argparse
from logging import getLogger, basicConfig, WARN, DEBUG, INFO

# from canvas import Canvas    #On-memory canvas
# from canvas2 import Canvas   #Cached canvas
# from tiledimage import cachedimage as ci
from trainscanner import trainscanner
from trainscanner import video
from trainscanner.i18n import init_translations, tr
from trainscanner.rasterio_canvas import RasterioCanvas
from trainscanner.pass1 import extend_canvas

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
        help="Scaling ratio for the final image.",
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
    parser.add_argument("filename", type=str, help="Movie file name.")

    return parser


class Stitcher:
    """
    exclude video handling
    """

    def __init__(self, argv, hook=None):
        logger = getLogger()

        init_translations()

        parser = prepare_parser()
        # これが一番スマートなんだが、動かないので、手動で--fileをさがして処理を行う。
        # parser.add_argument('--file', type=open, action=LoadFromFile)
        for i, arg in enumerate(argv):
            if arg == "--file":
                tsconf = argv[i + 1]
                del argv[i]
                del argv[i]
                with open(tsconf) as f:
                    argv += f.read().splitlines()
                break
        self.params, unknown = parser.parse_known_args(argv[1:])
        # 昔のpass1が計算したcanvasサイズは信用ならないので、自前で再計算する。
        del self.params.canvas

        # Decide the paths
        moviepath = self.params.filename
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
        logger.info("TSPos  {0}".format(self.tsposfile))
        logger.info("Movie  {0}".format(moviefile))
        logger.info("Output {0}".format(self.outfilename))

        self.firstFrame = True
        self.currentFrame = 0  # 1 is the first frame

        # self.R = None
        # self.M = None
        self.transform = trainscanner.transformation(
            self.params.rotate, self.params.perspective, self.params.crop
        )

        # 1フレームだけ読んで、キャンバスの大きさを決定する。
        self.vl = video.video_loader_factory(moviefile)
        _, frame = self.vl.next()
        _, _, cropped = self.transform.process_image(frame)
        height, width = cropped.shape[:2]

        self.vl = video.video_loader_factory(moviefile)

        # ファイルから位置を読み込む。
        # canvasを正確に再定義する。
        locations = []
        absx = 0
        absy = 0
        canvas_dimen = extend_canvas(None, width, height, 0, 0)
        tspos = open(self.tsposfile)
        for line in tspos.readlines():
            if len(line) > 0 and line[0] != "@":
                cols = [float(x) for x in line.split()]
                if len(cols) > 0:
                    # この計算順序は正しい。まず変位を足してから、画像を置く。
                    absx += cols[1]
                    absy += cols[2]
                    canvas_dimen = extend_canvas(
                        canvas_dimen, width, height, absx, absy
                    )
                    cols = [cols[0], absx, absy] + cols[1:]
                    cols[1:] = [float(x * self.params.scale) for x in cols[1:]]
                    locations.append(cols)
        self.locations = locations
        self.total_frames = len(locations)

        # scaleオプションは無視する。
        del self.params.scale
        scale = 1.0
        if self.params.length > 0:
            # product length is specified.
            # scale is overridden
            scale = self.params.length / canvas_dimen[0]
            if scale > 1:
                scale = 1  # do not allow stretching
            # for GUI
        self.dimen = canvas_dimen
        self.hook = hook
        self.canvas = RasterioCanvas(
            "new",
            size=canvas_dimen[:2],
            lefttop=canvas_dimen[2:],
            tiff_filename=self.outfilename,
            scale=scale,
        )

    def before(self):
        """
        is a generator.
        """
        logger = getLogger()
        if len(self.locations) == 0:
            return
        # initial seek
        while self.currentFrame + 1 < self.locations[0][0]:
            logger.debug((self.currentFrame, self.locations[0][0]))
            # このyieldは要るのか?
            yield self.currentFrame, self.locations[0][0]
            self.currentFrame = self.vl.skip()

    def getProgress(self):
        den = self.total_frames
        num = den - len(self.locations)
        return (num, den)

    def add_image(self, frame, absx, absy, idx, idy):
        _, _, cropped = self.transform.process_image(frame)
        if self.firstFrame:
            self.canvas.put_image((absx, absy), cropped)
            self.firstFrame = False
        else:
            width = cropped.shape[1]
            alpha = linear_alpha(
                img_width=width,
                mixing_width=self.params.slitwidth,
                # defaultは1.0で、これは画面幅の1%に相当する。
                slit_pos=self.params.slitpos,
                head_right=idx < 0,
            )
            self.canvas.put_image((absx, absy), cropped, linear_alpha=alpha)

    def stitch(self):
        logger = getLogger()
        for num, den in self.before():
            pass
        for num, den in self.loop():
            pass
        self.canvas.close()

    def loop(self):
        while self._onestep():
            yield self.getProgress()

    def _onestep(self):
        if len(self.locations) == 0:
            return False
        while self.currentFrame + 1 < self.locations[0][0]:
            self.currentFrame = self.vl.skip()
            if self.currentFrame == 0:
                return False
        self.currentFrame, frame = self.vl.next()
        if self.currentFrame == 0:
            return False
        self.add_image(frame, *self.locations[0][1:])
        self.locations.pop(0)
        if len(self.locations) == 0:
            return False
        return True  # not end


if __name__ == "__main__":
    debug = True
    if debug:
        basicConfig(
            level=DEBUG,
            # filename='log.txt',
            format="%(asctime)s %(levelname)s %(message)s",
        )
    else:
        basicConfig(level=INFO, format="%(asctime)s %(levelname)s %(message)s")
    st = Stitcher(argv=sys.argv)

    st.stitch()
    # st.make_a_big_picture()
