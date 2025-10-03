#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass
import cv2
import numpy as np
import math
import sys
import os
import re
import itertools
from logging import getLogger, basicConfig, DEBUG, WARN, INFO
import argparse
from trainscanner import FramePosition
from trainscanner.image import (
    deparse,
    diffview,
    standardize,
    Transformation,
    match,
    MatchScore,
    PreMatchScore,
    MatchResult,
)
from trainscanner import video
from pyperbox import Rect, Range


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


def displacements(
    new_image,
    old_image,
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
    old_height, old_width = old_image.shape[0:2]
    template_rect = Rect(
        x_range=Range(
            min_val=old_width * focus.left // 1000,
            max_val=old_width * focus.right // 1000,
        ),
        y_range=Range(
            min_val=old_height * focus.top // 1000,
            max_val=old_height * focus.bottom // 1000,
        ),
    )
    template = old_image[
        template_rect.top : template_rect.bottom,
        template_rect.left : template_rect.right,
    ]
    new_height, new_width = new_image.shape[0:2]
    match_area = Rect.from_bounds(0, new_width, 0, new_height)

    # Apply template Matching
    if maxaccel is None:
        # maxaccelは指定されていない場合は、画像全体がマッチング対象になる。
        hop = 1
        if yfixed:
            # x方向にのみずらして照合する。
            match_area = Rect.from_bounds(
                0, new_width, template_rect.top, template_rect.bottom
            )
        subimage = new_image[
            match_area.top : match_area.bottom, match_area.left : match_area.right
        ]

        # matchは座標換算つき照合
        return match(subimage, match_area, template, template_rect)

    else:
        match_scores = {}
        # maxmax_loc = None
        # maxmax_val = 0
        # maxmax_hop = 0
        # maxmax_fra = None
        for hop in range(1, dropframe + 2):
            # subpixel_matchingする時に必要なマージン
            fit_margins = [min(2, maxaccel[0]), min(2, maxaccel[1])]

            # 探査する範囲。整数にしておく。
            roix0 = int(np.floor(template_rect.left + delta[0] * hop - maxaccel[0]))
            roiy0 = int(np.floor(template_rect.top + delta[1] * hop - maxaccel[1]))
            roix1 = int(np.ceil(template_rect.right + delta[0] * hop + maxaccel[0]))
            roiy1 = int(np.ceil(template_rect.bottom + delta[1] * hop + maxaccel[1]))
            match_area = Rect(
                x_range=Range(min_val=roix0, max_val=roix1),
                y_range=Range(min_val=roiy0, max_val=roiy1),
            )

            subimage = new_image[
                match_area.top : match_area.bottom, match_area.left : match_area.right
            ]
            match_score = match(subimage, match_area, template, template_rect)
            match_scores[hop] = match_score
        return match_scores


def prepare_parser():
    """
    pass1のコマンドラインオプションのパーザ
    """
    parser = argparse.ArgumentParser(
        description="TrainScanner matcher",
    )
    parser.add_argument("--debug", action="store_true", help="Show debug info.")
    parser.add_argument("-z", "--zero", action="store_true", help="Suppress drift.")
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

    @property
    def length(self):
        return len(self.queue)


def valid_focus(focus: Rect):
    try:
        focus.validate()
        return True
    except ValueError:
        return False


def iterations(
    videoloader,
    focus: Rect,
    transform: Transformation,
    coldstart: bool = False,
    yfixed: bool = False,
    dropframe: int = 0,
    maxaccel: int = 1,
    identity: float = 1.0,
    antishake: int = 5,
    estimate: int = 10,
    last: int = 0,
    hook=None,
    stop_callback=None,
):
    logger = getLogger()

    rawframe = None
    cropped = None

    absx, absy = 0, 0
    velx, vely = 0, 0
    match_fail = 0
    in_action = False
    # coldstartの場合は、変化の大きさに関わらず、変位を記録する。
    # そして、変位がantishakeを越えたあとは、通常と同じように判定する。

    motions_plot = []  # リアルタイムプロット用のデータ
    velx_history = historyQueue(estimate)  # store velocities
    vely_history = historyQueue(estimate)  # store velocities

    if not valid_focus(focus):
        return

    framepositions = []
    prematches = []

    while True:
        # 停止チェック
        if stop_callback and stop_callback():
            logger.info("停止が要求されました")
            break

        lastrawframe = rawframe
        lastframe = cropped
        # もしlastが設定されていて，しかもframe数がそれを越えていれば，終了．
        if 0 < last < videoloader.head:
            break
        # 1フレームとりこみ
        rawframe = videoloader.next()
        if rawframe is None:
            logger.debug("Video ended (2).")
            break
        ##### compare with the previous raw frame
        if lastrawframe is None:
            _, _, cropped = transform.process_first_image(rawframe)
            continue

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
            match_scores = displacements(
                lastframe,
                cropped,
                focus=focus,
                maxaccel=accel,
                delta=(velx, vely),
                dropframe=dropframe,
            )
            # dropframeの数だけscoresが帰ってくるので、その中の最大のものをさがしたいのだが、もっと簡単にしたいなあ。
            maxmax_val = 0
            maxmax_loc = None
            maxmax_hop = 0
            for hop in match_scores:
                scores = match_scores[hop].value
                _, maxval, _, maxloc = cv2.minMaxLoc(scores)
                if maxmax_val <= maxval:
                    maxmax_val = maxval
                    maxmax_hop = hop
                    maxmax_loc = maxloc
            delta = (
                match_scores[maxmax_hop].dx[maxmax_loc[0]],
                match_scores[maxmax_hop].dy[maxmax_loc[1]],
            )
            hop = maxmax_hop
            value = maxmax_val
            motions_plot.append([delta[0], delta[1], value])
            if delta is None:
                logger.error(
                    "Matching failed (probabily the motion detection window goes out of the image)."
                )
                break
        else:
            # 速度不明なので、広い範囲でマッチングを行う。
            match_score = displacements(lastframe, cropped, focus=focus, yfixed=yfixed)
            # あとで、focus突入時の速度予測に使う。
            prematches.append(
                PreMatchScore(
                    frame_index=videoloader.head - 1,
                    dx=match_score.dx,
                    dy=match_score.dy,
                    value=match_score.value,
                )
            )
            _, maxval, _, maxloc = cv2.minMaxLoc(match_score.value)
            # print(dx.shape, dy.shape, scores.shape, maxloc)
            delta = (match_score.dx[maxloc[0]], match_score.dy[maxloc[1]])
            hop = 1
            value = maxval
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
                logger.debug(f"Accept the motion ({videoloader.head-1} {velx} {vely})")
                match_fail = 0
            else:
                # 動きがantishake水準より小さくなった - 小さな動きを無視
                match_fail += 1
                logger.debug(
                    f"Ignore a small motion ({videoloader.head-1} {velx} {vely})"
                )
                # TODO: match_failカウンターがparams.trailingに届いたら停止処理
                # if match_fail > trailing: break
        else:
            # まだ動きを検出していない状態
            if motion_detected:
                if coldstart:
                    # コールドスタート時は即座に動作開始
                    in_action = True
                    coldstart = False
                    logger.debug(
                        f"Cold start motion detected ({videoloader.head-1} {velx} {vely})"
                    )
                else:
                    # 通常時は安定性をチェック
                    fluctuation_x = velx_history.fluctuation()
                    fluctuation_y = vely_history.fluctuation()

                    if (
                        antishake <= fluctuation_x
                        or antishake <= fluctuation_y
                        or velx_history.length < estimate
                    ):
                        # 変動が大きい - カメラが安定するまで待機
                        logger.debug(
                            f"Wait for the camera to stabilize ({videoloader.head-1=} {velx=} {vely=} {fluctuation_x=} {fluctuation_y=})"
                        )
                    else:
                        # 速度が安定した - 記録開始
                        in_action = True
                        logger.debug(
                            f"The camera is stabilized. Now ready to start recording. {videoloader.head-1=} {velx=} {vely=}"
                        )
                        # TODO: 過去にさかのぼってマッチングを行う
                        # self.tspos = self._backward_match(absx, absy, dx, dy, precount)

            else:
                # 動きが小さい - 静止フレームとして無視
                logger.debug(f"Still frame ({videoloader.head-1} {velx} {vely})")
                match_fail = 0  # 動きを検出していない時はmatch_failをリセット

        logger.debug(f"Capture {videoloader.head-1=} {velx=} {vely=} #{in_action=}")
        absx += hopx
        absy += hopy

        if hook is not None:
            matchresult = MatchResult(
                index=videoloader.head - 1,
                dt=hop,
                velocity=(velx, vely),
                value=value,
                image=cropped,
            )
            hook(matchresult)

        if in_action:
            frameposition = FramePosition(
                index=videoloader.head - 1, dt=hop, velocity=(velx, vely)
            )
            framepositions.append(frameposition)
    return framepositions, prematches
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
    framepositions: list[FramePosition],
    prepatches: list[PreMatchScore],
    accel: int = 1,
    yfixed: bool = False,
    dropframe: int = 0,
):
    """
    Add leading frames to tspos.

    外挿ではなく、prepatchesを使って、速度を予測する。
    """
    reversed = prepatches[::-1]
    xaccel = accel
    yaccel = accel
    if yfixed:
        yaccel = 0

    vx, vy = framepositions[0].velocity
    frame_index = framepositions[0].index
    # まず、1フレームだけ予測を書いてみる。
    # prematchesの最後のフレームは、最初のvx, vyを予測したものに一致するはず。
    assert reversed[0].frame_index == frame_index
    # vx, vy周辺でのピークをさがす。
    # print(reversed[0].value.shape)
    reversed.pop(0)

    leading_frames = []

    for prematchscore in reversed:
        frame_index = prematchscore.frame_index
        # dx, dyはscoresの目盛り、等間隔
        dx = prematchscore.dx
        dy = prematchscore.dy
        scores = prematchscore.value

        maxmax_hop = 0
        maxmax_val = 0
        maxmax_loc = None
        for hop in range(1, dropframe + 2):
            dx_min = int(vx * hop - dx[0] - xaccel)
            dx_max = int(vx * hop - dx[0] + xaccel + 1)
            dy_min = int(vy * hop - dy[0] - yaccel)
            dy_max = int(vy * hop - dy[0] + yaccel + 1)

            # print(scores.shape)
            # print(dx_min, dx_max, dy_min, dy_max)
            minval, maxval, minloc, maxloc = cv2.minMaxLoc(
                scores[dy_min:dy_max, dx_min:dx_max]
            )
            # print(minval, maxval, minloc, maxloc)
            if maxmax_val < maxval:
                maxmax_hop = hop
                maxmax_loc = maxloc
                maxmax_val = maxval
        delta = (maxmax_loc[0] - xaccel, maxmax_loc[1] - yaccel)
        # print(f"{delta=}")
        vx += delta[0]
        vy += delta[1]

        leading_frames.append(
            FramePosition(index=frame_index, dt=maxmax_hop, velocity=(vx, vy))
        )

    return leading_frames[::-1] + framepositions


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
        args = deparse(self.parser, self.params)
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
                    "--debug",
                ):
                    if value is True:
                        self.tsconf += option + "\n"
                else:
                    self.tsconf += f"{option}\n{value}\n"
        # print(self.tsconf)
        # end of the header
        #############Open the video file #############################
        self.vl = video.video_loader_factory(found)

        self.focus = Rect.from_bounds(
            self.params.focus[0],
            self.params.focus[1],
            self.params.focus[2],
            self.params.focus[3],
        )
        self.v = diffview(focus=self.focus)
        self.diff_image = None

    def cue(self):
        """
        prepare for the loop
        note that it is a generator.
        """
        logger = getLogger()
        self.vl.seek(self.params.skip)

    def diff_update(self, matchresult: MatchResult):
        self.diff_image = self.v.view(matchresult)

    def run(self, hook=None, stop_callback=None):
        # for the compatibility
        logger = getLogger()
        # hook = self.diff_update
        transform = Transformation(
            angle=self.params.rotate,
            pers=self.params.perspective,
            crop=self.params.crop,
        )
        if hook is None:
            hook = self.diff_update
        self.framepositions, self.prematches = iterations(
            videoloader=self.vl,
            focus=self.focus,
            transform=transform,
            coldstart=self.params.stall,
            yfixed=self.params.zero,
            dropframe=self.params.dropframe,
            maxaccel=self.params.maxaccel,
            identity=self.params.identity,
            estimate=self.params.estimate,
            last=self.params.last,
            hook=hook,
            stop_callback=stop_callback,
        )

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
            prepatches=self.prematches,
            accel=self.params.maxaccel,
            yfixed=self.params.zero,
            dropframe=self.params.dropframe,
        )

        # self.tsconf += f"--canvas\n{canvas[0]}\n{canvas[1]}\n{canvas[2]}\n{canvas[3]}\n"
        if self.params.log is None:
            ostream = sys.stdout
        else:
            ostream = open(self.params.log + ".tsconf", "w", encoding="utf-8")
        ostream.write(self.tsconf)
        if self.params.log is not None:
            ostream = open(self.params.log + ".tspos", "w", encoding="utf-8")
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
        ),
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
