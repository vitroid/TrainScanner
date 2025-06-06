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


def antishake(video_iter, foci, max_shift=5, logfile=None):
    """最初のフレームの、指定された領域内の画像が動かないように、各フレームを平行移動する。

    全自動で位置あわせしたいのだが、現実的には、列車のすぐそばで位置あわせしないと、列車のぶれを止めきれない。

    2箇所指定した場合は、1個目が固定位置、2個目は回転補正用とする。
    3箇所以上指定された場合はもっと調節できるが、必要が生じてから考える。
    """

    frame0 = next(video_iter)
    gray0 = cv2.cvtColor(frame0, cv2.COLOR_BGR2GRAY)

    assert 0 < len(foci) <= 2

    match_areas = []
    for f in foci:
        x, y, w, h = f
        crop = gray0[y : y + h, x : x + w].astype(np.int32)
        focus = Focus(rect=(x, y, w, h), shift=(0, 0), match_area=crop)
        match_areas.append(focus)

    # frame0上にmatch_areaを長方形で描画する。
    if logfile is not None:
        logfile.write(f"{len(foci)}\n")
    for focus in match_areas:
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

        for focus in match_areas:
            max_diff = 1e99
            best = None
            for dx in range(focus.shift[0] - max_shift, focus.shift[0] + max_shift + 1):
                for dy in range(
                    focus.shift[1] - max_shift, focus.shift[1] + max_shift + 1
                ):
                    x, y, w, h = focus.rect
                    x += dx
                    y += dy
                    top, bottom, left, right = paddings(x, y, w, h, gray2.shape)
                    match_area = gray2[
                        y + top : y + h - bottom, x + left : x + w - right
                    ]
                    original_area = focus.match_area[top : h - bottom, left : w - right]
                    diff = np.mean((original_area - match_area) ** 2)
                    # print(dx, dy, diff, focus.match_area.shape, match_area.shape)
                    if diff < max_diff:
                        max_diff = diff
                        best = (dx, dy)

            focus.shift = best
            # print(best)
        if logfile is not None:
            logfile.write(f"{focus.shift[0]} {focus.shift[1]}\n")
        if len(match_areas) == 1:
            # cv2.imshow(
            #     "match_area", np.abs(focus.match_area - match_area).astype(np.uint8)
            # )
            m = match_areas[0]
            yield np.roll(
                frame2,
                (-m.shift[1], -m.shift[0]),
                axis=(0, 1),
            )
            continue
        # 2箇所の場合。

        # もとのmatch_areaの中心
        center0 = (
            np.array(match_areas[0].rect[:2]) + np.array(match_areas[0].rect[2:]) / 2
        )
        center1 = (
            np.array(match_areas[1].rect[:2]) + np.array(match_areas[1].rect[2:]) / 2
        )
        angle = np.arctan2(center1[1] - center0[1], center1[0] - center0[0])

        # 平行移動後のmatch_areaの中心
        displaced0 = center0 + np.array(match_areas[0].shift)
        displaced1 = center1 + np.array(match_areas[1].shift)
        angle2 = np.arctan2(
            displaced1[1] - displaced0[1], displaced1[0] - displaced0[0]
        )

        # 角度変化
        angle_diff = angle2 - angle
        # frame2をまず-match_area[0].shiftだけ平行移動する。
        # これにより、displace[0]がcenter0と重なる。
        frame2_shifted = np.roll(
            frame2,
            (-match_areas[0].shift[1], -match_areas[0].shift[0]),
            axis=(0, 1),
        )

        # center0を中心として回転する
        scale = 1.0
        rotation_matrix = cv2.getRotationMatrix2D(
            center0, np.degrees(angle_diff), scale
        )

        yield cv2.warpAffine(
            frame2_shifted,
            rotation_matrix,
            frame2.shape[1::-1],
        )


def main(filename="/Users/matto/Dropbox/ArtsAndIllustrations/Stitch tmp2/Untitled.mp4"):

    for frame in antishake(
        video_iter(filename),
        [(1520, 430, 150, 80), (100, 465, 100, 50)],
    ):
        cv2.imshow("deshaked", frame)
        cv2.waitKey(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()
