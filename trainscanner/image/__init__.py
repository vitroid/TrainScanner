import cv2
import numpy as np
from pyperbox import Rect, Range
import math
from dataclasses import dataclass
from trainscanner import MatchResult
import matplotlib.pyplot as plt


def _find_peaks(arr: np.ndarray):
    """
    周囲8点のいずれよりも値が大きい点を極値とし、その位置と値を返す。
    """
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
    return [(x + 1, y + 1) for y, x in np.argwhere(is_max)]


def find_paraboloid_extremum(values):
    """
    3x3の格子点(x,y in [-1, 0, 1])の値から、
    最小二乗法で放物面をフィッティングし、その極値を計算する。

    引数:
        values (list of list or np.ndarray): 3x3の配列。
                                             values[y_idx][x_idx] が
                                             y = y_idx - 1, x = x_idx - 1
                                             に対応するものとする。

    戻り値:
        dict: 極値に関する情報。
              {"status": "success", "x": x0, "y": y0, "z": z0, "type": ext_type}
              またはエラー時は
              {"status": "error", "message": "..."}
    """

    # 1. データ準備 (Data Preparation)
    # ユーザーの指定通り、values[y_idx][x_idx]
    # z_vecは z(-1,-1), z(0,-1), z(1,-1), z(-1,0), ... の順
    try:
        z_vec = np.array(values).flatten()
        if z_vec.shape[0] != 9:
            raise ValueError("入力は3x3の配列である必要があります。")
    except Exception as e:
        return {"status": "error", "message": f"入力値エラー: {e}"}

    # x, y 座標の生成 (z_vecの順序に対応)
    # x = [-1, 0, 1, -1, 0, 1, -1, 0, 1]
    # y = [-1, -1, -1, 0, 0, 0, 1, 1, 1]
    x = np.array([-1, 0, 1] * 3)
    y = np.repeat([-1, 0, 1], 3)

    # 2. 係数の算出 (Coefficient Calculation)
    # z = a*x^2 + b*y^2 + c*xy + d*x + e*y + f
    # M * p = z_vec
    M = np.stack(
        [x**2, y**2, x * y, x, y, np.ones(9)], axis=-1  # a  # b  # c  # d  # e  # f
    )

    try:
        # 最小二乗法で係数ベクトル p = [a, b, c, d, e, f] を解く
        p, _, _, _ = np.linalg.lstsq(M, z_vec, rcond=None)
        a, b, c, d, e, f = p
    except np.linalg.LinAlgError as e:
        return {"status": "error", "message": f"最小二乗法エラー: {e}"}

    # 3. 極値の座標の算出 (Extremum Coordinate Calculation)
    # ヘッセ行列 (Hessian) と 勾配の定数項
    # [ 2a  c ] [ x ] = [ -d ]
    # [  c 2b ] [ y ] = [ -e ]
    Hessian = np.array([[2 * a, c], [c, 2 * b]])
    B = np.array([-d, -e])

    # det = 4ab - c^2
    det = np.linalg.det(Hessian)

    if np.isclose(det, 0):
        # 行列が特異(det=0)の場合、唯一の極値が存在しない (例: 円筒面、鞍状の線)
        return {
            "status": "no_unique_extremum",
            "message": "解が一意に定まりません (det=0)。極値は存在しないか、線状に存在します。",
            "coefficients": {"a": a, "b": b, "c": c, "d": d, "e": e, "f": f},
        }

    try:
        # (x0, y0) を解く
        coords = np.linalg.solve(Hessian, B)
        x0, y0 = coords
    except np.linalg.LinAlgError:
        # det=0 で捕捉されるはずだが、念のため
        return {
            "status": "error",
            "message": "座標の連立方程式を解けませんでした。",
            "coefficients": {"a": a, "b": b, "c": c, "d": d, "e": e, "f": f},
        }

    # 4. 極値の値の算出 (Extremum Value Calculation)
    # z0 = a*x0^2 + b*y0^2 + c*x0*y0 + d*x0 + e*y0 + f
    z0 = p @ [x0**2, y0**2, x0 * y0, x0, y0, 1]

    # 5. 極値のタイプの判定 (Extremum Type)
    if det > 0:
        # a (またはb) の符号で極大・極小を判定
        ext_type = "極小値 (Local Minimum)" if a > 0 else "極大値 (Local Maximum)"
    else:
        ext_type = "鞍点 (Saddle Point)"

    return {
        "status": "success",
        "x": x0,
        "y": y0,
        "z": z0,
        "type": ext_type,
        "coefficients": {"a": a, "b": b, "c": c, "d": d, "e": e, "f": f},
    }


