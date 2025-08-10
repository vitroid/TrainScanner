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
from trainscanner import video, standardize, subpixel_match, match


def draw_focus_area(f, focus, delta=None, active=False):
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
    if active:
        colors = [(0, 255, 0), (255, 255, 0)]
    else:
        colors = [(0, 128, 0), (128, 128, 0)]
    cv2.rectangle(f, (pos[0], pos[2]), (pos[1], pos[3]), colors[0], 1)
    if delta is not None:
        dx, dy = delta
        pos = [
            w * focus[0] // 1000 + dx,
            w * focus[1] // 1000 + dx,
            h * focus[2] // 1000 + dy,
            h * focus[3] // 1000 + dy,
        ]
        cv2.rectangle(f, (pos[0], pos[2]), (pos[1], pos[3]), colors[1], 1)


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
    image,
    ref,
    focus=(333, 666, 333, 666),
    maxaccel=None,
    delta=(0, 0),
    yfixed=False,
    dropframe=0,
):
    """
    ref画像のfocusで指定された領域内の画像と同じ画像をimage内で探して、その変位を返す。
    maxaccelとdeltaが指定されている場合は、探索範囲を絞り高速にマッチングできる。
    dropfameが0でない場合、N+1倍の移動がありうる。
    """
    logger = getLogger()
    hi, wi = ref.shape[0:2]
    xmin = wi * focus[0] // 1000
    xmax = wi * focus[1] // 1000
    ymin = hi * focus[2] // 1000
    ymax = hi * focus[3] // 1000
    template = ref[ymin:ymax, xmin:xmax, :]
    gray_template = standardize(cv2.cvtColor(template, cv2.COLOR_BGR2GRAY))
    h, w = template.shape[0:2]

    # Apply template Matching
    if maxaccel is None:
        # maxaccelは指定されていない場合は、画像全体がマッチング対象になる。
        if yfixed:
            # x方向にのみずらして照合する。
            image = image[ymin:ymax, :, :]
            # max_loc, fractional_shift, max_val = subpixel_match(
            #     image, template, subpixel=False
            # )
            max_loc, max_val = match(image, template)
            # max_locはtemplateの左上角を原点とした相対座標なので、xminを引く。
            max_loc = (max_loc[0] - xmin, max_loc[1])
            return max_loc

        # max_loc, fractional_shift, max_val = subpixel_match(
        #     image, template, subpixel=False
        # )
        max_loc, max_val = match(image, template)
        max_loc = (max_loc[0] - xmin, max_loc[1] - ymin)
        # print(min_loc)
        return max_loc
    else:
        maxmax_loc = None
        maxmax_val = 0
        maxmax_hop = 0
        for hop in range(1, dropframe + 2):

            # use delta here
            # print(f"maxaccel: {maxaccel} delta: {delta}")
            roix0 = xmin + delta[0] * hop - maxaccel[0]
            roiy0 = ymin + delta[1] * hop - maxaccel[1]
            # subpixel transformation
            affine = np.matrix(((1.0, 0.0, -roix0), (0.0, 1.0, -roiy0)))
            logger.debug(f"maxaccel:{maxaccel} delta:{delta}")
            crop = cv2.warpAffine(
                image,
                affine,
                (xmax - xmin + 2 * maxaccel[0], ymax - ymin + 2 * maxaccel[1]),
            )
            gray_crop = standardize(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY))

            # res = cv2.matchTemplate(gray_crop, gray_template, cv2.TM_SQDIFF_NORMED)
            # min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            fit_width = [2, 2]
            if maxaccel[0] < 2:
                fit_width[0] = maxaccel[0]
            if maxaccel[1] < 2:
                fit_width[1] = maxaccel[1]

            # max_loc, fractional_shift, max_val = subpixel_match(
            #     gray_crop, gray_template, fit_width=fit_width  # , subpixel=False
            # )
            max_loc, max_val = match(gray_crop, gray_template)
            logger.info(f"{hop=} {max_loc=} {max_val=} ")
            if maxmax_val < max_val:
                maxmax_loc = max_loc
                maxmax_val = max_val
                maxmax_hop = hop

        roix0 = xmin + delta[0] * maxmax_hop - maxaccel[0]
        roiy0 = ymin + delta[1] * maxmax_hop - maxaccel[1]

        new_delta = (
            maxmax_loc[0] + roix0 - xmin,
            maxmax_loc[1] + roiy0 - ymin,
        )
        # dropframeがあった場合、2倍や3倍の移動が検出される。
        # new_deltaには変位をそのまま返すが、同時に倍率も返す。
        return new_delta, maxmax_hop


