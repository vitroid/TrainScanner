import cv2
import numpy as np
import scipy.optimize


def standardize(x):
    return ((x - np.mean(x)) / np.std(x)).astype(np.float32)


def subpixel_match(
    target_area: np.ndarray, focus: np.ndarray, fit_width=[2, 2], subpixel=True
):
    scores = cv2.matchTemplate(target_area, focus, cv2.TM_CCOEFF)
    scores_resized = cv2.resize(
        scores, (scores.shape[1], 10), interpolation=cv2.INTER_NEAREST
    )
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(scores)
    # print(10, fit_width, max_loc, scores.shape)
    # print(
    #         f"target_area: {target_area.shape} focus: {focus.shape} scores: {scores.shape} min_loc: {min_loc}"
    # )

    # もし、min_locが端すぎる場合には、subpixelは返さない。
    if (
        not (
            fit_width[0] <= max_loc[0] < scores.shape[1] - fit_width[0]
            and fit_width[1] <= max_loc[1] < scores.shape[0] - fit_width[1]
        )
        or not subpixel
    ):
        # print(11)
        return max_loc, (0.0, 0.0), max_val

    def parabola(xy, x0, y0, sigma_x, sigma_y, B):
        x, y = xy
        return (
            -((x - x0) ** 2) / (2 * sigma_x**2) - (y - y0) ** 2 / (2 * sigma_y**2)
        ) + B

    def parabola1D(xy, x0, sigma_x, B):
        x, y = xy
        return (-((x - x0) ** 2) / (2 * sigma_x**2)) + B

    x, y = np.meshgrid(np.arange(fit_width[0] * 2 + 1), np.arange(fit_width[1] * 2 + 1))
    x = x.flatten()
    y = y.flatten()
    local_scores = scores[
        max_loc[1] - fit_width[1] : max_loc[1] + fit_width[1] + 1,
        max_loc[0] - fit_width[0] : max_loc[0] + fit_width[0] + 1,
    ]
    local_scores = standardize(local_scores).flatten()
    if local_scores.shape != ((fit_width[0] * 2 + 1) * (fit_width[1] * 2 + 1),):
        # print(12)
        return  # terminate

    # print(local_scores, max_loc)
    if fit_width[1] == 0:
        try:
            p0 = [1, 1, 1.0]
            p, _ = scipy.optimize.curve_fit(
                parabola1D,
                [x, y],
                local_scores,
                p0,
            )
        except RuntimeError:
            return max_loc, (0.0, 0.0), max_val
        p[0] -= fit_width[0]
        # print(0)
        if -0.8 < p[0] < 0.8:
            # print(1)
            value = parabola1D([x, y], p[0], p[1], p[2])
            return max_loc, (p[0], 0.0), value
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
            return max_loc, (0.0, 0.0), max_val
        p[0] -= fit_width[0]
        p[1] -= fit_width[1]
        if -1 / 2 < p[0] < 1 / 2 and -1 / 2 < p[1] < 1 / 2:
            # print(5)
            value = parabola([x, y], p[0], p[1], p[2], p[3], p[4])
            return max_loc, (p[0], p[1]), value
        # fitting failed
        # print(6)
        return max_loc, (0.0, 0.0), max_val


def match(target_area: np.ndarray, focus: np.ndarray):
    scores = cv2.matchTemplate(target_area, focus, cv2.TM_CCOEFF)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(scores)
    return max_loc, max_val
