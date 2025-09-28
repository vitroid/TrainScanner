import cv2
import numpy as np
from trainscanner.image import standardize
import sys
from matplotlib import pyplot as plt
from scipy.signal import find_peaks

# from sklearn.mixture import GaussianMixture
import matplotlib as mpl
from test_antishake2 import AntiShaker2


def find_2d_peaks(scores, num_peaks=4, min_distance=5):
    """
    2次元配列から高い順にピーク位置を検出する

    Args:
        scores: 2次元のスコア配列
        num_peaks: 検出するピーク数（デフォルト4）
        min_distance: ピーク間の最小距離

    Returns:
        peaks: [(y, x), ...] のリスト（高い順）
    """
    # 方法1: 各行でピークを検出
    all_peaks = []

    for i, row in enumerate(scores):
        # 1次元のピーク検出
        peaks_x, properties = find_peaks(
            row, height=np.mean(scores), distance=min_distance
        )
        heights = properties["peak_heights"]

        # 各ピークの座標と高さを記録
        for x, height in zip(peaks_x, heights):
            all_peaks.append((height, i, x))  # (高さ, y座標, x座標)

    # 各列でもピークを検出
    for j in range(scores.shape[1]):
        col = scores[:, j]
        peaks_y, properties = find_peaks(
            col, height=np.mean(scores), distance=min_distance
        )
        heights = properties["peak_heights"]

        # 各ピークの座標と高さを記録
        for y, height in zip(peaks_y, heights):
            all_peaks.append((height, y, j))  # (高さ, y座標, x座標)

    # 重複を除去（近い位置のピークを統合）
    unique_peaks = []
    for height, y, x in sorted(all_peaks, reverse=True):
        is_duplicate = False
        for _, uy, ux in unique_peaks:
            if abs(y - uy) <= min_distance and abs(x - ux) <= min_distance:
                is_duplicate = True
                break
        if not is_duplicate:
            unique_peaks.append((height, y, x))

    # 高い順にソートして上位num_peaks個を取得
    top_peaks = [(y, x) for _, y, x in unique_peaks[:num_peaks]]

    return top_peaks


# 残像マスクはけっこううまくいくみたい。
# 昼間の撮影ならこれだけでほとんど解決するかも。
# もうすこしadaptiveにしたい。動く部分と動かない部分の判定とか。
# gmmで分ける? うまくいっているかどうかわからん。
# maskは、動く部分をうまく抽出しているので、本来なら極大をさがすだけで速度推定できる。
class BlurMask:
    def __init__(self, lifetime=10):
        self.lifetime = lifetime
        self.masks = []
        self.sumask = None

    def add_frame(self, diff):
        # assert diff does not contain nan
        assert not np.isnan(diff).any()

        if self.sumask is None:
            self.sumask = diff
        else:
            self.sumask += diff

        self.masks.append(diff.copy())
        if len(self.masks) > self.lifetime:
            elim = self.masks.pop(0)
            self.sumask -= elim

        assert not np.isnan(self.sumask).any()
        # return self.sumask / self.lifetime
        return np.log(self.sumask + 1)


def peak_suppression(scores, center=(100, 100)):  # xy
    points = set()

    def explore(p):
        myscore = scores[p[1], p[0]]
        points.add(p)
        for nei in (
            (p[0] - 1, p[1]),
            (p[0] + 1, p[1]),
            (p[0], p[1] - 1),
            (p[0], p[1] + 1),
        ):
            if (
                nei[0] < 0
                or nei[0] >= scores.shape[1]
                or nei[1] < 0
                or nei[1] >= scores.shape[0]
            ):
                continue
            if nei not in points and scores[nei[1], nei[0]] < myscore:
                explore(nei)

    explore(center)
    smallest = min(scores[p[1], p[0]] for p in points)
    print(f"smallest {smallest}")
    # if smallest is not nan
    if not np.isnan(smallest):
        for p in points:
            scores[p[1], p[0]] = smallest


colors = ["navy", "turquoise"]  # , "darkorange"]


