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
from tiledimage import cachedimage as ci
from trainscanner import trainscanner
from trainscanner import video
from trainscanner.i18n import init_translations, tr


class AlphaMask:
    def __init__(self, img_width, slit=0, width=1.0):
        self.img_width = img_width
        self.width = width
        self.slitpos = slit * img_width // 1000
        self.alphas = dict()

    def make_linear_alpha(self, displace):
        """
        Make an orthogonal mask of only one line.
        slit position is -500 to 500
        slit width=1 is standard, width<1 is narrow (sharp) and width>1 is diffuse alpha
        """
        if displace in self.alphas:
            return self.alphas[displace]
        if displace == 0:
            self.alphas[0.0] = np.ones((self.img_width, 3))
            self.alphas[0] = self.alphas[0.0]
            return self.alphas[0]
        slitwidth = abs(int(displace * self.width))
        alpha = np.zeros((self.img_width, 3))
        if displace > 0:
            slitin = self.img_width // 2 - self.slitpos
            slitout = slitin + slitwidth
            alpha[slitout:, :] = 1.0
            alpha[slitin:slitout, :] = np.fromfunction(
                lambda x, v: x / slitwidth, (slitwidth, 3)
            )
        else:
            slitin = self.img_width // 2 + self.slitpos
            slitout = slitin - slitwidth
            alpha[:slitout, :] = 1.0
            alpha[slitout:slitin, :] = np.fromfunction(
                lambda x, v: (slitwidth - x) / slitwidth, (slitwidth, 3)
            )
        self.alphas[displace] = alpha
        return alpha


def prepare_parser(parser=None):
    if parser is None:
        # parser = myargparse.MyArgumentParser(description='TrainScanner stitcher')
        parser = argparse.ArgumentParser(description="TrainScanner stitcher")
    parser.add_argument(
        "-C",
        "--canvas",
        type=int,
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
        help="Slit mixing width.",
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

    def __init__(self, argv):
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
        self.outfilename = tsconfdir + "/" + tsconfbase + ".png"
        self.cachedir = tsconfdir + "/" + tsconfbase + ".pngs"  # if required
        if not os.path.exists(moviefile):
            moviefile = moviepath
        logger.info("TSPos  {0}".format(self.tsposfile))
        logger.info("Movie  {0}".format(moviefile))
        logger.info("Output {0}".format(self.outfilename))

        self.vl = video.video_loader_factory(moviefile)
        self.firstFrame = True
        self.currentFrame = 0  # 1 is the first frame

        self.R = None
        self.M = None
        self.transform = trainscanner.transformation(
            self.params.rotate, self.params.perspective, self.params.crop
        )
        # initialization of the super class
        # logger.info("scale:{0}".format(self.params.scale))
        # logger.info("length:{0}".format(self.params.length))
        if self.params.scale == 1 and self.params.length > 0:
            # product length is specified.
            # scale is overridden
            self.params.scale = self.params.length / self.params.canvas[0]
            if self.params.scale > 1:
                self.params.scale = 1  # do not allow stretching
            # for GUI
        self.dimen = [int(x * self.params.scale) for x in self.params.canvas]

    # Canvas should be set after the arguments are parsed.
    def set_canvas(self, canvas):
        self.canvas = canvas

    def before(self):
        """
        is a generator.
        """
        logger = getLogger()
        locations = []
        absx = 0
        absy = 0
        tspos = open(self.tsposfile)
        for line in tspos.readlines():
            if len(line) > 0 and line[0] != "@":
                cols = [int(x) for x in line.split()]
                if len(cols) > 0:
                    absx += cols[1]
                    absy += cols[2]
                    cols = [cols[0], absx, absy] + cols[1:]
                    cols[1:] = [int(x * self.params.scale) for x in cols[1:]]
                    locations.append(cols)
        self.locations = locations
        self.total_frames = len(locations)
        if len(locations) == 0:
            return
        # initial seek
        while self.currentFrame + 1 < self.locations[0][0]:
            logger.debug((self.currentFrame, self.locations[0][0]))
            yield self.currentFrame, self.locations[0][0]
            self.currentFrame = self.vl.skip()

    def getProgress(self):
        den = self.total_frames
        num = den - len(self.locations)
        return (num, den)

    def add_image(self, frame, absx, absy, idx, idy):
        rotated, warped, cropped = self.transform.process_image(frame)
        if self.firstFrame:
            self.canvas.put_image((absx, absy), cropped)
            self.mask = AlphaMask(
                cropped.shape[1], slit=self.params.slitpos, width=self.params.slitwidth
            )
            self.firstFrame = False
        else:
            alpha = self.mask.make_linear_alpha(int(idx))
            self.canvas.put_image((absx, absy), cropped, linear_alpha=alpha)

    def stitch(self):
        logger = getLogger()
        for num, den in self.before():
            pass
        for num, den in self.loop():
            logger.info(num / den)
        # while result is None:
        #    result = self.onestep()
        # self.canvas.done()

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
        if self.params.scale != 1:
            frame = cv2.resize(frame, None, fx=self.params.scale, fy=self.params.scale)
        self.add_image(frame, *self.locations[0][1:])
        self.locations.pop(0)
        if len(self.locations) == 0:
            return False
        return True  # not end

    def make_a_big_picture(self):
        """
        This is an optional process.
        """
        file_name = self.outfilename
        # It costs high when using the CachedImage.
        img = self.canvas.get_image()
        cv2.imwrite(file_name, img)


if __name__ == "__main__":
    debug = False
    if debug:
        basicConfig(
            level=DEBUG,
            # filename='log.txt',
            format="%(asctime)s %(levelname)s %(message)s",
        )
    else:
        basicConfig(level=INFO, format="%(asctime)s %(levelname)s %(message)s")
    st = Stitcher(argv=sys.argv)

    tilesize = (512, 512)  # canbe smaller for smaller machine
    cachesize = 10
    canvas = ci.CachedImage(
        "new", dir=st.cachedir, tilesize=tilesize, cachesize=cachesize
    )
    st.set_canvas(canvas)

    st.stitch()
    st.make_a_big_picture()
