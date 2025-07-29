import cv2
import numpy as np
import scipy.optimize


def standardize(x):
    return ((x - np.mean(x)) / np.std(x)).astype(np.float32)


def subpixel_match(
    target_area: np.ndarray, focus: np.ndarray, fit_width=2, subpixel=True
):
    scores = cv2.matchTemplate(target_area, focus, cv2.TM_SQDIFF)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(scores)
    # print(
    #         f"target_area: {target_area.shape} focus: {focus.shape} scores: {scores.shape} min_loc: {min_loc}"
    # )

    # もし、min_locが端すぎる場合には、subpixelは返さない。
    if (
        not (
            fit_width <= min_loc[0] < scores.shape[0] - fit_width
            and fit_width <= min_loc[1] < scores.shape[1] - fit_width
        )
        or not subpixel
    ):
        return min_loc, (0.0, 0.0)

    def parabola(xy, x0, y0, sigma_x, sigma_y, B):
        x, y = xy
        return ((x - x0) ** 2 / (2 * sigma_x**2) + (y - y0) ** 2 / (2 * sigma_y**2)) + B

    x, y = np.meshgrid(np.arange(fit_width * 2 + 1), np.arange(fit_width * 2 + 1))
    x = x.flatten()
    y = y.flatten()
    local_scores = scores[
        min_loc[1] - fit_width : min_loc[1] + fit_width + 1,
        min_loc[0] - fit_width : min_loc[0] + fit_width + 1,
    ]
    local_scores = standardize(local_scores).flatten()
    if local_scores.shape != ((fit_width * 2 + 1) ** 2,):
        return  # terminate
    p0 = [1, 1, 1, 1, -2.0]

    try:
        p, _ = scipy.optimize.curve_fit(
            parabola,
            [x, y],
            local_scores,
            p0,
        )
    except RuntimeError:
        return min_loc, (0.0, 0.0)
    p[0] -= fit_width
    p[1] -= fit_width
    if -1 / 2 < p[0] < 1 / 2 and -1 / 2 < p[1] < 1 / 2:
        return min_loc, (p[0], p[1])
    # fitting failed
    return min_loc, (0.0, 0.0)
