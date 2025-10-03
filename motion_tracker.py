# motions.jsonは2次元の数値配列の時間変化を含む。(実際にはMatchScore形式のデータクラス)
# これを読みこみ、極大を複数見付けだし、その移動を追跡する。、
# 極大の個数はとりあえず最大で3個。

import json
from trainscanner.image import MatchScore
import numpy as np
import matplotlib.pyplot as plt
from pyperbox import Rect, Range


def find_peaks(arr: np.ndarray, rect: Rect, height: float = 0.5):
    assert rect.width == arr.shape[1]
    assert rect.height == arr.shape[0]
    centers = arr[1:-1, 1:-1]
    non_max = np.zeros_like(centers, dtype=bool)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx or dy:
                cmp = (
                    arr[
                        1 + dy : centers.shape[0] + 1 + dy,
                        1 + dx : centers.shape[1] + 1 + dx,
                    ]
                    > centers
                )

                non_max |= cmp
    is_max = ~non_max
    for y, x in np.argwhere(is_max):
        if arr[y + 1, x + 1] > height:
            yield x - rect.left + 1, y - rect.top + 1, arr[y + 1, x + 1]


with open("motions.json", "r") as f:
    motions = json.load(f)


# 持続するpeak。番号は出現順でつける。
persistent = {}
n_persistent = 0

for motion in motions:
    matchscore = MatchScore(
        dx=eval(motions[motion]["dx"]),
        dy=eval(motions[motion]["dy"]),
        value=np.array(motions[motion]["value"]),
    )

    # 高さが0.5以上の極大の位置を推定する。
    # random_scores = np.random.random([5, 5])
    peaks = {
        (x, y): value
        for x, y, value in sorted(
            find_peaks(
                matchscore.value,
                Rect.from_bounds(
                    0, matchscore.value.shape[1], 0, matchscore.value.shape[0]
                ),
                height=0.5,
            ),
            key=lambda x: x[2],
            reverse=True,
        )[:3]
    }
    # persistentに直前までのピーク位置の履歴が保存されていて、
    # それぞれの新しい位置をカルマンフィルタで予測する。
    for p in persistent.keys():
        persistent[p].predict()
    # 個々のpeakについて、
    # 追跡しているpeak(
    # の延長線上に極めて近い場所にあるなら、
    # それを
    print(peaks)
    # とりあえず、matchscore.valueを2次元の等高線で表示したい。
    # x軸とy軸の範囲はmatchscore.dxとmatchscore.dyから決める。
    x = np.linspace(matchscore.dx[0], matchscore.dx[-1], matchscore.value.shape[1])
    y = np.linspace(matchscore.dy[0], matchscore.dy[-1], matchscore.value.shape[0])
    # 値そのものをグラデーション表示
    # 位置をあわせる。
    X, Y = np.meshgrid(x, y)

    # imshowとcontourの座標系を統一
    plt.figure(figsize=(10, 8))

    # imshowで背景画像を表示（extentで座標範囲を指定）
    im = plt.imshow(
        matchscore.value,
        cmap="jet",
        extent=[
            matchscore.dx[0],
            matchscore.dx[-1],
            matchscore.dy[-1],
            matchscore.dy[0],
        ],  # y軸は反転
        aspect="auto",
        alpha=0.8,
    )

    # contourで等高線を重ねて描画
    contours = plt.contour(X, Y, matchscore.value, colors="white", linewidths=1.5)
    plt.clabel(contours, inline=True, fontsize=8)

    # カラーバーを追加（imshowの色情報を使用）
    plt.colorbar(im, label="Match Score Value")

    # 軸ラベルとタイトル
    plt.xlabel("dx")
    plt.ylabel("dy")
    plt.title(f"Motion Analysis: {motion}")

    plt.show()
    # print(np.min(matchscore.value), np.max(matchscore.value))
