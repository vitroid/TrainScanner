#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import math
import sys
import os
import re
import itertools
from logging import getLogger, basicConfig, DEBUG, WARN, INFO
import argparse
from trainscanner import trainscanner
from trainscanner import video


def draw_focus_area(f, focus, delta=None):
    """
    cv2形式の画像の中に四角を描く
    """
    h, w = f.shape[0:2]
    pos = [
        w * focus[0] // 1000,
        w * focus[1] // 1000,
        h * focus[2] // 1000,
        h * focus[3] // 1000,
    ]
    cv2.rectangle(f, (pos[0], pos[2]), (pos[1], pos[3]), (0, 255, 0), 1)
    if delta is not None:
        dx, dy = delta
        pos = [
            w * focus[0] // 1000 + dx,
            w * focus[1] // 1000 + dx,
            h * focus[2] // 1000 + dy,
            h * focus[3] // 1000 + dy,
        ]
        cv2.rectangle(f, (pos[0], pos[2]), (pos[1], pos[3]), (255, 255, 0), 1)


def draw_slit_position(f, slitpos, dx):
    """
    cv2形式の画像の中にスリットマーカーを描く
    """
    h, w = f.shape[0:2]
    if dx > 0:
        x1 = w // 2 + slitpos * w // 1000
        x2 = x1 - dx
    else:
        x1 = w // 2 - slitpos * w // 1000
        x2 = x1 - dx
    cv2.line(f, (x1, 0), (x1, h), (0, 255, 0), 1)
    cv2.line(f, (x2, 0), (x2, h), (0, 255, 0), 1)