def make_ellipses(gmm, ax):
    for n, color in enumerate(colors):
        if gmm.covariance_type == "full":
            covariances = gmm.covariances_[n][:2, :2]
        elif gmm.covariance_type == "tied":
            covariances = gmm.covariances_[:2, :2]
        elif gmm.covariance_type == "diag":
            covariances = np.diag(gmm.covariances_[n][:2])
        elif gmm.covariance_type == "spherical":
            covariances = np.eye(gmm.means_.shape[1]) * gmm.covariances_[n]
        v, w = np.linalg.eigh(covariances)
        u = w[0] / np.linalg.norm(w[0])
        angle = np.arctan2(u[1], u[0])
        angle = 180 * angle / np.pi  # convert to degrees
        v = 2.0 * np.sqrt(2.0) * np.sqrt(v)
        ell = mpl.patches.Ellipse(
            gmm.means_[n, :2], v[0], v[1], angle=180 + angle, color=color
        )
        ell.set_clip_box(ax.bbox)
        ell.set_alpha(0.5)
        ax.add_artist(ell)
        ax.set_aspect("equal", "datalim")


def intersection(a, b):
    return (max(a[0], b[0]), min(a[1], b[1]))


# 動画を読み込む
if len(sys.argv) < 2:
    videofile = "examples/sample3.mov"
    videofile = "/Users/matto/Dropbox/ArtsAndIllustrations/Stitch tmp2/TrainScannerWorkArea/他人の動画/antishake test/Untitled.mp4"
else:
    videofile = sys.argv[1]

cap = cv2.VideoCapture(videofile)  # 動画ファイルのパスを指定

frames = []
ret, frame0 = cap.read()
if frame0.shape[1] > 1000:
    frame0 = cv2.resize(frame0, (0, 0), fx=0.5, fy=0.5)
frames.append(frame0)

