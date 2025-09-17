from dataclasses import dataclass


@dataclass
class Region:
    """
    cv2-like region specification.
    """

    left: int
    right: int
    top: int
    bottom: int

    def validate(self, minimal_size: tuple[int, int]):
        if self.left >= self.right or self.top >= self.bottom:
            raise ValueError("Invalid region")
        if (
            self.right - self.left < minimal_size[0]
            or self.bottom - self.top < minimal_size[1]
        ):
            raise ValueError("Region is too small")


def trim_region(region: Region, image_shape: tuple[int, int]) -> Region:
    """
    画像の範囲を超える領域をtrimする。
    """
    top = max(0, region.top)
    bottom = min(image_shape[0], region.bottom)
    left = max(0, region.left)
    right = min(image_shape[1], region.right)
    return Region(top=top, bottom=bottom, left=left, right=right)


def region_to_cvrect(region: Region) -> tuple[int, int, int, int]:
    return (
        region.left,
        region.top,
        region.right - region.left,
        region.bottom - region.top,
    )
