from PIL import Image, ImageDraw
import subprocess
import argparse
import os
import tempfile
import shutil
import logging
from tqdm import tqdm
import sys
from trainscanner.i18n import tr


def make_movie(
    image_path: str,
    head_right: bool = False,
    output: str = None,
    duration: float = None,
    height: int = 1080,
    width: int = 1920,
    fps: int = 30,
    alternating: bool = False,
    png: bool = False,
    bitrate: int = None,
    accel: bool = False,
    encoder: str = "libx264",
):
    """横スクロール動画を生成します。"""
    logger = logging.getLogger()

    if not output:
        output = image_path.replace(".png", ".ymk.mp4")

    image = Image.open(image_path)
    iw, ih = image.size
    print(f"Input image size: {iw}x{ih}")

    if not duration:
        duration = 2 * iw / ih

    tn_height = ih * width // iw
    thumbnail = image.resize((width, tn_height), Image.Resampling.LANCZOS)

    viewport_height = height - tn_height
    if viewport_height < tn_height:
        raise ValueError("viewport_height is too small")

    scaled_iw = iw * viewport_height // ih

    # 画像をスケーリング
    scaled = image.resize((scaled_iw, viewport_height), Image.Resampling.LANCZOS)

    print(f"Output video size: {width}x{height}")
    print(f"Thumbnail size: {width}x{tn_height}")

    # スクロールの総移動量を計算
    total_scroll = scaled_iw - width
    # 全フレーム数
    total_frames = int(duration * fps)

    single_frame = Image.new("RGB", (width, height), (255, 255, 255))

    if png:
        ext = "png"
    else:
        ext = "jpg"

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

    # 一時ディレクトリを作成して管理
    with tempfile.TemporaryDirectory() as temp_dir:
        # フレームレート
        total_frames = int(duration * fps)

        # 各フレームを生成
        for frame in tqdm(range(total_frames)):
            # 現在のスクロール位置を計算
            current_scroll = frame_pointers[frame]

            single_frame.paste(thumbnail, (0, 0))

            # 必要な部分を切り出し
            cropped = scaled.crop(
                (current_scroll, 0, current_scroll + width, viewport_height)
            )
            single_frame.paste(cropped, (0, tn_height))

            marker_x = current_scroll * width // scaled_iw
            marker_width = width * width // scaled_iw

            # ビューポート領域を四角で囲む
            draw = ImageDraw.Draw(single_frame)
            # 太さ2ピクセルの赤い線で四角を描画
            draw.rectangle(
                [(marker_x, 0), (marker_x + marker_width, tn_height)],
                outline=(255, 0, 0),
                width=2,
            )

            # フレームを保存
            frame_path = os.path.join(temp_dir, f"frame_{frame:06d}.{ext}")
            single_frame.save(frame_path)

            # -loop_alternateの場合は、テンポラリ画像フォルダーに逆順の画像を作成する。
            # 実際に作成するのではなく、シンボリックリンクを作成する。
            if alternating:
                os.link(
                    frame_path,
                    os.path.join(
                        temp_dir, f"frame_{total_frames*2-1 - frame:06d}.{ext}"
                    ),
                )

        cmd = [
            "ffmpeg",
            "-y",
            f"-framerate {fps}",
            f'-i "{temp_dir}/frame_%06d.{ext}"',
            f"-c:v {encoder}",
            "-pix_fmt yuv420p",
            f"-b:v {bitrate}M" if bitrate else "",
            f'"{output}"',
        ]
        cmd = " ".join(cmd)
        print(cmd)
        subprocess.run(cmd, shell=True)


def get_parser():
    """
    コマンドライン引数のパーサーを生成して返す関数
    """
    parser = argparse.ArgumentParser(
        description=tr("Make a movie with a thumbnail from a train image")
    )
    parser.add_argument("image_path", help=tr("Path of the input image file"))
    parser.add_argument("--output", "-o", help=tr("Path of the output file"))
    parser.add_argument(
        "--duration",
        "-d",
        type=float,
        default=8,
        help=tr("Duration of the movie (seconds)") + "-- 0.1,1000",
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
        "--bitrate",
        "-b",
        type=float,
        default=8,
        help=tr("Bitrate (Mbit/s)") + " -- 0.1,100",
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
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    make_movie(
        args.image_path,
        args.head_right,
        args.output,
        args.duration,
        args.height,
        args.width,
        args.fps,
        args.alternating,
        args.png,
        args.bitrate,
        args.accel,
        args.encoder,
    )


if __name__ == "__main__":
    main()
