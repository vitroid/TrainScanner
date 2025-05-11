from PIL import Image
import subprocess
import click


def make_movie(image_path, output=None, duration=None, height=1080, width=1920):
    """横スクロール動画を生成します。"""
    if not output:
        output = image_path.replace(".png", ".mp4")

    image = Image.open(image_path)
    iw, ih = image.size
    print(f"Input image size: {iw}x{ih}")

    if not duration:
        duration = 2 * iw / ih

    # 画像の高さに応じて動画サイズを調整
    if ih < height:
        # 画像の高さが目標未満の場合、アスペクト比を保って幅を調整
        movie_h = ih
        movie_w = int(width * (ih / height))
        if movie_w % 2 == 1:
            movie_w += 1
        if movie_h % 2 == 1:
            movie_h -= 1
    else:
        # 画像の高さが目標以上の場合、高さを目標に制限
        movie_h = height
        movie_w = width

    print(f"Output video size: {movie_w}x{movie_h}")

    # スクロールの総移動量を計算
    total_scroll = iw - movie_w
    # 1秒あたりの移動量を計算
    scroll_per_second = total_scroll / duration

    # 横スクロール用のffmpegコマンド
    cmd = f'ffmpeg -loop 1 -r 30 -y -i "{image_path}" -vf "crop={movie_w}:{movie_h}:{scroll_per_second}*t:0,scale={movie_w}:{movie_h}" -pix_fmt yuv420p -t {duration} "{output}"'
    print(cmd)

    subprocess.run(cmd, shell=True)


@click.command()
@click.argument("image_path")
@click.option("--output", "-o", help="出力ファイルのパス")
@click.option("--duration", "-d", type=float, help="動画の長さ（秒）")
@click.option("--height", "-h", type=int, default=1080, help="目標の高さ")
@click.option("--width", "-w", type=int, default=1920, help="目標の幅")
def main(image_path, output, duration, height, width):
    make_movie(image_path, output, duration, height, width)


if __name__ == "__main__":
    main()