@dataclass
class MatchRect:
    """
    目盛りつきのmatch score行列
    """

    value: np.ndarray
    rect: Rect

    _figure = None
    _axes = None
    _colorbar = None

    # used in trainscanner2
    def peak(self, subpixel=False):
        _, maxval, _, (x, y) = cv2.minMaxLoc(self.value)
        if subpixel:
            if 0 < x < self.rect.width - 1 and 0 < y < self.rect.height - 1:
                # (x,y)の周囲9点を放物面近似して頂点の位置と値を求める。
                values = self.value[y - 1 : y + 2, x - 1 : x + 2]
                result = find_paraboloid_extremum(values)
                if result["status"] == "success":
                    return self.coord(x + result["x"], y + result["y"]), result["z"]
        return self.coord(x, y), maxval

    def peaks(self, height: float = 0.5, subpixel=False):
        """
        周囲8点のいずれよりも値が大きい点を極値とし、その位置と値を返す。
        """
        for x, y in _find_peaks(self.value):
            if self.value[y, x] > height:
                if subpixel:
                    if 0 < x < self.rect.width - 1 and 0 < y < self.rect.height - 1:
                        values = self.value[y - 1 : y + 2, x - 1 : x + 2]
                        result = find_paraboloid_extremum(values)
                        if result["status"] == "success":
                            yield self.coord(x + result["x"], y + result["y"]), result[
                                "z"
                            ]
                        else:
                            yield self.coord(x, y), self.value[y, x]
                    else:
                        yield self.coord(x, y), self.value[y, x]
                else:
                    yield self.coord(x, y), self.value[y, x]

    def coord(self, x: int, y: int):
        # 配列要素(x,y)を、座標に変換する。
        return x + self.rect.left, y + self.rect.top

    def plot(self, label=""):
        # とりあえず、matchscore.valueを2次元の等高線で表示したい。
        # x軸とy軸の範囲はmatchscore.dxとmatchscore.dyから決める。
        x = np.linspace(self.rect.left, self.rect.right - 1, self.rect.width)
        y = np.linspace(self.rect.top, self.rect.bottom - 1, self.rect.height)
        # 値そのものをグラデーション表示
        # 位置をあわせる。
        X, Y = np.meshgrid(x, y)

        # 既存のFigureがあれば再利用。なければ生成。
        if MatchRect._figure is None or MatchRect._axes is None:
            if not plt.isinteractive():
                plt.ion()
            MatchRect._figure, MatchRect._axes = plt.subplots(figsize=(10, 8))
            plt.show(block=False)
        else:
            if MatchRect._colorbar is not None:
                MatchRect._colorbar.remove()
                MatchRect._colorbar = None
            MatchRect._axes.clear()

        # imshowで背景画像を表示（extentで座標範囲を指定）
        im = MatchRect._axes.imshow(
            self.value,
            cmap="jet",
            extent=[
                self.rect.left,
                self.rect.right - 1,
                self.rect.bottom - 1,
                self.rect.top,
            ],  # y軸は反転
            aspect="auto",
            alpha=0.8,
        )

        # contourで等高線を重ねて描画
        contours = MatchRect._axes.contour(
            X, Y, self.value, colors="white", linewidths=1.5
        )
        MatchRect._axes.clabel(contours, inline=True, fontsize=8)

        # カラーバーを追加（imshowの色情報を使用）
        MatchRect._colorbar = MatchRect._figure.colorbar(im, label="Score")

        # 軸ラベルとタイトル
        MatchRect._axes.set_xlabel("dx")
        MatchRect._axes.set_ylabel("dy")
        MatchRect._axes.set_title(f"Motion Analysis {label}")

        MatchRect._figure.canvas.draw_idle()
        MatchRect._figure.canvas.flush_events()
        # print(np.min(matchscore.value), np.max(matchscore.value))


