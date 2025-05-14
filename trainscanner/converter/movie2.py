from PIL import Image, ImageDraw
import subprocess
import click
import os
import tempfile
import shutil
import logging
from tqdm import tqdm
import sys


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
            f"-b:v {bitrate}" if bitrate else "",
            f'"{output}"',
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
@click.option("--png", "-p", is_flag=True, help="中間ファイルをpngにする")
@click.option("--alternating", "-a", is_flag=True, help="前進+後退")
@click.option("--accel", "-A", is_flag=True, help="加速")
@click.option("--encoder", "-e", type=str, default="libx264", help="mp4エンコーダー")
def main(
    image_path,
    head_right,
    output,
    duration,
    height,
    width,
    fps,
    alternating,
    png,
    bitrate,
    accel,
    encoder,
):
    """
    Make a movie with a thumbnailfrom a train image
    """
    make_movie(
        image_path,
        head_right,
        output,
        duration,
        height,
        width,
        fps,
        alternating,
        png,
        bitrate,
        accel,
        encoder,
    )


if __name__ == "__main__":
    main()
