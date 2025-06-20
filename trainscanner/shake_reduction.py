# ムービーを読みこみ、画像を縮小し、ピクセルごとの明暗の時系列を作る。

import cv2
import numpy as np
import sys
from dataclasses import dataclass


@dataclass
class Focus:
    rect: tuple[int, int, int, int]  # x, y, w, h
    shift: tuple[int, int]
    match_area: np.ndarray


def paddings(x, y, w, h, shape):
    top = max(0, -y)
    bottom = max(0, y + h - shape[0])
    left = max(0, -x)
    right = max(0, x + w - shape[1])
    return top, bottom, left, right


def standardize(x):
    return ((x - np.mean(x)) / np.std(x)).astype(np.float32)


def antishake(video_iter, foci, max_shift=10, logfile=None, show_snapshot=None):
    """最初のフレームの、指定された領域内の画像が動かないように、各フレームを平行移動する。

    全自動で位置あわせしたいのだが、現実的には、列車のすぐそばで位置あわせしないと、列車のぶれを止めきれない。

    2箇所指定した場合は、1個目が固定位置、2個目は回転補正用とする。
    3箇所以上指定された場合はもっと調節できるが、必要が生じてから考える。
    """

    frame0 = next(video_iter)
    gray0 = cv2.cvtColor(frame0, cv2.COLOR_BGR2GRAY)

    assert 0 < len(foci) <= 2

    foci_ = []
    for f in foci:
        x, y, w, h = f
        crop = standardize(gray0[y : y + h, x : x + w].astype(float))
        focus = Focus(rect=(x, y, w, h), shift=(0, 0), match_area=crop)
        foci_.append(focus)

    foci = foci_

    # frame0上にmatch_areaを長方形で描画する。
    if logfile is not None:
        logfile.write(f"{len(foci)}\n")
    for focus in foci:
        x, y, w, h = focus.rect
        cv2.rectangle(
            frame0,
            (x, y),
            (x + w, y + h),
            (0, 0, 255),
            2,
        )
        if logfile is not None:
            logfile.write(f"{x} {y} {w} {h}\n")
    # cv2.imshow("match_areas", frame0)

    for frame2 in video_iter:
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY).astype(np.int32)

        for focus in foci:
            x, y, w, h = focus.rect
            x += focus.shift[0]
            y += focus.shift[1]
            top, bottom, left, right = paddings(x, y, w, h, gray2.shape)
            target_area = np.zeros(
                [h + max_shift * 2 + 1, w + max_shift * 2 + 1], dtype=np.float32
            )
            target_area[
                max_shift + top : h + max_shift - bottom,
                max_shift + left : max_shift + w - right,
            ] = standardize(
                gray2[y + top : y + h - bottom, x + left : x + w - right].astype(float)
            )
            scores = cv2.matchTemplate(target_area, focus.match_area, cv2.TM_SQDIFF)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(scores)
            focus.shift = (
                focus.shift[0] + min_loc[0] - max_shift,
                focus.shift[1] + min_loc[1] - max_shift,
            )
            # print(best)
        if len(foci) == 1:
            # cv2.imshow(
            #     "match_area", np.abs(focus.match_area - match_area).astype(np.uint8)
            # )
            if logfile is not None:
                logfile.write(f"{focus.shift[0]} {focus.shift[1]}\n")
            m = foci[0]
            frame2_shifted = np.roll(
                frame2,
                (-m.shift[1], -m.shift[0]),
                axis=(0, 1),
            )
            if show_snapshot is not None:
                annotated = frame2_shifted.copy()
                for focus in foci:
                    x, y, w, h = focus.rect
                    cv2.rectangle(
                        annotated,
                        (x, y),
                        (x + w, y + h),
                        (0, 0, 255),
                        2,
                    )
                show_snapshot(annotated)
            yield frame2_shifted
            continue
        # 2箇所の場合。

        # もとのmatch_areaの中心
        center0 = np.array(foci[0].rect[:2]) + np.array(foci[0].rect[2:]) / 2
        center1 = np.array(foci[1].rect[:2]) + np.array(foci[1].rect[2:]) / 2
        angle = np.arctan2(center1[1] - center0[1], center1[0] - center0[0])

        # 平行移動後のmatch_areaの中心
        displaced0 = center0 + np.array(foci[0].shift)
        displaced1 = center1 + np.array(foci[1].shift)
        angle2 = np.arctan2(
            displaced1[1] - displaced0[1], displaced1[0] - displaced0[0]
        )

        # 角度変化
        angle_diff = angle2 - angle
        # frame2をまず-match_area[0].shiftだけ平行移動する。
        # これにより、displace[0]がcenter0と重なる。
        frame2_shifted = np.roll(
            frame2,
            (-foci[0].shift[1], -foci[0].shift[0]),
            axis=(0, 1),
        )

        # center0を中心として回転する
        scale = 1.0
        rotation_matrix = cv2.getRotationMatrix2D(
            center0, np.degrees(angle_diff), scale
        )
        if logfile is not None:
            logfile.write(f"{foci[0].shift[1], foci[0].shift[0]} {angle_diff}\n")

        frame2_rotated = cv2.warpAffine(
            frame2_shifted,
            rotation_matrix,
            frame2.shape[1::-1],
        )
        if show_snapshot is not None:
            annotated = frame2_rotated.copy()
            for focus in foci:
                x, y, w, h = focus.rect
                cv2.rectangle(
                    annotated,
                    (x, y),
                    (x + w, y + h),
                    (0, 0, 255),
                    2,
                )
            show_snapshot(annotated)
        yield frame2_rotated


def main(filename="/Users/matto/Dropbox/ArtsAndIllustrations/Stitch tmp2/Untitled.mp4"):
    from trainscanner.video import video_iter

    viter = video_iter(filename)
    for frame in antishake(
        viter,
        # [(1520, 430, 150, 80), (100, 465, 100, 50)], # for Untitled.mp4
        foci=[(400, 768, 80, 139), (1089, 746, 178, 134)],
    ):

        cv2.imshow("deshaked", frame)
        cv2.waitKey(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()