@dataclass
class PreMatchRect(MatchRect):
    frame_index: int


# fit image in a square
def fit_to_square(image, size):
    h, w = image.shape[0:2]
    modified = False
    if h > w:
        if h > size:
            w = w * size // h
            h = size
            modified = True
    else:
        if w > size:
            h = h * size // w
            w = size
            modified = True
    if not modified:
        return image
    return cv2.resize(image, (w, h), interpolation=cv2.INTER_CUBIC)


def standardize(x):
    return ((x - np.mean(x)) / np.std(x)).astype(np.float32)


def diffImage(frame1, frame2, dx, dy, mode="stack"):  # , focus=None, slitpos=None):
    """
    2枚のcv2画像の差を返す．
    """
    affine = np.matrix(((1.0, 0.0, dx), (0.0, 1.0, dy)))
    h, w = frame1.shape[0:2]
    if mode == "diff":
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
        flags = np.arange(h) * 16 % h > h // 2
        frame1 = cv2.warpAffine(frame1, affine, (w, h))
        frame1[flags] = frame2[flags]
        return frame1
    elif mode == "checker":
        sq = 32
        flags = np.zeros(frame1.shape[:2], dtype=bool)
        X, Y = np.meshgrid(np.arange(w), np.arange(h))
        flags[X % (sq * 2) < sq] = ~flags[X % (sq * 2) < sq]
        flags[Y % (sq * 2) < sq] = ~flags[Y % (sq * 2) < sq]
        frame1 = cv2.warpAffine(frame1, affine, (w, h))
        frame1[flags] = frame2[flags]
        return frame1


def draw_focus_area(f, focus: Rect):
    """
    cv2形式の画像の中に四角を描く
    """
    h, w = f.shape[0:2]
    pos = Rect(
        x_range=Range(
            min_val=w * focus.x_range.min_val // 1000,
            max_val=w * focus.x_range.max_val // 1000,
        ),
        y_range=Range(
            min_val=h * focus.y_range.min_val // 1000,
            max_val=h * focus.y_range.max_val // 1000,
        ),
    )
    colors = [(0, 255, 0), (255, 255, 0)]
    cv2.rectangle(f, (pos.left, pos.top), (pos.right, pos.bottom), colors[0], 1)


class diffview:
    def __init__(self, focus: Rect):
        self.focus = focus
        self.lastimage = None
        self.preview_size = 500

    def view(self, matchresult: MatchResult):
        preview = fit_to_square(matchresult.image, self.preview_size)
        # draw focus area here
        draw_focus_area(
            preview,
            self.focus,
        )
        preview_ratio = preview.shape[0] / matchresult.image.shape[0]
        if self.lastimage is None:
            self.lastimage = preview
            return None
        deltax = int(matchresult.velocity[0] * matchresult.dt * preview_ratio)
        deltay = int(matchresult.velocity[1] * matchresult.dt * preview_ratio)
        diff = diffImage(preview, self.lastimage, deltax, deltay)
        self.lastimage = preview
        return diff


# from parser to args
def deparse(parser, params):
    args = dict()
    pvars = vars(params)
    for key in pvars:
        value = pvars[key]
        for action in parser._actions:
            kwargs = action._get_kwargs()  # list of tuple
            kwdict = dict(kwargs)
            # print(kwdict)
            if kwdict["dest"] == key:
                options = kwdict["option_strings"]
                if len(options) == 0:
                    args["__UNNAMED__"] = value
                else:
                    args[options[-1]] = value
    return args


