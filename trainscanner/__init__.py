import numpy as np
from dataclasses import dataclass


@dataclass
class FramePosition:
    index: int
    dt: int
    velocity: tuple[float, float]


@dataclass
class MatchResult:
    index: int
    dt: int
    velocity: tuple[float, float]
    value: float
    image: np.ndarray