def motion(
    image, ref, focus=(333, 666, 333, 666), maxaccel=0, delta=(0, 0), antishake=2
):
    """
    ref画像のfocusで指定された領域内の画像と同じ画像をimage内で探して、その変位を返す。
    maxaccelとdeltaが指定されている場合は、探索範囲を絞り高速にマッチングできる。
    """
    logger = getLogger()
    hi, wi = ref.shape[0:2]
    wmin = wi * focus[0] // 1000
    wmax = wi * focus[1] // 1000
    hmin = hi * focus[2] // 1000
    hmax = hi * focus[3] // 1000
    template = ref[hmin:hmax, wmin:wmax, :]
    h, w = template.shape[0:2]

    # Apply template Matching
    if maxaccel == 0:
        res = cv2.matchTemplate(image, template, cv2.TM_SQDIFF_NORMED)
        # loc is given by x,y
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        return min_loc[0] - wmin, min_loc[1] - hmin
    else:
        # use delta here
        roix0 = wmin + delta[0] - maxaccel
        roiy0 = hmin + delta[1] - maxaccel
        roix1 = wmax + delta[0] + maxaccel
        roiy1 = hmax + delta[1] + maxaccel
        affine = np.matrix(((1.0, 0.0, -roix0), (0.0, 1.0, -roiy0)))
        logger.debug("maxaccel:{0} delta:{1}".format(maxaccel, delta))
        crop = cv2.warpAffine(image, affine, (roix1 - roix0, roiy1 - roiy0))
        # imageh,imagew = image.shape[0:2]
        # if roix0 < 0 or roix1 >= imagew or roiy0 < 0 or roiy1 >= imageh:
        #    print(roix0,roix1,roiy0,roiy1,imagew,imageh)
        #    return None
        # crop = image[roiy0:roiy1, roix0:roix1, :]
        res = cv2.matchTemplate(crop, template, cv2.TM_SQDIFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        # loc is given by x,y

        # Test: isn't it just a background?
        roix02 = wmin - antishake
        roiy02 = hmin - antishake
        roix12 = wmax + antishake
        roiy12 = hmax + antishake
        crop = image[roiy02:roiy12, roix02:roix12, :]
        res = cv2.matchTemplate(crop, template, cv2.TM_SQDIFF_NORMED)
        min_val2, max_val2, min_loc2, max_loc2 = cv2.minMaxLoc(res)
        # loc is given by x,y
        if min_val <= min_val2:
            return (min_loc[0] + roix0 - wmin, min_loc[1] + roiy0 - hmin)
        else:
            return (min_loc2[0] + roix02 - wmin, min_loc2[1] + roiy02 - hmin)


def diffImage(frame1, frame2, dx, dy):  # , focus=None, slitpos=None):
    """
    2枚のcv2画像の差を返す．
    """
    affine = np.matrix(((1.0, 0.0, dx), (0.0, 1.0, dy)))
    h, w = frame1.shape[0:2]
    frame1 = cv2.warpAffine(frame1, affine, (w, h))
    diff = 255 - cv2.absdiff(frame1, frame2)
    # if focus is not None:
    #     draw_focus_area(diff, focus, delta=(dx, dy))
    # if slitpos is not None:
    #     draw_slit_position(diff, slitpos, dx)
    return diff


# Automatically extensible canvas.
def canvas_size(canvas_dimen, image, x, y):
    """
    canvas_dimenで定義されるcanvasの，位置(x,y)にimageを貼りつけた場合の，拡張後のcanvasの大きさを返す．
    canvas_dimenはcanvasの左上角の絶対座標と，canvasの幅高さの4因子でできている．
    """
    x = int(x)
    y = int(y)
    if canvas_dimen is None:
        h, w = image.shape[:2]
        return w, h, x, y
    absx, absy = canvas_dimen[2:4]  # absolute coordinate of the top left of the canvas
    cxmin = absx
    cymin = absy
    cxmax = canvas_dimen[0] + absx
    cymax = canvas_dimen[1] + absy
    ixmin = x
    iymin = y
    ixmax = image.shape[1] + x
    iymax = image.shape[0] + y

    xmin = min(cxmin, ixmin)
    xmax = max(cxmax, ixmax)
    ymin = min(cymin, iymin)
    ymax = max(cymax, iymax)
    if (xmax - xmin, ymax - ymin) != (canvas_dimen[0], canvas_dimen[1]):
        canvas_dimen = [xmax - xmin, ymax - ymin, xmin, ymin]
    getLogger().debug(canvas_dimen)
    return canvas_dimen


def prepare_parser():
    """
    pass1のコマンドラインオプションのパーザ
    """
    parser = argparse.ArgumentParser(
        description="TrainScanner matcher",
    )
    parser.add_argument(
        "--debug", action="store_true", dest="debug", help="Show debug info."
    )
    parser.add_argument(
        "-z", "--zero", action="store_true", dest="zero", help="Suppress drift."
    )
    parser.add_argument(
        "-S",
        "--skip",
        "--start",
        type=int,
        metavar="N",
        default=0,
        dest="skip",
        help="Skip first N frames.",
    )
    parser.add_argument(
        "-L",
        "--last",
        type=int,
        metavar="N",
        default=0,
        dest="last",
        help="Specify the last frame.",
    )
    parser.add_argument(
        "-E",
        "--estimate",
        type=int,
        metavar="N",
        default=10,
        dest="estimate",
        help="Use first N frames for velocity estimation.",
    )
    parser.add_argument(
        "-p",
        "--perspective",  # do not allow "--pers"
        type=int,
        nargs=4,
        default=None,
        dest="perspective",
        help="Specity perspective warp.",
    )
    parser.add_argument(
        "-f",
        "--focus",
        type=int,
        nargs=4,
        default=[333, 666, 333, 666],
        dest="focus",
        help="Motion detection area relative to the image size.",
    )
    parser.add_argument(
        "-a",
        "--antishake",
        type=int,
        default=5,
        metavar="x",
        dest="antishake",
        help="Antishake.  Ignore motion smaller than x pixels.",
    )
    parser.add_argument(
        "-t",
        "--trail",
        type=int,
        default=10,
        dest="trailing",
        help="Trailing frames after the train runs away.",
    )
    parser.add_argument(
        "-r", "--rotate", type=int, default=0, dest="rotate", help="Image rotation."
    )
    parser.add_argument(
        "-e",
        "--every",
        type=int,
        default=1,
        dest="every",
        metavar="N",
        help="Load every N frames.",
    )
    parser.add_argument(
        "-i",
        "--identity",
        type=float,
        default=1.0,
        dest="identity",
        metavar="x",
        help="Decide the identity of two successive frames with the threshold.",
    )
    parser.add_argument(
        "-c",
        "--crop",
        type=int,
        nargs=2,
        default=[0, 1000],
        dest="crop",
        metavar="tb",
        help="Crop the image (top and bottom).",
    )
    parser.add_argument(
        "-x",
        "--stall",
        action="store_true",
        dest="stall",
        default=False,
        help="Train is initially stopping inside the motion detection area.",
    )
    parser.add_argument(
        "-m",
        "--maxaccel",
        type=int,
        default=1,
        dest="maxaccel",
        metavar="N",
        help="Interframe acceleration in pixels.",
    )
    parser.add_argument(
        "-2",
        "--option2",
        type=str,
        action="append",
        dest="option2",
        help="Additional option (just ignored in this program).",
    )
    parser.add_argument(
        "-l",
        "--log",
        type=str,
        dest="log",
        default=None,
        help="TrainScanner settings (.tsconf) file name.",
    )
    parser.add_argument("filename", type=str, help="Movie file name.")
    return parser


class Pass1:
    """
    ムービーを前から読んで，最終的なキャンバスの大きさと，各フレームを貼りつける位置を調べて，tsposファイルに書きだす．
    実際に大きな画像を作る作業はstitch.pyにまかせる．
    """

    def __init__(self, argv):
        logger = getLogger()
        self.parser = prepare_parser()
        self.params, unknown = self.parser.parse_known_args(argv[1:])
        if self.params.debug:
            basicConfig(
                level=DEBUG,
                # filename='log.txt',
                format="%(asctime)s %(levelname)s %(message)s",
            )
        else:
            basicConfig(level=INFO, format="%(asctime)s %(levelname)s %(message)s")
        # Assume the video is in the same dir.
        self.dirnames = []
        # if self.parser.fromfile_name is not None:
        #     logger.debug("Conf filename {0}".format(self.parser.fromfile_name))
        #     self.dirnames.append(os.path.dirname(self.parser.fromfile_name))
        self.dirnames.append(os.path.dirname(self.params.filename))
        # remove the dirname from the filename
        self.params.filename = os.path.basename(self.params.filename)
        logger.debug("Directory candidates: {0}".format(self.dirnames))

    def before(self):
        """
        prepare for the loop
        note that it is a generator.
        """
        logger = getLogger()
        ####Determine the movie file########################
        found = None
        logger.debug("Basename {0}".format(self.params.filename))
        # First we assume that the movie is in the same directory as tsconf if tsconf is specified.
        # Otherwise we look at the absolute path given in the command line or in the tsconf.
        for dirname in self.dirnames:
            filename = dirname + "/" + self.params.filename
            if os.path.exists(filename):
                found = filename
                break
        if not found:
            logger.error("File not found.")
        # update the file path
        self.params.filename = found
        logger.debug("Found filename {0}".format(found))
        ####prepare tsconf file#############################
        self.tsconf = ""
        args = trainscanner.deparse(self.parser, self.params)
        self.tsconf += "{0}\n".format(args["__UNNAMED__"])
        for option in args:
            value = args[option]
            if value is None or option in ("__UNNAMED__"):
                continue
            if option == "--option2":
                # Expand "key=value" to "--key\tvalue\n"
                for v in value:
                    equal = v.find("=")
                    if equal >= 0:
                        self.tsconf += "--{0}\n{1}\n".format(v[:equal], v[equal + 1 :])
                    else:
                        self.tsconf += "--{0}\n".format(v)
            else:
                if option in (
                    "--perspective",
                    "--focus",
                    "--crop",
                ):  # multiple values
                    self.tsconf += f"{option}\n"
                    for v in value:
                        self.tsconf += f"{v}\n"
                elif option in (
                    "--zero",
                    "--stall",
                ):
                    if value is True:
                        self.tsconf += option + "\n"
                else:
                    self.tsconf += "{0}\n{1}\n".format(option, value)
        # print(self.tsconf)
        # end of the header

        #############Open the video file #############################
        self.vl = video.video_loader_factory(found)
        # self.nframes = 0  #1 is the first frame

        for i in range(self.params.skip):  # skip frames
            nframe = self.vl.skip()
            if nframe == 0:
                break
            yield nframe, self.params.skip  # report progress
        nframe, frame = self.vl.next()
        if nframe == 0:
            logger.debug("End of film.")
            sys.exit(0)
        self.rawframe = frame
        self.lastnframe = nframe  # just for iter()

    def _add_trailing_frames(self):
        """
        Add trailing frames to tspos.
        """
        logger = getLogger()
        logger.info("Adding trailing frames to tspos.")

        if len(self.tspos) < self.params.estimate:
            return
        num_frames = self.params.trailing

        # 座標を抽出する
        t = [
            self.tspos[i][0]
            for i in range(len(self.tspos) - self.params.estimate, len(self.tspos))
        ]
        x = [
            self.tspos[i][1]
            for i in range(len(self.tspos) - self.params.estimate, len(self.tspos))
        ]
        y = [
            self.tspos[i][2]
            for i in range(len(self.tspos) - self.params.estimate, len(self.tspos))
        ]

        ax, bx = np.polyfit(t, x, 1)
        ay, by = np.polyfit(t, y, 1)

        # 外挿する
        t_extrapolated = np.linspace(
            t[-1] + 1,
            t[-1] + num_frames,
            num_frames,
            dtype=int,
        )
        x_extrapolated = (ax * t_extrapolated + bx).astype(int)
        y_extrapolated = (ay * t_extrapolated + by).astype(int)
        for i in range(num_frames):
            self.tspos.append([t_extrapolated[i], x_extrapolated[i], y_extrapolated[i]])

    def _add_leading_frames(self):
        """
        Add leading frames to tspos.
        """
        logger = getLogger()
        logger.info(f"Adding leading frames to tspos. {self.tspos}")

        if len(self.tspos) < self.params.estimate:
            return
        num_frames = self.params.trailing
        if self.tspos[0][0] < num_frames:
            num_frames = self.tspos[0][0]

        t = [self.tspos[i][0] for i in range(num_frames)]
        x = [self.tspos[i][1] for i in range(num_frames)]
        y = [self.tspos[i][2] for i in range(num_frames)]

        ax, bx = np.polyfit(t, x, 1)
        ay, by = np.polyfit(t, y, 1)

        t_extrapolated = np.linspace(
            t[0] - num_frames,
            t[0] - 1,
            num_frames,
            dtype=int,
        )
        x_extrapolated = (ax * t_extrapolated + bx).astype(int)
        y_extrapolated = (ay * t_extrapolated + by).astype(int)
        leading_tspos = []
        for i in range(num_frames):
            leading_tspos.append(
                [t_extrapolated[i], x_extrapolated[i], y_extrapolated[i]]
            )
        self.tspos = leading_tspos + self.tspos

    def valid_focus(self, focus):
        if focus is None:
            return False
        if focus[0] >= focus[1]:
            return False
        if focus[2] >= focus[3]:
            return False
        return True

    def iter(self):
        logger = getLogger()
        # All self variables to be inherited.
        rawframe = self.rawframe
        vl = self.vl
        params = self.params
        nframe = self.lastnframe

        transform = trainscanner.transformation(
            angle=params.rotate, pers=params.perspective, crop=params.crop
        )
        rotated, warped, cropped = transform.process_first_image(rawframe)
        # Prepare a scalable self.canvas with the origin.
        self.canvas = None

        absx, absy = 0, 0
        velx, vely = 0, 0
        match_fail = 0
        guess_mode = params.stall
        precount = 0
        preview_size = 500
        preview = trainscanner.fit_to_square(cropped, preview_size)
        preview_ratio = preview.shape[0] / cropped.shape[0]

        self.tspos = []
        self.cache = []  # save only "active" frames.
        deltax = []  # store displacements
        deltay = []  # store displacements

        if not self.valid_focus(params.focus):
            return

        while True:
            lastrawframe = rawframe
            lastframe = cropped
            lastpreview = preview
            # もしlastが設定されていて，しかもframe数がそれを越えていれば，終了．
            if params.skip < params.last < nframe + params.every:
                break
            # フレームの早送り
            for i in range(params.every - 1):
                nframe = vl.skip()
                if nframe == 0:
                    logger.debug("Video ended (1).")
                    break
            # 1フレームとりこみ
            nframe, rawframe = vl.next()
            if nframe == 0:
                logger.debug("Video ended (2).")
                break
            ##### compare with the previous raw frame
            diff = cv2.absdiff(rawframe, lastrawframe)
            # When the raw frame is not changed at all, ignore the frame.
            # It happens in the frame rate adjustment between PAL and NTSC
            diff = np.sum(diff) / np.prod(diff.shape)
            if diff < params.identity:
                logger.info("skip identical frame #{0}".format(diff))
                continue
            ##### Warping the frame
            _, _, cropped = transform.process_next_image(rawframe)
            ##### motion detection.
            # if maxaccel is set, motion detection area becomes very narrow
            # assuming that the train is running at constant speed.
            # This mode is activated after the 10th frames.

            # Now I do care only magrin case.
            if guess_mode:
                # do not apply maxaccel for the first 10 frames
                # because the velocity uncertainty.
                delta = motion(
                    lastframe,
                    cropped,
                    focus=params.focus,
                    maxaccel=params.maxaccel,
                    delta=(velx, vely),
                )
                if delta is None:
                    logger.error(
                        "Matching failed (probabily the motion detection window goes out of the image)."
                    )
                    break
                dx, dy = delta
            else:
                dx, dy = motion(lastframe, cropped, focus=params.focus)

            ##### Suppress drifting.
            if params.zero:
                dy = 0
            # 直近5フレームの移動量を記録する．
            deltax.append(dx)
            deltay.append(dy)
            if len(deltax) > 5:
                deltax.pop(0)
                deltay.pop(0)
            # 最大100フレームの画像を記録する．
            if cropped is not None and self.cache is not None:
                self.cache.append([nframe, cropped])
                if len(self.cache) > 100:  # always keep 100 frames in self.cache
                    self.cache.pop(0)
            ##### Make the preview image
            # preview = trainscanner.fit_to_square(cropped,preview_size)
            # diff_img = diffImage(preview,lastpreview,int(dx*preview_ratio),int(dy*preview_ratio),focus=params.focus)
            diff_img = diffImage(cropped, lastframe, int(dx), int(dy))
            diff_img = trainscanner.fit_to_square(diff_img, preview_size)
            draw_focus_area(
                diff_img,
                params.focus,
                delta=(int(dx * preview_ratio), int(dy * preview_ratio)),
            )
            # previewを表示
            yield diff_img
            ##### if the motion is large
            if abs(dx) >= params.antishake or abs(dy) >= params.antishake:
                if not guess_mode:
                    # number of frames since the first motion is detected.
                    precount += 1
                    # 過去5フレームでの移動量の変化
                    ddx = max(deltax) - min(deltax)
                    ddy = max(deltay) - min(deltay)
                    # if the displacements are almost constant in the last 5 frames,
                    if params.antishake <= ddx or params.antishake <= ddy:
                        logger.debug(
                            f"Wait for the camera to stabilize ({nframe} {dx} {dy})"
                        )
                        continue
                    else:
                        # 速度は安定した．
                        guess_mode = True
                        logger.debug(f"The camera is stabilized. {nframe} {dx} {dy}")
                        # この速度を信じ，過去にさかのぼってもう一度マッチングを行う．
                        # self.tspos = self._backward_match(absx, absy, dx, dy, precount)
                # 変位をそのまま採用する．
                logger.debug(f"Accept the motion ({nframe} {dx} {dy})")
                velx = dx
                vely = dy
                match_fail = 0
            else:
                if guess_mode:
                    # 動きがantishake水準より小さかった場合
                    match_fail += 1
                    # match_failカウンターがparams.trailingに届くまではそのまま回す．
                    if match_fail > params.trailing:
                        # end of work
                        # Add trailing frames to the log file here.

                        # ここで、マッチしはじめる前の部分と、マッチしおえたあとの部分を整える。

                        break
                    logger.info(
                        f"Ignore a small motion ({nframe} {dx} {dy} +{match_fail}/{params.trailing})"
                    )
                    # believe the last velx and vely
                else:
                    # not guess mode, not large motion: just ignore.
                    logger.info(f"Still frame ({nframe} {dx} {dy})")
                    continue

            logger.info(f"Capture {nframe} {velx} {vely} #{np.amax(diff)}")
            absx += velx
            absy += vely
            self.canvas = canvas_size(self.canvas, cropped, absx, absy)
            self.tspos.append([nframe, velx, vely])
        # end of capture

        # 最後の、match_failフレームを削除する。
        logger.debug(f"tspos before: {self.tspos} {match_fail}")
        if match_fail > 0:
            self.tspos = self.tspos[:-match_fail]
        logger.debug(f"tspos after: {self.tspos}")
        # 10枚ほど余分に削る。
        # self.tspos = self.tspos[:-10]
        # self.tspos = self.tspos[10:]

        self._add_trailing_frames()
        self._add_leading_frames()

    def after(self):
        """
        Action after the loop
        """
        logger = getLogger()
        if self.canvas is None or len(self.tspos) == 0:
            logger.error("No motion detected.")
            return
        self.tsconf += "--canvas\n{0}\n{1}\n{2}\n{3}\n".format(*self.canvas)
        if self.params.log is None:
            ostream = sys.stdout
        else:
            ostream = open(self.params.log + ".tsconf", "w")
        ostream.write(self.tsconf)
        if self.params.log is not None:
            ostream = open(self.params.log + ".tspos", "w")
        for t, x, y in self.tspos:
            ostream.write(f"{t} {x} {y}\n")
        ostream.close()

        self.rawframe = None


def main():
    pass1 = Pass1(argv=sys.argv)
    for num, den in pass1.before():
        pass
    for ret in pass1.iter():
        cv2.imshow("pass1", ret)
        cv2.waitKey(1)
    pass1.after()


if __name__ == "__main__":
    main()