def diffImage(frame1, frame2, dx, dy, mode="stack"):  # , focus=None, slitpos=None):
    """
    2枚のcv2画像の差を返す．
    """
    if mode == "diff":
        affine = np.matrix(((1.0, 0.0, dx), (0.0, 1.0, dy)))
        h, w = frame1.shape[0:2]
        std2 = standardize(frame2)
        frame1 = cv2.warpAffine(frame1, affine, (w, h))
        std1 = standardize(frame1)
        diff = (255 * cv2.absdiff(std1, std2)).astype(np.uint8)
        # if focus is not None:
        #     draw_focus_area(diff, focus, delta=(dx, dy))
        # if slitpos is not None:
        #     draw_slit_position(diff, slitpos, dx)
        return diff
    elif mode == "stack":
        affine = np.matrix(((1.0, 0.0, dx), (0.0, 1.0, dy)))
        h, w = frame1.shape[0:2]
        flags = np.arange(h) * 16 % h > h // 2
        frame1 = cv2.warpAffine(frame1, affine, (w, h))
        frame1[flags] = frame2[flags]
        return frame1


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
        "-D",
        "--dropframe",
        type=int,
        default=2,
        metavar="N",
        help="Maximum number of dropped frames accepted.",
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
        in_action = False
        # coldstartの場合は、変化の大きさに関わらず、変位を記録する。
        # そして、変位がantishakeを越えたあとは、通常と同じように判定する。
        coldstart = params.stall
        precount = 0
        preview_size = 500
        preview = trainscanner.fit_to_square(cropped, preview_size)
        preview_ratio = preview.shape[0] / cropped.shape[0]

        self.tspos = []
        self.cache = []  # save only "active" frames.
        velx_history = []  # store velocities
        vely_history = []  # store velocities

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
            maxaccel = [params.maxaccel, params.maxaccel]
            if params.zero:
                maxaccel = [params.maxaccel, 0]
            if in_action or coldstart:
                # 現在の速度に加え、加速度の範囲内で、マッチングを行う。
                logger.info(f"velx: {velx} vely: {vely}")
                delta, hop = motion(
                    lastframe,
                    cropped,
                    focus=params.focus,
                    maxaccel=maxaccel,
                    delta=(velx, vely),
                    dropframe=params.dropframe,
                )
                if delta is None:
                    logger.error(
                        "Matching failed (probabily the motion detection window goes out of the image)."
                    )
                    break
                hopx, hopy = delta
                velx, vely = delta[0] / hop, delta[1] / hop
                logger.info(f"hop: {hop} velx: {velx} vely: {vely}")
            else:
                # 速度不明なので、広い範囲でマッチングを行う。
                velx, vely = motion(
                    lastframe, cropped, focus=params.focus, yfixed=params.zero
                )
                hopx, hopy = velx, vely

            # ##### Suppress drifting.
            # if params.zero:
            #     dy = 0
            # 直近5フレームの移動量を記録する．
            # ここではhopの大きさ(dropframeのせいでときどき倍になる)ではなく、真の速度を記録する。
            velx_history.append(velx)
            vely_history.append(vely)
            if len(velx_history) > 5:
                velx_history.pop(0)
                vely_history.pop(0)
            # 最大100フレームの画像を記録する．
            if cropped is not None and self.cache is not None:
                self.cache.append([nframe, cropped])
                if len(self.cache) > 100:  # always keep 100 frames in self.cache
                    self.cache.pop(0)
            ##### Make the preview image
            # preview = trainscanner.fit_to_square(cropped,preview_size)
            # diff_img = diffImage(preview,lastpreview,int(dx*preview_ratio),int(dy*preview_ratio),focus=params.focus)
            diff_img = diffImage(cropped, lastframe, int(hopx), int(hopy))
            diff_img = trainscanner.fit_to_square(diff_img, preview_size)
            draw_focus_area(
                diff_img,
                params.focus,
                delta=(int(hopx * preview_ratio), int(hopy * preview_ratio)),
                active=in_action,
            )
            # previewを表示
            yield diff_img
            ##### if the motion is larger than the params.antishake

            if coldstart:
                assert False, "まだ考えてない"
                if not in_action:
                    logger.debug(f"Accept the motion ({nframe} {dx} {dy})")
                    velx = dx
                    vely = dy
                    match_fail = 0

                if abs(dx) >= params.antishake or abs(dy) >= params.antishake:
                    if not in_action:
                        in_action = True
                        coldstart = False

            else:
                if abs(velx) >= params.antishake or abs(vely) >= params.antishake:
                    if not in_action:
                        # number of frames since the first motion is detected.
                        precount += 1
                        # 過去5フレームでの移動量の変化
                        ddx = max(velx_history) - min(velx_history)
                        ddy = max(vely_history) - min(vely_history)
                        # if the displacements are almost constant in the last 5 frames,
                        if params.antishake <= ddx or params.antishake <= ddy:
                            logger.info(
                                f"Wait for the camera to stabilize ({nframe=} {velx=} {vely=} {ddx=} {ddy=})"
                            )
                            continue
                        else:
                            # 速度は安定した．
                            in_action = True
                            # 十分変位が大きくなったらcoldstartフラグはおろす。
                            logger.info(
                                f"The camera is stabilized. {nframe=} {velx=} {vely=}"
                            )
                            # この速度を信じ，過去にさかのぼってもう一度マッチングを行う．
                            # self.tspos = self._backward_match(absx, absy, dx, dy, precount)
                    # 変位をそのまま採用する．
                    logger.debug(f"Accept the motion ({nframe} {velx} {vely})")
                    match_fail = 0
                else:
                    if in_action:
                        # 動きがantishake水準より小さかった場合
                        match_fail += 1
                        # match_failカウンターがparams.trailingに届くまではそのまま回す．
                        if match_fail > params.trailing:
                            # end of work
                            # Add trailing frames to the log file here.

                            # ここで、マッチしはじめる前の部分と、マッチしおえたあとの部分を整える。

                            break
                        logger.info(
                            f"Ignore a small motion ({nframe} {velx} {vely} +{match_fail}/{params.trailing})"
                        )
                        # believe the last velx and vely
                    else:
                        # not guess mode, not large motion: just ignore.
                        logger.info(f"Still frame ({nframe} {velx} {vely})")
                        continue

            logger.info(f"Capture {nframe=} {velx=} {vely=} #{in_action=}")
            absx += hopx
            absy += hopy
            self.canvas = canvas_size(self.canvas, cropped, absx, absy)
            self.tspos.append([nframe, hopx, hopy])
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