blurmask = BlurMask(lifetime=20)
antishaker = AntiShaker2()
# 背景のずれ
antishakes = []
deltas = []
stabilized = 0
max_vals = []
longest_span = (0, 0)
mask = np.ones(frames[0].shape[:2], dtype=np.float32)
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # 大きい場合は半分に縮小
    if frame.shape[1] > 1000:
        frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)

    antimask = np.exp(-mask)

    frame, delta, abs_loc = antishaker.add_frame(frame, antimask)

    frames.append(frame)

    antishakes.append(delta)
    # まずてぶれ補正。これは最初のフレームと照合したほうがいいかも。
    # フレームを細分し、それぞれの場所でのずれを別々に計算すれば、回転も検出できる。
    # これはこれだけでまず書くべき。

    # グレースケールに変換
    base_std = (
        standardize(
            np.log(cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY).astype(np.float32) + 1)
        )
        * antimask
    )
    next_std = (
        standardize(
            np.log(cv2.cvtColor(frames[1], cv2.COLOR_BGR2GRAY).astype(np.float32) + 1)
        )
        * antimask
    )
    diff = (base_std - next_std) ** 2
    cv2.imshow("differ", diff)
    mask = blurmask.add_frame(diff)
    # 今のやりかただと、maskは空間で不動。それはいいのか。背景が動かないようにフレームをいつも動かして重ねていくわけだから。
    # 平均背景画像を表示してみたいな。

    # 2025-09 ここからあとは、本家Trainscanner同様に、変位速度が落ちつくまで様子を見てから、以後はそれを第一予測として利用する。また、leadingの処理も行う。
    # しばらくはこれから離れて仕事する。

    # 差をとると、列車が動いている部分は、ある場所が鋭く正に、すこしずれて鋭く負になる。
    # 差が小さい部分は背景の可能性が高いので、照合から除外する。
    # つまり、原画上で0にしてしまう。
    # diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

    # maskは、diffの値が大きいピクセル。
    print(f"mask {np.min(mask)}, {np.max(mask)}")
    mask += np.min(mask)

    base_masked = base_std.copy() * mask
    # マスクで重みづけした上で、内積で照合する(TM_CCORR)
    next_masked = next_std.copy() * mask

    # こんどは移動量をたっぷりとる。
    max_shift = 100

    base_masked_extended = np.zeros(
        [base_std.shape[0] + 2 * max_shift, base_std.shape[1] + 2 * max_shift],
        dtype=np.float32,
    )
    base_masked_extended[max_shift:-max_shift, max_shift:-max_shift] = base_masked
    scores = cv2.matchTemplate(base_masked_extended, next_masked, cv2.TM_CCORR_NORMED)

    # 画面中心はいつもピークがあるが、それは列車の移動と関係ないので除去する。
    peak_suppression(scores, (max_shift, max_shift))
    # これによってすべてのピクセルが0になってしまう場合がありうる。

    min_val, max_val1, min_loc, max_loc = cv2.minMaxLoc(scores)

    # ピーク検出（後でプロットに使用）
    print(f"Top 4 peaks: {find_2d_peaks(scores, num_peaks=4)}")

    # if min_val == max_val1:
    #     # assume the displace vector is same as the previous one
    #     deltas.append(deltas[-1])
    # else:
    deltas.append((max_loc[0] - max_shift, max_loc[1] - max_shift))

    max_vals.append(max_val1)

    # プロットのx軸が幅広すぎる場合に圧縮する
    if len(deltas) > max_shift * 2:
        x = np.linspace(-max_shift, max_shift, len(deltas))
    else:
        x = [i - max_shift for i in range(len(deltas))]

    mv = np.array(max_vals)

    # ある時刻以降の最小値が、その時刻以前の最大値よりも大きくなるような時刻を探す
    for t in range(len(mv) - 2, 1, -1):
        if np.min(mv[t:]) > np.max(mv[:t]):
            # そういう時刻がみつかったら、stitchの準備をはじめる。
            # ただし、あまりにも短い場合は捨てる? ユーザーにまかせればいい。
            # movieと、deltasとtをもらって、順次連結するstitcherを準備し、それにわたしていく。
            # そいつが、tよりも前の補完なども担う。
            print(f"stabilized at {t}")
            threshold = np.max(mv[:t]) * max_shift / np.max(mv)
            plt.plot(x, threshold * np.ones_like(x), "o-", label=f"{t}")
            if len(mv) - t > longest_span[1] - longest_span[0]:
                longest_span = (t, len(mv))
                stabilized = t
            break

    mv = mv * max_shift / np.max(mv)
    plt.plot(x, mv, "o-", label="max_val")
    d = np.array(deltas)
    plt.plot(x[:stabilized], d[:stabilized, 0], "o-", label="x")
    plt.plot(x[:stabilized], d[:stabilized, 1], "o-", label="y")
    plt.plot(x[stabilized:], d[stabilized:, 0], "o-", label="x")
    plt.plot(x[stabilized:], d[stabilized:, 1], "o-", label="y")
    plt.legend()

    cv2.imshow("frame", frames[0])
    cv2.imshow("mask", mask)
    cv2.imshow("reversed mask", antimask)
    cv2.imshow("base_masked", base_masked)
    cv2.imshow("next_masked", next_masked)
    # cv2.imshow("raw_diff", frames[0] - frames[1])
    # cv2.imshow("as_diff", frames[0] - frame)

    plt.imshow(scores, extent=[-max_shift, max_shift, -max_shift, max_shift])

    # ピーク位置に赤い丸を描画
    peaks = find_2d_peaks(scores, num_peaks=10)
    for i, (y, x) in enumerate(peaks):
        # スコア座標系をプロット座標系に変換
        print(x, y)
        if (x - max_shift) ** 2 + (y - max_shift) ** 2 < 12:
            continue

        plot_x = (x / scores.shape[1]) * (2 * max_shift) - max_shift
        plot_y = (y / scores.shape[0]) * (2 * max_shift) - max_shift

        plt.plot(
            plot_x,
            plot_y,
            "ro",
            markersize=8,
            markerfacecolor=None,
            # markeredgecolor="red",
            markeredgewidth=1,
        )
        # ピークの順位を表示
        plt.text(
            plot_x + 2,
            plot_y + 2,
            str(i + 1),
            color="white",
            fontsize=10,
            fontweight="bold",
        )

    plt.colorbar(label="Correlation Score")
    plt.title(f"Correlation Scores with Top 4 Peaks (Frame {len(deltas)})")
    plt.xlabel("X Shift")
    plt.ylabel("Y Shift")
    plt.savefig("scores.png")
    plt.close()
    cv2.imshow("scores", cv2.imread("scores.png"))
    cv2.waitKey(0)

    if len(frames) > 2:
        frames.pop(0)

# けっこううまいこといくが、迷子にならないような工夫が必要。
