import cv2
import numpy as np
import scipy.optimize


def standardize(x):
    return ((x - np.mean(x)) / np.std(x)).astype(np.float32)


def subpixel_match(target_area: np.ndarray, focus: np.ndarray, fit_width=2):
    scores = cv2.matchTemplate(target_area, focus, cv2.TM_SQDIFF)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(scores)

    def parabola(xy, x0, y0, sigma_x, sigma_y, B):
        x, y = xy
        return ((x - x0) ** 2 / (2 * sigma_x**2) + (y - y0) ** 2 / (2 * sigma_y**2)) + B

    x, y = np.meshgrid(np.arange(fit_width * 2 + 1), np.arange(fit_width * 2 + 1))
    x = x.flatten()
    y = y.flatten()
    local_scores = standardize(
        scores[
            min_loc[1] - fit_width : min_loc[1] + fit_width + 1,
            min_loc[0] - fit_width : min_loc[0] + fit_width + 1,
        ]
    ).flatten()
    if local_scores.shape != ((fit_width * 2 + 1) ** 2,):
        return  # terminate
    p0 = [1, 1, 1, 1, -2.0]
    p, _ = scipy.optimize.curve_fit(
        parabola,
        [x, y],
        local_scores,
        p0,
    )
    return min_loc, (p[0] - fit_width, p[1] - fit_width)
