# ムービーを読みこみ、画像を縮小し、ピクセルごとの明暗の時系列を作る。

import cv2
import numpy as np
import sys
from dataclasses import dataclass
import logging
from trainscanner.image import standardize, match
from pyperbox import Rect, Range


@dataclass
class Focus:
    rect: Rect
    shift: tuple[int, int]
    subpixel_shift: tuple[float, float]
    match_area: np.ndarray


def antishake(
    video_iter, foci: list[Rect], max_shift=10, logfile=None, show_snapshot=None
):
    """最初のフレームの、指定された領域内の画像が動かないように、各フレームを平行移動する。

    全自動で位置あわせしたいのだが、現実的には、列車のすぐそばで位置あわせしないと、列車のぶれを止めきれない。

    2箇所指定した場合は、1個目が固定位置、2個目は回転補正用とする。
    3箇所以上指定された場合はもっと調節できるが、必要が生じてから考える。
    """
    logger = logging.getLogger()
    frame0 = next(video_iter)
    gray0 = cv2.cvtColor(frame0, cv2.COLOR_BGR2GRAY)
    std_gray0 = standardize(gray0)

    assert 0 < len(foci) <= 2

    foci_ = []
    for f in foci:
        crop = standardize(gray0[f.top : f.bottom, f.left : f.right].astype(float))
        focus = Focus(rect=f, shift=(0, 0), match_area=crop, subpixel_shift=(0.0, 0.0))
        foci_.append(focus)

    foci = foci_

    # frame0上にmatch_areaを長方形で描画する。
    if logfile is not None:
        logfile.write(f"{len(foci)}\n")
    for focus in foci:
        rect = focus.rect
        cv2.rectangle(
            frame0,
            (rect.left, rect.top),
            (rect.right, rect.bottom),
            (0, 0, 255),
            2,
        )
        if logfile is not None:
            logfile.write(f"{rect.left} {rect.top} {rect.right} {rect.bottom}\n")
    # cv2.imshow("match_areas", frame0)

    for frame2 in video_iter:
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY).astype(np.int32)
        std_gray2 = standardize(gray2)

        for fi, focus in enumerate(foci):
            # 基準画像のfocusの位置。
            rect = Rect.from_bounds(
                focus.rect.left + focus.shift[0] - max_shift,
                focus.rect.right + focus.shift[0] + max_shift,
                focus.rect.top + focus.shift[1] - max_shift,
                focus.rect.bottom + focus.shift[1] + max_shift,
            )
            # 直前のフレームで、focusの位置を移動した。
            # 照合したい画像のうち、マッチングに使う領域を切り取るための枠。
            # 初期値0は平均値を意味する。
            # 画面外に出てしまわない範囲を計算する。
            trimmed_rect = rect.trim(gray2.shape)
            trimmed_std_gray2 = std_gray2[
                trimmed_rect.top : trimmed_rect.bottom,
                trimmed_rect.left : trimmed_rect.right,
            ]
            matchscore = match(
                trimmed_std_gray2, trimmed_rect, focus.match_area, focus.rect
            )
            _, _, _, maxloc = cv2.minMaxLoc(matchscore.value)

            focus.shift = (matchscore.dx[maxloc[0]], matchscore.dy[maxloc[1]])
        if len(foci) == 1:
            # cv2.imshow(
            #     "match_area", np.abs(focus.match_area - match_area).astype(np.uint8)
            # )
            m = foci[0]
            if logfile is not None:
                logfile.write(f"{m.shift[0]} {m.shift[1]}\n")
            translation_matrix = np.eye(3)
            translation_matrix[0, 2] = -m.shift[0]  # - m.subpixel_shift[0]
            translation_matrix[1, 2] = -m.shift[1]  # - m.subpixel_shift[1]
            frame2_shifted = cv2.warpAffine(
                frame2,
                translation_matrix[:2],
                frame2.shape[1::-1],
            )
            if show_snapshot is not None:
                annotated = frame2_shifted.copy()
                for focus in foci:
                    rect = focus.rect
                    cv2.rectangle(
                        annotated,
                        (rect.left, rect.top),
                        (rect.right, rect.bottom),
                        (0, 0, 255),
                        2,
                    )
                show_snapshot(annotated)
            yield frame2_shifted
            continue
        # 2箇所の場合。

        # もとのmatch_areaの中心
        center0 = (
            np.array(
                [
                    foci[0].rect.top + foci[0].rect.bottom,
                    foci[0].rect.left + foci[0].rect.right,
                ]
            )
            / 2
        )
        center1 = (
            np.array(
                [
                    foci[1].rect.top + foci[1].rect.bottom,
                    foci[1].rect.left + foci[1].rect.right,
                ]
            )
            / 2
        )
        angle = np.arctan2(center1[1] - center0[1], center1[0] - center0[0])

        # 平行移動後のmatch_areaの中心
        displaced0 = center0 + np.array(foci[0].shift)
        displaced1 = center1 + np.array(foci[1].shift)
        angle2 = np.arctan2(
            displaced1[1] - displaced0[1], displaced1[0] - displaced0[0]
        )

        # 角度変化
        angle_diff = angle2 - angle
        # まず、displace0が画像の左上にくるように平行移動する。
        # 画面の左上に関して回転するため。
        height, width = frame0.shape[:2]
        translation_matrix = np.eye(3)
        translation_matrix[0, 2] = -displaced0[0]
        translation_matrix[1, 2] = -displaced0[1]

        scale = 1.0
        rotation_matrix23 = cv2.getRotationMatrix2D(
            center0, np.degrees(angle_diff), scale
        )
        rotation_matrix = np.eye(3)
        rotation_matrix[:2, :2] = rotation_matrix23[:2, :2]

        # 画面の左上が、center0にくるように平行移動する。
        translation2_matrix = np.eye(3)
        translation2_matrix[0, 2] = center0[0]
        translation2_matrix[1, 2] = center0[1]

        # 縦ベクトルをうしろからかける形式。
        affine_matrix = translation2_matrix @ rotation_matrix @ translation_matrix
        # center0を中心として回転する
        if logfile is not None:
            logfile.write(f"{foci[0].shift[1], foci[0].shift[0]} {angle_diff}\n")

        frame2_rotated = cv2.warpAffine(
            frame2,
            affine_matrix[:2],
            (width, height),
        )
        if show_snapshot is not None:
            annotated = frame2_rotated.copy()
            for focus in foci:
                rect = focus.rect
                cv2.rectangle(
                    annotated,
                    (rect.left, rect.top),
                    (rect.right, rect.bottom),
                    (0, 0, 255),
                    2,
                )
            show_snapshot(annotated)
        yield frame2_rotated


