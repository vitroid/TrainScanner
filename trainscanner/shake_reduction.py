# ムービーを読みこみ、画像を縮小し、ピクセルごとの明暗の時系列を作る。

import cv2
import numpy as np
import sys
from dataclasses import dataclass
import logging
from trainscanner import standardize, subpixel_match, Region, trim_region


@dataclass
class Focus:
    region: Region
    shift: tuple[int, int]
    subpixel_shift: tuple[float, float]
    match_area: np.ndarray


def antishake(
    video_iter, foci: list[Region], max_shift=10, logfile=None, show_snapshot=None
):
    """最初のフレームの、指定された領域内の画像が動かないように、各フレームを平行移動する。

    全自動で位置あわせしたいのだが、現実的には、列車のすぐそばで位置あわせしないと、列車のぶれを止めきれない。

    2箇所指定した場合は、1個目が固定位置、2個目は回転補正用とする。
    3箇所以上指定された場合はもっと調節できるが、必要が生じてから考える。
    """
    logger = logging.getLogger()
    frame0 = next(video_iter)
    gray0 = cv2.cvtColor(frame0, cv2.COLOR_BGR2GRAY)

    assert 0 < len(foci) <= 2

    foci_ = []
    for f in foci:
        crop = standardize(gray0[f.top : f.bottom, f.left : f.right].astype(float))
        focus = Focus(
            region=f, shift=(0, 0), match_area=crop, subpixel_shift=(0.0, 0.0)
        )
        foci_.append(focus)

    foci = foci_

    # frame0上にmatch_areaを長方形で描画する。
    if logfile is not None:
        logfile.write(f"{len(foci)}\n")
    for focus in foci:
        region = focus.region
        cv2.rectangle(
            frame0,
            (region.left, region.top),
            (region.right, region.bottom),
            (0, 0, 255),
            2,
        )
        if logfile is not None:
            logfile.write(
                f"{region.left} {region.top} {region.right} {region.bottom}\n"
            )
    # cv2.imshow("match_areas", frame0)

    for frame2 in video_iter:
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY).astype(np.int32)

        for fi, focus in enumerate(foci):
            # 基準画像のfocusの位置。
            region = Region(
                left=focus.region.left,
                top=focus.region.top,
                right=focus.region.right,
                bottom=focus.region.bottom,
            )
            logger.info(f"{region=}")
            # 直前のフレームで、focusの位置を移動した。
            region.left += focus.shift[0] - max_shift
            region.top += focus.shift[1] - max_shift
            region.right += focus.shift[0] + max_shift
            region.bottom += focus.shift[1] + max_shift
            logger.info(f"{region=} {gray2.shape=}")
            # 照合したい画像のうち、マッチングに使う領域を切り取るための枠。
            # 初期値0は平均値を意味する。
            target_area = np.zeros(
                [region.bottom - region.top, region.right - region.left],
                dtype=np.float32,
            )
            # 画面外に出てしまわない範囲を計算する。
            trimmed_region = trim_region(region, gray2.shape)
            logger.info(f"{trimmed_region=}")
            # 照合したい画像のうち、マッチングに使う領域を切り取る。
            # 画面外の領域は0になる。
            target_area[
                trimmed_region.top - region.top : trimmed_region.bottom - region.top,
                trimmed_region.left - region.left : trimmed_region.right - region.left,
            ] = standardize(
                gray2[
                    trimmed_region.top : trimmed_region.bottom,
                    trimmed_region.left : trimmed_region.right,
                ].astype(float)
            )

            logger.info(f"{target_area.shape=} {focus.match_area.shape=}")
            min_loc, fractional_shift, _ = subpixel_match(target_area, focus.match_area)

            accel = (min_loc[0] - max_shift, min_loc[1] - max_shift)
            focus.shift = (focus.shift[0] + accel[0], focus.shift[1] + accel[1])
            focus.subpixel_shift = fractional_shift
        if len(foci) == 1:
            # cv2.imshow(
            #     "match_area", np.abs(focus.match_area - match_area).astype(np.uint8)
            # )
            m = foci[0]
            if logfile is not None:
                logfile.write(f"{m.shift[0]} {m.shift[1]}\n")
            translation_matrix = np.eye(3)
            translation_matrix[0, 2] = -m.shift[0] - m.subpixel_shift[0]
            translation_matrix[1, 2] = -m.shift[1] - m.subpixel_shift[1]
            frame2_shifted = cv2.warpAffine(
                frame2,
                translation_matrix[:2],
                frame2.shape[1::-1],
            )
            if show_snapshot is not None:
                annotated = frame2_shifted.copy()
                for focus in foci:
                    region = focus.region
                    cv2.rectangle(
                        annotated,
                        (region.left, region.top),
                        (region.right, region.bottom),
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
                    foci[0].region.top + foci[0].region.bottom,
                    foci[0].region.left + foci[0].region.right,
                ]
            )
            / 2
        )
        center1 = (
            np.array(
                [
                    foci[1].region.top + foci[1].region.bottom,
                    foci[1].region.left + foci[1].region.right,
                ]
            )
            / 2
        )
        angle = np.arctan2(center1[1] - center0[1], center1[0] - center0[0])

        # 平行移動後のmatch_areaの中心
        displaced0 = (
            center0 + np.array(foci[0].shift) + np.array(foci[0].subpixel_shift)
        )
        displaced1 = (
            center1 + np.array(foci[1].shift) + np.array(foci[1].subpixel_shift)
        )
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
                region = focus.region
                cv2.rectangle(
                    annotated,
                    (region.left, region.top),
                    (region.right, region.bottom),
                    (0, 0, 255),
                    2,
                )
            show_snapshot(annotated)
        yield frame2_rotated


def main(
    filename="/Users/matto/Dropbox/ArtsAndIllustrations/Stitch tmp2/antishake test/Untitled.mp4",
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
                Region(left=1520, right=1670, top=430, bottom=510),
                Region(left=100, right=200, top=465, bottom=515),
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
