import cv2
import numpy as np
import scipy.optimize
from logging import getLogger
import functools


def debug_log(func):
    """関数の引数と戻り値をデバッグログに出力するデコレータ"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = getLogger()
        # 引数を文字列に変換
        args_str = ", ".join(map(repr, args))
        kwargs_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        all_args_str = (
            f"{args_str}, {kwargs_str}"
            if args_str and kwargs_str
            else args_str or kwargs_str
        )

        logger.debug(f"{func.__name__} called with arguments: ({all_args_str})")
        result = func(*args, **kwargs)
        logger.debug(f"{func.__name__} returned: {result!r}")
        return result

    return wrapper


def standardize(x):
    return ((x - np.mean(x)) / np.std(x)).astype(np.float32)


# @debug_log
def subpixel_match(
    target_area: np.ndarray, focus: np.ndarray, fit_margins=[2, 2], subpixel=True
):
    logger = getLogger()
    scores = cv2.matchTemplate(target_area, focus, cv2.TM_CCOEFF_NORMED)
    # scores = standardize(scores)
    logger.debug(f"{scores=}")
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(scores)
    # print(10, fit_width, max_loc, scores.shape)
    # print(
    #         f"target_area: {target_area.shape} focus: {focus.shape} scores: {scores.shape} min_loc: {min_loc}"
    # )

    # もし、min_locが端すぎる場合には、subpixelは返さない。
    if (
        not (
            fit_margins[0] <= max_loc[0] < scores.shape[1] - fit_margins[0]
            and fit_margins[1] <= max_loc[1] < scores.shape[0] - fit_margins[1]
        )
        or not subpixel
    ):
        logger.debug(f"11 {fit_margins=} {max_loc=} {scores.shape=}")
        return max_loc, (0.0, 0.0), max_val

    def parabola(xy, x0, y0, sigma_x, sigma_y, B):
        x, y = xy
        return (
            -((x - x0) ** 2) / (2 * sigma_x**2) - (y - y0) ** 2 / (2 * sigma_y**2)
        ) + B

    def parabola1D(xy, x0, sigma_x, B):
        x, y = xy
        return (-((x - x0) ** 2) / (2 * sigma_x**2)) + B

    scores_w, scores_h = fit_margins[0] * 2 + 1, fit_margins[1] * 2 + 1
    x, y = np.meshgrid(np.arange(scores_w), np.arange(scores_h))
    x = x.flatten()
    y = y.flatten()
    local_scores = scores[
        max_loc[1] - fit_margins[1] : max_loc[1] + fit_margins[1] + 1,
        max_loc[0] - fit_margins[0] : max_loc[0] + fit_margins[0] + 1,
    ]
    local_scores = local_scores.flatten()
    if local_scores.shape != (scores_w * scores_h,):
        logger.debug(f"12 {local_scores.shape=} {scores_w=} {scores_h=}")
        return  # terminate

    # print(local_scores, max_loc)
    if fit_margins[1] == 0:
        try:
            p0 = [1, 1, 1.0]
            p, _ = scipy.optimize.curve_fit(
                parabola1D,
                [x, y],
                local_scores,
                p0,
            )
        except RuntimeError:
            logger.debug("1")
            return max_loc, (0.0, 0.0), max_val
        p[0] -= fit_margins[0]
        # print(0)
        if -0.8 < p[0] < 0.8:
            # print(1)
            logger.debug("2")
            return max_loc, (p[0], 0.0), p[2]
        # fitting failed
        # print(2)
        return max_loc, (0.0, 0.0), max_val
    else:
        try:
            p0 = [1, 1, 1, 1, 1.0]
            p, _ = scipy.optimize.curve_fit(
                parabola,
                [x, y],
                local_scores,
                p0,
            )
            # print(3)
        except RuntimeError:
            # print(4)
            logger.debug("3")
            return max_loc, (0.0, 0.0), max_val
        p[0] -= fit_margins[0]
        p[1] -= fit_margins[1]
        if -1 / 2 < p[0] < 1 / 2 and -1 / 2 < p[1] < 1 / 2:
            # print(5)
            logger.debug(f"4 {local_scores=}")
            return max_loc, (p[0], p[1]), p[4]
        # fitting failed
        # print(6)
        logger.debug("5")
        return max_loc, (0.0, 0.0), max_val


def match(target_area: np.ndarray, focus: np.ndarray):
    scores = cv2.matchTemplate(target_area, focus, cv2.TM_CCOEFF)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(scores)
    return max_loc, max_val


def diffImage(frame1, frame2, dx, dy, mode="stack"):  # , focus=None, slitpos=None):
    """
    2枚のcv2画像の差を返す．
    """
    if mode == "diff":
        affine = np.matrix(((1.0, 0.0, dx), (0.0, 1.0, dy)))
        h, w = frame1.shape[0:2]
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
        affine = np.matrix(((1.0, 0.0, dx), (0.0, 1.0, dy)))
        h, w = frame1.shape[0:2]
        flags = np.arange(h) * 16 % h > h // 2
        frame1 = cv2.warpAffine(frame1, affine, (w, h))
        frame1[flags] = frame2[flags]
        return frame1
