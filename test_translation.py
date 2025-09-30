from attr import dataclass
import cv2
import numpy as np
import sys
from matplotlib import pyplot as plt
from scipy.signal import find_peaks

# from sklearn.mixture import GaussianMixture
import matplotlib as mpl
from test_antishake2 import AntiShaker2
from trainscanner.image import match, linear_alpha, standardize
from tiffeditor import Rect
from trainscanner.video import video_loader_factory
from tiledimage.cachedimage import CachedImage

# Stitchは問題なく動いているので、速度予測の精度を上げることにもうちょっと注力する。
# 今の考え方だけだと、もともとの画像が周期的だった場合に、それを速度と勘違いしてしまう。
# 背景画像から背景画像を引いてしまうのはどうか。
#
# あと、透視図に対応していない。これのためには、以前試したような、ブロック分割が良いとおもうが、まだ不完全。
#
# Rectを使うためだけにtiffeditorを読むのは不便。


@dataclass
class FramePosition:
    index: int
    train_velocity: tuple[float, float]
    absolute_location: tuple[float, float]  # of the frame


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
        return self.sumask / self.lifetime
        # return np.log(self.sumask + 1)


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


def normalize(x):
    return (x - np.min(x)) / (np.max(x) - np.min(x))


def alpha_mask(size, delta, width=20):
    # 実際にはalphaを傾ける必要はなかった。
    # 画像のほうを回すべきだった。
    w, h = size
    dx, dy = delta
    L = (dx**2 + dy**2) ** 0.5
    dx /= L
    dy /= L
    # 原点を通る平面。z = A x + B y
    # (0、0、0)と(dx, dy, 1/w)を通るようにしたい。ただし1=dx^2+dy^2
    # dx/A + dy/B = L/w
    X, Y = np.meshgrid(np.arange(w), np.arange(h))
    alpha = ((X - w / 2) * dx + (Y - h / 2) * dy) / width
    print(alpha[int(dy * width) + h // 2, int(dx * width) + w // 2])
    alpha[alpha > 1] = 1
    alpha[alpha < 0] = 0
    return alpha


class FIFO:
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

    @property
    def filled(self):
        return len(self.queue) == self.maxlen


def rotated_placement(frame, sine, cosine, train_position):
    h, w = frame.shape[:2]
    rh = int(abs(h * cosine) + abs(w * sine))
    rw = int(abs(h * sine) + abs(w * cosine))
    halfw, halfh = w / 2, h / 2
    R = np.matrix(
        (
            (cosine, sine, -cosine * halfw - sine * halfh + rw / 2),
            (-sine, cosine, sine * halfw - cosine * halfh + rh / 2),
        )
    )
    alpha = linear_alpha(img_width=rw, mixing_width=20, slit_pos=0, head_right=True)
    rotated = cv2.warpAffine(frame, R, (rw, rh))
    # 画像中心をそろえる
    canvas.put_image(
        (int(train_position) - rw // 2, -rh // 2),
        rotated,
        linear_alpha=alpha,
    )


# 動画を読み込む
if len(sys.argv) < 2:
    videofile = "examples/sample3.mov"
    videofile = "/Users/matto/Dropbox/ArtsAndIllustrations/Stitch tmp2/TrainScannerWorkArea/他人の動画/antishake test/Untitled.mp4"
else:
    videofile = sys.argv[1]


# cv2.imshow("alpha", alpha_mask((1000, 2000), (50, 15), width=50))
# cv2.waitKey(0)
# sys.exit(0)

frames = FIFO(2)
vl = video_loader_factory(videofile)
if "0835" in videofile:
    vl.seek(47 * 30)
frame0 = vl.next()
if frame0.shape[1] > 1000:
    ratio = 1000 / frame0.shape[1]
    frame0 = cv2.resize(frame0, (0, 0), fx=ratio, fy=ratio)
frames.append(frame0)

blurmask = BlurMask(lifetime=20)
antishaker = AntiShaker2(velocity=1)
# 背景のずれ
framepositions = {}
stabilized = False
max_vals = []
longest_span = (0, 0)
# number of frames to estimate the velocity
estimate = 5
velx_history = FIFO(estimate)
vely_history = FIFO(estimate)
train_deltas = []
train_position = 0
mask = np.ones(frames.queue[0].shape[:2], dtype=np.float32)
averaged_background = np.zeros_like(frames.queue[0], dtype=np.float32)
matchscores = []
with CachedImage("new", dir="test_translation.pngs") as canvas:
    while True:
        frame = vl.next()
        if frame is None:
            break

        # 大きい場合は半分に縮小
        if frame.shape[1] > 1000:
            ratio = 1000 / frame.shape[1]
            frame = cv2.resize(frame, (0, 0), fx=ratio, fy=ratio)

        # antimask = np.exp(-mask)
        if np.max(mask) == np.min(mask):
            antimask = np.ones_like(mask)
        else:
            antimask = 1 - normalize(mask)

        frame, delta, abs_loc = antishaker.add_frame(frame, antimask)

        # framesにはてぶれを修正し,最初のフレームの位置に背景がそろえられた画像が入るので、あとの処理は列車の動きだけ考えればいい。
        frames.append(frame)

        frame_index = vl.head - 1
        print(f"{frame_index=} {delta=} {abs_loc=}")
        framepositions[frame_index] = FramePosition(
            index=frame_index, train_velocity=None, absolute_location=abs_loc
        )

        averaged_background += frame
        cv2.imshow(
            "averaged_background", averaged_background / len(framepositions) / 255
        )
        # グレースケールに変換
        base_std = (
            standardize(
                np.log(
                    cv2.cvtColor(frames.queue[0], cv2.COLOR_BGR2GRAY).astype(np.float32)
                    + 1
                )
            )
            * antimask
        )
        next_std = (
            standardize(
                np.log(
                    cv2.cvtColor(frames.queue[1], cv2.COLOR_BGR2GRAY).astype(np.float32)
                    + 1
                )
            )
            * antimask
        )
        diff = (base_std - next_std) ** 2
        cv2.imshow("differ", diff)
        mask = blurmask.add_frame(diff)

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
        base_extended_rect = Rect.from_bounds(
            -max_shift,
            base_std.shape[1] + max_shift,
            -max_shift,
            base_std.shape[0] + max_shift,
        )
        next_rect = Rect.from_bounds(
            0,
            next_std.shape[1],
            0,
            next_std.shape[0],
        )
        matchscore = match(
            base_masked_extended, base_extended_rect, next_masked, next_rect
        )

        # 画面中心はいつもピークがあるが、それは列車の移動と関係ないので除去する。
        peak_suppression(matchscore.value, (max_shift, max_shift))
        # これによってすべてのピクセルが0になってしまう場合がありうる。

        # leading framesでの速度予測のために記録しておく。
        matchscores.append(matchscore)

        _, max_val1, _, max_loc = cv2.minMaxLoc(matchscore.value)
        delta = (matchscore.dx[max_loc[0]], matchscore.dy[max_loc[1]])
        train_deltas.append(delta)

        velx_history.append(delta[0])
        vely_history.append(delta[1])
        if stabilized:

            framepositions[frame_index].train_velocity = delta
            dx, dy = delta
            dd = -((dx**2 + dy**2) ** 0.5)
            train_position += dd
            cosine = dx / dd
            sine = dy / dd
            rotated_placement(frame, sine, cosine, train_position)
        elif (
            velx_history.filled
            and velx_history.fluctuation() < 3
            and vely_history.fluctuation() < 3
        ):
            # pass
            stabilized = True
            for fi in range(estimate):
                # 最後のestimate個の速度は安定しているので、さかのぼって採用する。
                delta = (velx_history.queue[fi], vely_history.queue[fi])
                framepositions[frame_index].train_velocity = delta
                dx, dy = delta
                dd = -((dx**2 + dy**2) ** 0.5)
                train_position += dd
                cosine = dx / dd
                sine = dy / dd
                rotated_placement(frame, sine, cosine, train_position)
            #         vely_history.queue[fi],
            #     )
            #     train_position[0] += velx_history.queue[fi]
            #     train_position[1] += vely_history.queue[fi]
            #     absx, absy = train_position
            #     h, w = frame.shape[:2]
            #     alpha = alpha_mask(
            #         (w, h), (velx_history.queue[fi], vely_history.queue[fi]), width=200
            #     )
            #     canvas.put_image((absx, absy), frame, full_alpha=alpha)
        for fp in list(framepositions.keys())[-6:]:
            print(framepositions[fp])

        max_vals.append(max_val1)

        # プロットのx軸が幅広すぎる場合に圧縮する
        if len(train_deltas) > max_shift * 2:
            x = np.linspace(-max_shift, max_shift, len(train_deltas))
        else:
            x = [i - max_shift for i in range(len(train_deltas))]

        if stabilized:
            cv2.imshow("canvas", canvas.get_image())
        cv2.imshow("mask", mask)
        cv2.imshow("reversed mask", antimask)
        cv2.imshow("base_masked", base_masked * 6)
        cv2.imshow("next_masked", next_masked * 6)
        # cv2.imshow("raw_diff", frames[0] - frames[1])
        # cv2.imshow("as_diff", frames[0] - frame)

        plt.imshow(
            matchscore.value, extent=[-max_shift, max_shift, -max_shift, max_shift]
        )

        # ピーク位置に赤い丸を描画
        peaks = find_2d_peaks(matchscore.value, num_peaks=10)
        for i, (y, x) in enumerate(peaks):
            # スコア座標系をプロット座標系に変換
            x = matchscore.dx[x]
            y = matchscore.dy[y]

            plt.plot(
                x,
                y,
                "ro",
                markersize=8,
                markerfacecolor=None,
                # markeredgecolor="red",
                markeredgewidth=1,
            )
            # ピークの順位を表示
            plt.text(
                x + 2,
                y + 2,
                str(i + 1),
                color="white",
                fontsize=10,
                fontweight="bold",
            )

        plt.colorbar(label="Correlation Score")
        plt.title(f"Correlation Scores with Top 4 Peaks (Frame {len(train_deltas)})")
        plt.xlabel("X Shift")
        plt.ylabel("Y Shift")
        plt.savefig("scores.png")
        plt.close()
        cv2.imshow("scores", cv2.imread("scores.png"))
        cv2.waitKey(0)


# けっこううまいこといくが、迷子にならないような工夫が必要。
