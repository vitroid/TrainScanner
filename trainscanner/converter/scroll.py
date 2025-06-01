from PIL import Image
import subprocess
import argparse
import sys
from trainscanner.i18n import tr


def make_movie(
    image_path,
    head_right=False,
    output=None,
    duration=None,
    height=1080,
    width=1920,
    fps=30,
    bitrate=None,
    encoder="libx264",
):
    """横スクロール動画を生成します。"""
    if not output:
        output = image_path.replace(".png", ".scroll.mp4")

    image = Image.open(image_path)
    iw, ih = image.size
    print(f"Input image size: {iw}x{ih}")

    if not duration:
        duration = 2 * iw / ih

    # 画像の高さに応じて動画サイズを調整
    movie_h = height
    movie_w = width

    # 仮想的な幅を計算（アスペクト比を維持した場合の幅）
    virtual_width = iw * height // ih

    print(f"Output video size: {movie_w}x{movie_h}")

    # スクロールの総移動量を計算
    total_scroll = virtual_width - movie_w
    # 1秒あたりの移動量を計算
    scroll_per_second = total_scroll / duration

    # スクロール方向に応じて開始位置を調整
    if head_right:
        # 右から左へスクロールする場合、開始位置を右端に設定
        start_position = total_scroll
        scroll_expression = f"{start_position}-{scroll_per_second}*t"
    else:
        # 左から右へスクロールする場合、開始位置を左端に設定
        scroll_expression = f"{scroll_per_second}*t"

    # 横スクロール用のffmpegコマンド
    cmd = [
        "ffmpeg",
        "-loop 1",
        f"-r {fps}",
        "-y",
        f"-i '{image_path}'",
        f"-vf scale={virtual_width}:{movie_h},crop={movie_w}:{movie_h}:{scroll_expression}:0",
        "-pix_fmt yuv420p",
        f"-b:v {bitrate}M" if bitrate else "",
        f"-c:v {encoder}",
        f"-t {duration}",
        f"'{output}'",
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
        help=tr("Duration of the movie (seconds)") + "-- 0.1,1000",
    )
    parser.add_argument(
        "--height",
        "-H",
        type=int,
        default=1080,
        help=tr("Height of the movie (pixels)") + "-- 100,4096",
    )
    parser.add_argument(
        "--width",
        "-W",
        type=int,
        default=1920,
        help=tr("Width of the movie (pixels)") + "-- 100,4096",
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
        help=tr("Bitrate (Mbit/s)") + "-- 0.1,100",
    )
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
        args.bitrate,
        args.encoder,
    )


if __name__ == "__main__":
    main()
