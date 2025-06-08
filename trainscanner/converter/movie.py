import cv2
import numpy as np
import subprocess
import argparse
import os
import tempfile
import shutil
import logging
from tqdm import tqdm
import sys
from trainscanner.i18n import tr, init_translations
import time


def movie_iter(
    image: np.ndarray,
    head_right: bool = False,
    duration: float = None,
    height: int = 1080,
    width: int = 1920,
    fps: int = 30,
    alternating: bool = False,
    accel: bool = False,
    thumbnail: bool = False,
):
    """横スクロール動画を生成します。"""
    logger = logging.getLogger()

    ih, iw = image.shape[:2]

    if not duration:
        duration = 2 * iw / ih

    if thumbnail:
        tn_height = ih * width // iw
        thumbnail_image = cv2.resize(
            image, (width, tn_height), interpolation=cv2.INTER_LANCZOS4
        )
    else:
        tn_height = 0
        thumbnail_image = None

    viewport_height = height - tn_height
    if viewport_height < tn_height:
        raise ValueError("viewport_height is too small")

    scaled_iw = iw * viewport_height // ih

    # 画像をスケーリング
    scaled = cv2.resize(
        image, (scaled_iw, viewport_height), interpolation=cv2.INTER_LINEAR
    )
    # スクロールの総移動量を計算
    total_scroll = scaled_iw - width
    # 全フレーム数
    total_frames = int(duration * fps)

    frame_pointers = [0] * total_frames
    if accel:
        # 等加速度
        # 加速度aとすると、a (total_frames/2)**2 = total_scroll/2
        # よって、
        a = total_scroll / (total_frames / 2) ** 2 / 2
        for frame in range(total_frames // 2):
            current_scroll = int(a * frame**2)
            frame_pointers[frame] = current_scroll
            frame_pointers[total_frames - 1 - frame] = total_scroll - current_scroll
    else:
        scroll_per_frame = total_scroll / total_frames
        for frame in range(total_frames):
            # 左から右へスクロールする場合
            current_scroll = int(frame * scroll_per_frame)
            frame_pointers[frame] = current_scroll

    if head_right:
        frame_pointers = frame_pointers[::-1]

    if alternating:
        frame_pointers = frame_pointers + frame_pointers[::-1]

    # 一時ディレクトリを作成して管理
    # フレームレート

    # 各フレームを生成
    # for frame in tqdm(range(total_frames)):
    for frame in tqdm(range(len(frame_pointers))):
        # for frame in range(len(frame_pointers)):
        single_frame = np.zeros((height, width, 3), dtype=np.uint8)
        # 現在のスクロール位置を計算
        current_scroll = frame_pointers[frame]

        # 必要な部分を切り出し
        cropped = scaled[:, current_scroll : current_scroll + width]
        single_frame[tn_height:] = cropped

        if thumbnail:
            single_frame[:tn_height] = thumbnail_image

            marker_x = current_scroll * width // scaled_iw
            marker_width = width * width // scaled_iw

            # ビューポート領域を四角で囲む
            cv2.rectangle(
                single_frame,
                (marker_x, 0),
                (marker_x + marker_width, tn_height),
                (0, 0, 255),
                2,
            )

        yield single_frame


def make_movie(
    image: str,
    output: str,
    head_right: bool = False,
    duration: float = 8,
    height: int = 1080,
    width: int = 1920,
    fps: int = 30,
    alternating: bool = False,
    png: bool = False,
    crf: int = None,
    accel: bool = False,
    encoder: str = "libx264",
    thumbnail: bool = False,
):
    if png:
        ext = "png"
    else:
        ext = "jpg"

    with tempfile.TemporaryDirectory() as temp_dir:
        for i, frame in enumerate(
            movie_iter(
                image,
                head_right,
                duration,
                height,
                width,
                fps,
                alternating,
                accel,
                thumbnail,
            )
        ):
            frame_path = os.path.join(temp_dir, f"frame_{i:06d}.{ext}")
            cv2.imwrite(frame_path, frame)

        cmd = [
            "ffmpeg",
            "-y",
            f"-framerate {fps}",
            f'-i "{temp_dir}/frame_%06d.{ext}"',
            f"-c:v {encoder}",
            "-pix_fmt yuv420p",
            f"-crf {crf}" if crf else "",
            f'"{output}"',
        ]
        cmd = " ".join(cmd)
        print(cmd)
        subprocess.run(cmd, shell=True)


def get_parser():
    """
    コマンドライン引数のパーサーを生成して返す関数
    """
    parser = argparse.ArgumentParser(description=tr("Make a movie from a train image"))
    parser.add_argument("image_path", help=tr("Path of the input image file"))
    parser.add_argument("--output", "-o", help=tr("Path of the output file"))
    parser.add_argument(
        "--duration",
        "-d",
        type=float,
        default=8,
        help=tr("Duration of the movie (seconds)") + "-- 10,1000",
    )
    parser.add_argument(
        "--height",
        "-H",
        type=int,
        default=1080,
        help=tr("Height of the movie") + "-- 100,4096",
    )
    parser.add_argument(
        "--width",
        "-W",
        type=int,
        default=1920,
        help=tr("Width of the movie") + "-- 100,4096",
    )
    parser.add_argument(
        "--head-right",
        "-R",
        action="store_true",
        help=tr("The train heads to the right."),
    )
    parser.add_argument(
        "--fps", "-r", type=int, default=30, help=tr("Frame rate") + "-- 1,120"
    )
    parser.add_argument(
        "--crf",
        "-c",
        type=int,
        default=21,
        help=tr("CRF (Constant Rate Factor)") + " -- 16,30",
    )
    parser.add_argument(
        "--png", "-p", action="store_true", help=tr("Intermediate files are png")
    )
    parser.add_argument(
        "--alternating", "-a", action="store_true", help=tr("Go back and forth")
    )
    parser.add_argument("--accel", "-A", action="store_true", help=tr("Acceleration"))
    parser.add_argument(
        "--encoder", "-e", type=str, default="libx264", help=tr("mp4 encoder")
    )
    parser.add_argument(
        "--thumbnail",
        "-t",
        action="store_true",
        help=tr("Add a thumbnail (Yamako style)"),
    )
    return parser


def main():
    init_translations()

    parser = get_parser()
    args = parser.parse_args()

    output = args.image_path.replace(".png", ".ymk.mp4")

    image = cv2.imread(args.image_path)

    make_movie(
        image,
        output,
        head_right=args.head_right,
        duration=args.duration,
        height=args.height,
        width=args.width,
        fps=args.fps,
        alternating=args.alternating,
        png=args.png,
        crf=args.crf,
        accel=args.accel,
        encoder=args.encoder,
        thumbnail=args.thumbnail,
    )


if __name__ == "__main__":
    main()
