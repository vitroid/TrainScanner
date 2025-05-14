from PIL import Image
import subprocess
import click
import sys


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
        f"-b:v {bitrate}" if bitrate else "",
        f"-c:v {encoder}",
        f"-t {duration}",
        f"'{output}'",
    ]
    cmd = " ".join(cmd)
    print(cmd)

    subprocess.run(cmd, shell=True)


@click.command()
@click.argument("image_path")
@click.option("--output", "-o", help="出力ファイルのパス")
@click.option("--duration", "-d", type=float, help="動画の長さ（秒）")
@click.option("--height", "-h", type=int, default=1080, help="目標の高さ")
@click.option("--width", "-w", type=int, default=1920, help="目標の幅")
@click.option("--head-right", "-R", is_flag=True, help="右端が先頭")
@click.option("--fps", "-r", type=int, default=30, help="フレームレート")
@click.option("--bitrate", "-b", type=int, default=None, help="ビットレート")
@click.option("--encoder", "-e", type=str, default="libx264", help="mp4エンコーダー")
def main(
    image_path, head_right, output, duration, height, width, fps, bitrate, encoder
):
    """
    Make a movie from a train image
    """
    make_movie(
        image_path, head_right, output, duration, height, width, fps, bitrate, encoder
    )


if __name__ == "__main__":
    main()
