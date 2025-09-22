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
from trainscanner import (
    trainscanner,
    diffview,
    FramePosition,
    MatchResult,
)
from trainscanner import video, match, find_subimage
from tiffeditor import Rect, Range


def draw_slit_position(img, slitpos, dx):
    """
    cv2形式の画像の中にスリットマーカーを描く
    """
    h, w = img.shape[0:2]
    if dx > 0:
        x1 = w // 2 + slitpos * w // 1000
        x2 = x1 - dx
    else:
        x1 = w // 2 - slitpos * w // 1000
        x2 = x1 - dx
    cv2.line(img, (x1, 0), (x1, h), (0, 255, 0), 1)
    cv2.line(img, (x2, 0), (x2, h), (0, 255, 0), 1)


# @debug_log
def motion(
    image,
    ref,
    focus: Rect = Rect(
        x_range=Range(min_val=333, max_val=666), y_range=Range(min_val=333, max_val=666)
    ),
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
    template_rect = Rect(
        x_range=Range(
            min_val=wi * focus.left // 1000,
            max_val=wi * focus.right // 1000,
        ),
        y_range=Range(
            min_val=hi * focus.top // 1000,
            max_val=hi * focus.bottom // 1000,
        ),
    )
    template = ref[
        template_rect.top : template_rect.bottom,
        template_rect.left : template_rect.right,
        :,
    ]
    # gray_template = standardize(cv2.cvtColor(template, cv2.COLOR_BGR2GRAY))
    h, w = template.shape[0:2]

    # Apply template Matching
    if maxaccel is None:
        # maxaccelは指定されていない場合は、画像全体がマッチング対象になる。
        hop = 1
        if yfixed:
            # x方向にのみずらして照合する。
            image = image[
                template_rect.y_range.min_val : template_rect.y_range.max_val, :, :
            ]
            # max_loc, fractional_shift, max_val = subpixel_match(
            #     image, template, subpixel=False
            # )
            max_loc, max_val = match(image, template)
            # max_locはtemplateの左上角を原点とした相対座標なので、xminを引く。
            max_loc = (
                max_loc[0] - template_rect.left,
                max_loc[1],
            )
            return max_loc, hop, max_val

        # max_loc, fractional_shift, max_val = subpixel_match(
        #     image, template, subpixel=False
        # )
        max_loc, max_val = match(image, template)
        max_loc = (
            max_loc[0] - template_rect.left,
            max_loc[1] - template_rect.top,
        )
        # print(min_loc)
        return max_loc, hop, max_val
    else:
        maxmax_loc = None
        maxmax_val = 0
        maxmax_hop = 0
        maxmax_fra = None
        for hop in range(1, dropframe + 2):
            # subpixel_matchingする時に必要なマージン
            fit_margins = [min(2, maxaccel[0]), min(2, maxaccel[1])]

            # 探査する範囲。整数にしておく。
            roix0 = int(np.floor(template_rect.left + delta[0] * hop - maxaccel[0]))
            roiy0 = int(np.floor(template_rect.top + delta[1] * hop - maxaccel[1]))
            roix1 = int(np.ceil(template_rect.right + delta[0] * hop + maxaccel[0]))
            roiy1 = int(np.ceil(template_rect.bottom + delta[1] * hop + maxaccel[1]))
            rect = Rect(
                x_range=Range(min_val=roix0, max_val=roix1),
                y_range=Range(min_val=roiy0, max_val=roiy1),
            )

            result = find_subimage(
                image,
                template,
                rect,
                relative=False,
                fit_margins=fit_margins,
                subpixel=False,  # あんまり正確じゃないので、とりあえず封印する。
            )
            if result is None:
                continue
            max_loc, fractional_shift, max_val = result
            # max_loc, max_val = match(gray_crop, gray_template)
            if maxmax_val < max_val:
                maxmax_loc = max_loc
                maxmax_val = max_val
                maxmax_hop = hop
                maxmax_fra = fractional_shift

        new_delta = (
            maxmax_loc[0] + maxmax_fra[0] - template_rect.left,
            maxmax_loc[1] + maxmax_fra[1] - template_rect.top,
        )
        # dropframeがあった場合、2倍や3倍の移動が検出される。
        # new_deltaには変位をそのまま返すが、同時に倍率も返す。
        if maxmax_hop != 1:
            logger.info(f"Skipped frames: {maxmax_hop-1}")
        return new_delta, maxmax_hop, maxmax_val


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
        default=0,
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


class historyQueue:
    def __init__(self, maxlen: int):
        self.queue = []
        self.maxlen = maxlen

    def append(self, item):
        self.queue.append(item)
        if len(self.queue) > self.maxlen:
            self.queue.pop(0)

    def fluctuation(self):
        return max(self.queue) - min(self.queue)


def valid_focus(focus: Rect):
    try:
        focus.validate()
        return True
    except ValueError:
        return False


def iter2(
    videoloader,
    focus: Rect,
    transform: trainscanner.transformation,
    coldstart: bool = False,
    yfixed: bool = False,
    dropframe: int = 0,
    maxaccel: int = 1,
    identity: float = 1.0,
    antishake: int = 5,
    last: int = 0,
    hook=None,
    stop_callback=None,
):
    logger = getLogger()

    nframe, rawframe = videoloader.next()
    # All self variables to be inherited.
    _, _, cropped = transform.process_first_image(rawframe)
    # あとでcanvas の計算に使うために、frameの幅と高さを保存しておく。
    frame_width, frame_height = cropped.shape[1], cropped.shape[0]
    # Prepare a scalable self.canvas with the origin.
    # self.canvas = None

    absx, absy = 0, 0
    velx, vely = 0, 0
    match_fail = 0
    in_action = False
    # coldstartの場合は、変化の大きさに関わらず、変位を記録する。
    # そして、変位がantishakeを越えたあとは、通常と同じように判定する。

    motions_plot = []  # リアルタイムプロット用のデータ
    velx_history = historyQueue(5)  # store velocities
    vely_history = historyQueue(5)  # store velocities

    if not valid_focus(focus):
        return

    while True:
        # 停止チェック
        if stop_callback and stop_callback():
            logger.info("停止が要求されました")
            break

        lastrawframe = rawframe
        lastframe = cropped
        # もしlastが設定されていて，しかもframe数がそれを越えていれば，終了．
        if last > 0 and last < nframe + 1:
            break
        # 1フレームとりこみ
        nframe, rawframe = videoloader.next()
        if nframe == 0:
            logger.debug("Video ended (2).")
            break
        ##### compare with the previous raw frame
        diff = cv2.absdiff(rawframe, lastrawframe)
        # When the raw frame is not changed at all, ignore the frame.
        # It happens in the frame rate adjustment between PAL and NTSC
        diff = np.sum(diff) / np.prod(diff.shape)
        if diff < identity:
            logger.info("skip identical frame #{0}".format(diff))
            continue
        ##### Warping the frame
        _, _, cropped = transform.process_next_image(rawframe)
        ##### motion detection.
        # if maxaccel is set, motion detection area becomes very narrow
        # assuming that the train is running at constant speed.
        # This mode is activated after the 10th frames.

        # Now I do care only magrin case.
        if yfixed:
            accel = [maxaccel, 0]
        else:
            accel = [maxaccel, maxaccel]

        if in_action or coldstart:
            # 現在の速度に加え、加速度の範囲内で、マッチングを行う。
            logger.debug(f"velx: {velx} vely: {vely}")
            delta, hop, value = motion(
                lastframe,
                cropped,
                focus=focus,
                maxaccel=accel,
                delta=(velx, vely),
                dropframe=dropframe,
            )
            motions_plot.append([delta[0], delta[1], value])
            if delta is None:
                logger.error(
                    "Matching failed (probabily the motion detection window goes out of the image)."
                )
                break
        else:
            # 速度不明なので、広い範囲でマッチングを行う。
            delta, hop, value = motion(lastframe, cropped, focus=focus, yfixed=yfixed)
        hopx, hopy = delta
        velx, vely = delta[0] / hop, delta[1] / hop
        logger.debug(f"hop: {hop} velx: {velx} vely: {vely}")

        # ##### Suppress drifting.
        # if params.zero:
        #     dy = 0
        # 直近5フレームの移動量を記録する．
        # ここではhopの大きさ(dropframeのせいでときどき倍になる)ではなく、真の速度を記録する。
        velx_history.append(velx)
        vely_history.append(vely)
        ##### Make the preview image

        # Motion detectionロジック: in_actionの状態で大きく分岐
        motion_detected = abs(velx) >= antishake or abs(vely) >= antishake

        if in_action:
            # 既に動きを検出している状態
            if motion_detected:
                # 大きな動きが継続している - 変位をそのまま採用
                logger.debug(f"Accept the motion ({nframe} {velx} {vely})")
                match_fail = 0
            else:
                # 動きがantishake水準より小さくなった - 小さな動きを無視
                match_fail += 1
                logger.debug(f"Ignore a small motion ({nframe} {velx} {vely})")
                # TODO: match_failカウンターがparams.trailingに届いたら停止処理
                # if match_fail > trailing: break
        else:
            # まだ動きを検出していない状態
            if motion_detected:
                if coldstart:
                    # コールドスタート時は即座に動作開始
                    in_action = True
                    coldstart = False
                    logger.debug(f"Cold start motion detected ({nframe} {velx} {vely})")
                else:
                    # 通常時は安定性をチェック
                    fluctuation_x = velx_history.fluctuation()
                    fluctuation_y = vely_history.fluctuation()

                    if antishake <= fluctuation_x or antishake <= fluctuation_y:
                        # 変動が大きい - カメラが安定するまで待機
                        logger.debug(
                            f"Wait for the camera to stabilize ({nframe=} {velx=} {vely=} {fluctuation_x=} {fluctuation_y=})"
                        )
                    else:
                        # 速度が安定した - 記録開始
                        in_action = True
                        logger.debug(
                            f"The camera is stabilized. Now ready to start recording. {nframe=} {velx=} {vely=}"
                        )
                        # TODO: 過去にさかのぼってマッチングを行う
                        # self.tspos = self._backward_match(absx, absy, dx, dy, precount)

            else:
                # 動きが小さい - 静止フレームとして無視
                logger.debug(f"Still frame ({nframe} {velx} {vely})")
                match_fail = 0  # 動きを検出していない時はmatch_failをリセット

        logger.debug(f"Capture {nframe=} {velx=} {vely=} #{in_action=}")
        absx += hopx
        absy += hopy

        if hook is not None:
            matchresult = MatchResult(
                index=nframe, dt=hop, velocity=(velx, vely), value=value, image=cropped
            )
            hook(matchresult)

        if in_action:
            frameposition = FramePosition(index=nframe, dt=hop, velocity=(velx, vely))
            yield frameposition
    # end of capture


def add_trailing_frames(
    framepositions: list[FramePosition], dispose: int, estimate: int, extend: int
):
    """
    Add trailing frames to framepositions.

    framepositions: list[FramePosition]
    dispose: int # 捨てるフレーム数
    estimate: int # 事前の速度を予測するために用いるフレーム数
    extend: int # 外挿するフレーム数
    """

    # framepositionsの最後は速度が安定しないので捨てる。
    framepositions = framepositions[:-dispose]

    # 座標を抽出する
    dt = [fp.dt for fp in framepositions[-estimate:]]
    t = np.cumsum(dt)
    x = [fp.velocity[0] for fp in framepositions[-estimate:]]
    y = [fp.velocity[1] for fp in framepositions[-estimate:]]

    ax, bx = np.polyfit(t, x, 1)
    ay, by = np.polyfit(t, y, 1)

    t_extrapolated = np.linspace(
        t[-1] + 1,
        t[-1] + extend,
        extend,
        dtype=int,
    )
    x_extrapolated = ax * t_extrapolated + bx
    y_extrapolated = ay * t_extrapolated + by
    lastframe = framepositions[-1].index
    trailing_framepositions = [
        FramePosition(
            index=lastframe + t_extrapolated[i] - t[-1],
            dt=1,
            velocity=(x_extrapolated[i], y_extrapolated[i]),
        )
        for i in range(extend)
    ]
    return framepositions + trailing_framepositions


def add_leading_frames(
    framepositions: list[FramePosition], dispose: int, estimate: int, extend: int
):
    """
    Add leading frames to tspos.
    """

    # 最初は速度が安定しないので捨てる。
    framepositions = framepositions[dispose:]

    dt = [fp.dt for fp in framepositions[:estimate]]
    t = np.cumsum(dt)
    x = [fp.velocity[0] for fp in framepositions[:estimate]]
    y = [fp.velocity[1] for fp in framepositions[:estimate]]

    ax, bx = np.polyfit(t, x, 1)
    ay, by = np.polyfit(t, y, 1)

    t_extrapolated = np.linspace(
        -extend,
        -1,
        extend,
        dtype=int,
    )
    x_extrapolated = ax * t_extrapolated + bx
    y_extrapolated = ay * t_extrapolated + by
    firstframe = framepositions[0].index
    leading_framepositions = [
        FramePosition(
            index=firstframe + t_extrapolated[i],
            dt=1,
            velocity=(x_extrapolated[i], y_extrapolated[i]),
        )
        for i in range(extend)
    ]
    return leading_framepositions + framepositions


class Pass1:
    """
    ムービーを前から読んで，最終的なキャンバスの大きさと，各フレームを貼りつける位置を調べて，framepositionsファイルに書きだす．
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
                        self.tsconf += f"--{v[:equal]}\n{v[equal + 1 :]}\n"
                    else:
                        self.tsconf += f"--{v}\n"
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
                    self.tsconf += f"{option}\n{value}\n"
        # print(self.tsconf)
        # end of the header
        #############Open the video file #############################
        self.vl = video.video_loader_factory(found)

    def cue(self):
        """
        prepare for the loop
        note that it is a generator.
        """
        logger = getLogger()
        # self.nframes = 0  #1 is the first frame

        self.vl.seek(self.params.skip)
        # for i in range(self.params.skip):  # skip frames
        #     nframe = self.vl.skip()
        #     if nframe == 0:
        #         break
        #     yield nframe, self.params.skip  # report progress

    def run(self, hook=None, stop_callback=None):
        # for the compatibility
        logger = getLogger()
        focus = Rect(
            x_range=Range(min_val=self.params.focus[0], max_val=self.params.focus[1]),
            y_range=Range(min_val=self.params.focus[2], max_val=self.params.focus[3]),
        )
        transform = trainscanner.transformation(
            angle=self.params.rotate,
            pers=self.params.perspective,
            crop=self.params.crop,
        )
        self.framepositions: list[FramePosition] = [
            frameposition
            for frameposition in iter2(
                videoloader=self.vl,
                focus=focus,
                transform=transform,
                coldstart=self.params.stall,
                yfixed=self.params.zero,
                dropframe=self.params.dropframe,
                maxaccel=self.params.maxaccel,
                identity=self.params.identity,
                last=self.params.last,
                hook=hook,
                stop_callback=stop_callback,
            )
        ]

    def after(self):
        """
        Action after the loop
        """
        logger = getLogger()

        if len(self.framepositions) == 0:
            logger.error("No motion detected.")
            return

        self.framepositions = add_trailing_frames(
            framepositions=self.framepositions,
            estimate=self.params.estimate,
            dispose=self.params.estimate,
            extend=self.params.trailing,
        )
        self.framepositions = add_leading_frames(
            framepositions=self.framepositions,
            estimate=self.params.estimate,
            dispose=self.params.estimate,
            extend=self.params.trailing,
        )

        # self.tsconf += f"--canvas\n{canvas[0]}\n{canvas[1]}\n{canvas[2]}\n{canvas[3]}\n"
        if self.params.log is None:
            ostream = sys.stdout
        else:
            ostream = open(self.params.log + ".tsconf", "w")
        ostream.write(self.tsconf)
        if self.params.log is not None:
            ostream = open(self.params.log + ".tspos", "w")
        # tsposの内部形式は変えるが、data formatは変えない(今は)。
        for frameposition in self.framepositions:
            ostream.write(
                f"{frameposition.index} {frameposition.velocity[0]*frameposition.dt} {frameposition.velocity[1]*frameposition.dt}\n"
            )
        ostream.close()

        self.rawframe = None


def main():
    pass1 = Pass1(argv=sys.argv)
    v = diffview(
        focus=Rect(
            x_range=Range(
                min_val=pass1.params.focus[0],
                max_val=pass1.params.focus[1],
            ),
            y_range=Range(
                min_val=pass1.params.focus[2],
                max_val=pass1.params.focus[3],
            ),
        )
    )

    def show(matchresult: MatchResult):
        diff = v.view(matchresult)
        if diff is not None:
            cv2.imshow("pass1", diff)
            cv2.waitKey(0)

    # for num, den in pass1.cue():
    #     pass
    pass1.cue()
    pass1.run(hook=show)
    pass1.after()


if __name__ == "__main__":
    main()