def main(
    filename="/Users/matto/Dropbox/ArtsAndIllustrations/Stitch tmp2/TrainScannerWorkArea/他人の動画/antishake test/Untitled.mp4",
):
    from trainscanner.video import video_iter
    import os

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # makedirs
    os.makedirs(f"{os.path.basename(filename)}.dir", exist_ok=True)
    logfile = open(f"{os.path.basename(filename)}.dir/log.txt", "w")
    viter = video_iter(filename)
    for i, frame in enumerate(
        antishake(
            viter,
            # foci=[(1520, 430, 150, 80), (100, 465, 100, 50)],  # for Untitled.mp4
            foci=[
                Rect(
                    x_range=Range(min_val=1520, max_val=1670),
                    y_range=Range(min_val=430, max_val=510),
                ),
                Rect(
                    x_range=Range(min_val=100, max_val=200),
                    y_range=Range(min_val=465, max_val=515),
                ),
            ],  # for Untitled.mp4
            # foci=[
            #     (1520, 430, 150, 80),
            # ],  # for Untitled.mp4
            # foci=[(400, 768, 80, 139), (1089, 746, 178, 134)],
        )
    ):
        cv2.imwrite(f"{os.path.basename(filename)}.dir/{i:06d}.png", frame)
        cv2.imshow("deshaked", frame)
        cv2.waitKey(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()
