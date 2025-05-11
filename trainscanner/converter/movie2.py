from PIL import Image, ImageDraw
import subprocess
import click
import os
import tempfile
import shutil
import logging


def make_movie(
    image_path, head_right=False, output=None, duration=None, height=1080, width=1920
):
    logger = logging.getLogger()
    """横スクロール動画を生成します。"""
    if not output:
        output = image_path.replace(".png", ".mp4")

    image = Image.open(image_path)
    iw, ih = image.size
    print(f"Input image size: {iw}x{ih}")

    if not duration:
        duration = 2 * iw / ih

    tn_height = ih * width // iw
    thumbnail = image.resize((width, tn_height), Image.Resampling.LANCZOS)

    viewport_height = height - tn_height

    scaled_iw = iw * viewport_height // ih

    # 画像をスケーリング
    scaled = image.resize((scaled_iw, viewport_height), Image.Resampling.LANCZOS)

    print(f"Output video size: {width}x{height}")
    print(f"Thumbnail size: {width}x{tn_height}")

    # スクロールの総移動量を計算
    total_scroll = scaled_iw - width
    # 1秒あたりの移動量を計算
    scroll_per_second = total_scroll / duration

    single_frame = Image.new("RGB", (width, height), (255, 255, 255))

    # 一時ディレクトリを作成して管理
    with tempfile.TemporaryDirectory() as temp_dir:
        # フレームレート
        fps = 30
        total_frames = int(duration * fps)

        # 各フレームを生成
        for frame in range(total_frames):
            logger.info(f"Processing frame {frame} of {total_frames}")
            # 現在のスクロール位置を計算
            if head_right:
                # 右から左へスクロールする場合
                current_scroll = total_scroll - int(scroll_per_second * (frame / fps))
            else:
                # 左から右へスクロールする場合
                current_scroll = int(scroll_per_second * (frame / fps))

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
            frame_path = os.path.join(temp_dir, f"frame_{frame:06d}.png")
            single_frame.save(frame_path)

        # ffmpegで動画を生成
        cmd = f'ffmpeg -y -framerate {fps} -i "{temp_dir}/frame_%06d.png" -c:v libx264 -pix_fmt yuv420p "{output}"'
        print(cmd)
        subprocess.run(cmd, shell=True)


@click.command()
@click.argument("image_path")
@click.option("--output", "-o", help="出力ファイルのパス")
@click.option("--duration", "-d", type=float, help="動画の長さ（秒）")
@click.option("--height", "-h", type=int, default=1080, help="目標の高さ")
@click.option("--width", "-w", type=int, default=1920, help="目標の幅")
@click.option("--head-right", "-R", is_flag=True, help="右端が先頭")
def main(image_path, head_right, output, duration, height, width):
    make_movie(image_path, head_right, output, duration, height, width)


if __name__ == "__main__":
    main()