class Transformation:
    def __init__(self, angle=0, pers=None, crop=None):
        self.angle = -angle * math.pi / 180.0
        self.pers = pers
        self.crop = crop
        self.R = None
        self.M = None

    def rotation_affine(self, w, h):
        a = math.cos(self.angle)
        b = math.sin(self.angle)
        rh = abs(h * a) + abs(w * b)
        rw = abs(h * b) + abs(w * a)
        self.rh, self.rw = int(rh), int(rw)
        halfw, halfh = w / 2, h / 2
        self.R = np.matrix(
            (
                (a, b, -a * halfw - b * halfh + rw / 2),
                (-b, a, b * halfw - a * halfh + rh / 2),
            )
        )

    def rotated_image(self, image):
        return cv2.warpAffine(image, self.R, (self.rw, self.rh))

    def warp_affine(self):
        """
        Warp.  Save the perspective matrix to the file for future use.
        """
        if self.pers is None:
            return
        w = self.rw
        h = self.rh
        L = (self.pers[2] - self.pers[0]) * h // 1000
        S = (self.pers[3] - self.pers[1]) * h // 1000
        if L < S:
            L, S = S, L
        LS = (L * S) ** 0.5
        fdist = L / S
        ndist = LS // S
        sratio = ((fdist - 1.0) ** 2 + 1) ** 0.5
        neww = int(w * sratio / ndist)
        woffset = (neww - w) // 2
        p1 = np.float32(
            [
                (0, self.pers[0] * h / 1000),
                (w, self.pers[1] * h / 1000),
                (0, self.pers[2] * h / 1000),
                (w, self.pers[3] * h / 1000),
            ]
        )
        # Unskew
        p2 = np.float32(
            [
                (0, (self.pers[0] * self.pers[1]) ** 0.5 * h / 1000),
                (neww, (self.pers[0] * self.pers[1]) ** 0.5 * h / 1000),
                (0, (self.pers[2] * self.pers[3]) ** 0.5 * h / 1000),
                (neww, (self.pers[2] * self.pers[3]) ** 0.5 * h / 1000),
            ]
        )
        self.M = cv2.getPerspectiveTransform(p1, p2)
        self.ww = neww

    def warped_image(self, image):
        if self.pers is None:
            return image
        h = image.shape[0]
        return cv2.warpPerspective(image, self.M, (self.ww, h))

    def cropped_image(self, image):
        if self.crop is None:
            return image
        h, w = image.shape[:2]
        return image[self.crop[0] * h // 1000 : self.crop[1] * h // 1000, :, :]

    def process_first_image(self, image):
        h, w = image.shape[:2]
        self.rotation_affine(w, h)
        self.warp_affine()
        return self.process_next_image(image)

    def process_next_image(self, image):
        rotated = self.rotated_image(image)
        warped = self.warped_image(rotated)
        cropped = self.cropped_image(warped)
        return rotated, warped, cropped

    def process_image(self, image):
        if self.R is None:
            return self.process_first_image(image)
        else:
            return self.process_next_image(image)

    def process_images(self, images):
        h, w = images[0].shape[:2]
        self.rotation_affine(w, h)
        self.warp_affine()
        rs = []
        ws = []
        cs = []
        for image in images:
            rotated, warped, cropped = self.process_next_image(image)
            rs.append(rotated)
            ws.append(warped)
            cs.append(cropped)
        return rs, ws, cs


# def match(
#     target_area: np.ndarray, target_rect: Rect, focus: np.ndarray, focus_rect: Rect
# ) -> MatchScore:
#     # 大きな画像の一部(座標範囲はtarget_rect)であるtarget_areaの中に、同じく大きな画像(座標範囲はfocus_rect)の一部であるfocusがある。
#     # その場所をさがし、変位ベクトルとスコアを返す。
#     assert target_area.shape[0] == target_rect.height
#     assert target_area.shape[1] == target_rect.width
#     assert focus.shape[0] == focus_rect.height
#     assert focus.shape[1] == focus_rect.width
#     scores = cv2.matchTemplate(target_area, focus, cv2.TM_CCOEFF_NORMED)
#     # scoresに座標を指示する。
#     dx = range(
#         target_rect.left - focus_rect.left,
#         target_rect.right - focus_rect.right + 1,
#     )
#     dy = range(
#         target_rect.top - focus_rect.top,
#         target_rect.bottom - focus_rect.bottom + 1,
#     )
#     # 変位ベクトルとスコアをセットで返す。
#     return MatchScore(dx, dy, scores)


class ImageRect:
    """絶対座標付きの画像。"""

    def __init__(
        self,
        lefttop: tuple[int, int] = (0, 0),
        image: np.ndarray = None,
        bgcolor=(100, 100, 100),
    ):
        self.left, self.top = lefttop
        self.bgcolor = np.array(bgcolor, dtype=np.uint8)
        self.image = image

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  # TiledImageは特別なクリーンアップ処理は必要ありません

    @property
    def rect(self):
        if self.image is not None:
            return Rect.from_bounds(
                self.left,
                self.right,
                self.top,
                self.bottom,
            )

    @property
    def width(self):
        return self.image.shape[1]

    @property
    def height(self):
        return self.image.shape[0]

    @property
    def right(self):
        return self.left + self.image.shape[1]

    @property
    def bottom(self):
        return self.top + self.image.shape[0]

    @property
    def shape(self):
        return self.image.shape

    def get_region(self, rect: Rect | None = None):
        logger = logging.getLogger()
        if rect is None:
            rect = self.rect
        if rect is None:
            return
        logger.debug(f"get_region region:{rect}")

        # 指定されたrectが画像からはみでている部分はbgcolorで塗る。

        dst_width = rect.width
        dst_height = rect.height

        imagerect = ImageRect(
            lefttop=(rect.left, rect.top),
            image=np.zeros((dst_height, dst_width, 3), dtype=np.uint8) + self.bgcolor,
        )
        crop = self.rect & rect
        imagerect.put_image(
            lefttop=(crop.left, crop.top),
            image=self.image[
                crop.top - self.rect.top : crop.bottom - self.rect.top,
                crop.left - self.rect.left : crop.right - self.rect.left,
            ],
        )
        return imagerect

    def put_imagerect(self, imagerect):
        self.put_image(lefttop=(imagerect.left, imagerect.top), image=imagerect.image)

    def put_image(
        self,
        lefttop: tuple[int, int],
        image: np.ndarray,
        linear_alpha=None,
        full_alpha=None,
    ):
        """
        split the existent tiles
        and put a big single tile.
        the image must be larger than a single tile.
        otherwise, a different algorithm is required.
        """
        h, w = image.shape[:2]
        rect = Rect.from_bounds(lefttop[0], lefttop[0] + w, lefttop[1], lefttop[1] + h)
        # expand the canvas
        if self.image is None:
            self.left, self.top = lefttop
            self.image = image.copy()
        else:
            newrect = self.rect | rect
            new_image = (
                np.zeros([newrect.height, newrect.width, 3], dtype=np.uint8)
                + self.bgcolor
            )
            new_image[
                self.top - newrect.top : self.bottom - newrect.top,
                self.left - newrect.left : self.right - newrect.left,
            ] = self.image
            self.image = new_image
            self.left = newrect.left
            self.top = newrect.top

            if linear_alpha is None and full_alpha is None:
                self.image[
                    rect.top - self.rect.top : rect.bottom - self.rect.top,
                    rect.left - self.rect.left : rect.right - self.rect.left,
                ] = image
            else:
                if full_alpha is not None:
                    alpha = full_alpha[:, :, np.newaxis]
                else:
                    alpha = linear_alpha[np.newaxis, :, np.newaxis]
                self.image[
                    rect.top - self.top : rect.bottom - self.top,
                    rect.left - self.left : rect.right - self.left,
                    :,
                ] = (
                    alpha * image
                    + (1 - alpha)
                    * self.image[
                        rect.top - self.top : rect.bottom - self.top,
                        rect.left - self.left : rect.right - self.left,
                        :,
                    ]
                )

    def split_vertically(self, left_width: int):
        left = ImageRect(
            lefttop=(self.left, self.top), image=self.image[:, :left_width]
        )
        right = ImageRect(
            lefttop=(self.left + left_width, self.top), image=self.image[:, left_width:]
        )
        return left, right

    def get_image(self):
        # widthを指定すると縮小する。
        return self.get_region()


def match_rect(target: ImageRect, focus: ImageRect) -> MatchRect:
    # 大きな画像の一部(座標範囲はtarget_rect)であるtarget_areaの中に、同じく大きな画像(座標範囲はfocus_rect)の一部であるfocusがある。
    # その場所をさがし、変位ベクトルとスコアを返す。
    scores = cv2.matchTemplate(target.image, focus.image, cv2.TM_CCOEFF_NORMED)

    rect = Rect.from_bounds(
        target.left - focus.left,
        target.right - focus.right + 1,
        target.top - focus.top,
        target.bottom - focus.bottom + 1,
    )
    assert rect.width == scores.shape[1]
    assert rect.height == scores.shape[0]
    # 変位ベクトルとスコアをセットで返す。
    return MatchRect(value=scores, rect=rect)


def main():
    # --- 実行例 (Example Usage) ---

    # 例1: 単純なボウル (z = x^2 + y^2)、極小値 (0, 0, 0)
    # values[y][x]
    bowl_values = [[2, 1, 2], [1, 0, 1], [2, 1, 2]]  # y = -1  # y = 0  # y = 1

    print("--- ボウルの例 (z = x^2 + y^2) ---")
    result_bowl = find_paraboloid_extremum(bowl_values)
    print(result_bowl)
    # 出力 (x, y, z が 0 に近い値になる):
    # {'status': 'success', 'x': 0.0, 'y': 0.0, 'z': 0.0,
    #  'type': '極小値 (Local Minimum)',
    #  'coefficients': {'a': 1.0, 'b': 1.0, 'c': 0.0, 'd': 0.0, 'e': 0.0, 'f': 0.0}}

    # 例2: 鞍点 (z = x^2 - y^2)、鞍点 (0, 0, 0)
    saddle_values = [[0, -1, 0], [1, 0, 1], [0, -1, 0]]  # y = -1  # y = 0  # y = 1

    print("\n--- 鞍点の例 (z = x^2 - y^2) ---")
    result_saddle = find_paraboloid_extremum(saddle_values)
    print(result_saddle)
    # 出力:
    # {'status': 'success', 'x': 0.0, 'y': 0.0, 'z': 0.0,
    #  'type': '鞍点 (Saddle Point)',
    #  'coefficients': {'a': 1.0, 'b': -1.0, 'c': 0.0, 'd': 0.0, 'e': 0.0, 'f': 0.0}}

    # 例3: ずれた極小値 z = (x-0.5)^2 + (y+0.2)^2
    #      = x^2 - x + 0.25 + y^2 + 0.4y + 0.04
    #      = x^2 + y^2 - x + 0.4y + 0.29
    def f(x, y):
        return (x - 0.5) ** 2 + (y + 0.2) ** 2

    shifted_values = [
        [f(-1, -1), f(0, -1), f(1, -1)],  # y = -1
        [f(-1, 0), f(0, 0), f(1, 0)],  # y = 0
        [f(-1, 1), f(0, 1), f(1, 1)],  # y = 1
    ]

    print("\n--- ずれた極小値の例 ---")
    result_shifted = find_paraboloid_extremum(shifted_values)
    print(result_shifted)
    # 出力 (x=0.5, y=-0.2, z=0 に近い値になる):
    # {'status': 'success', 'x': 0.5, 'y': -0.2, 'z': 0.0,
    #  'type': '極小値 (Local Minimum)',
    #  'coefficients': {'a': 1.0, 'b': 1.0, 'c': 0.0, 'd': -1.0, 'e': 0.4, 'f': 0.29}}


if __name__ == "__main__":
    main()
