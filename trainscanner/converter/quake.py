# スリット位置を±10ほどずらして、それぞれの画像をマッチングさせる。
# stitch.pyを内部で呼びだす。

# usage: quake filename.tsconf
import click
import tiledimage.cachedimage as ci
from trainscanner.stitch import Stitcher
import numpy as np
import tempfile
import cv2
from tqdm import tqdm


def parse_tsconf(tsconf):
    options = {}
    basename = tsconf.pop(0)
    nextflag = None
    args = []
    while len(tsconf):
        arg = tsconf.pop(0)
        if len(arg) > 2 and arg[:2] == "--":
            if nextflag is not None:
                options[nextflag] = args
            nextflag = arg
            args = []
            continue
        args.append(arg)

    if nextflag is not None:
        options[nextflag] = args
    return basename, options


def run_stitch(basename, options, outfilename=None, width=None):
    # stitch.pyを内部で呼びだす。
    # コマンドラインではなく、関数として呼びたい。
    # optionsを展開
    args = ["dummy_command_name", basename]
    for key, value in options.items():
        args.append(key)
        args.extend(value)

    st = Stitcher(argv=args, outfilename=outfilename)

    tilesize = (512, 512)  # canbe smaller for smaller machine
    cachesize = 10
    with ci.CachedImage(
        "new", dir=st.cachedir, tilesize=tilesize, cachesize=cachesize
    ) as canvas:
        st.set_canvas(canvas)
        st.stitch()
        img = st.canvas.get_image()
        if width is not None:
            width = (width // 2) * 2
            height = img.shape[0] * width // img.shape[1]
            height = (height // 2) * 2
            img = cv2.resize(img, (width, height))
        cv2.imwrite(outfilename, img)


@click.command()
@click.argument("filename", type=click.Path(exists=True))
@click.option(
    "--slit_start",
    type=int,
    default=-20,
    help="start slit position (default to -20%) -50: left end; 0: center; +50: right end",
)
@click.option(
    "--slit_end",
    type=int,
    default=20,
    help="end slit position (default to 20%) -50: left end; 0: center; +50: right end",
)
@click.option("--frames", type=int, default=20, help="number of frames (default to 20)")
@click.option(
    "--width", type=int, default=3840, help="Width of output video (default to 3840)"
)
def main(filename, slit_start, slit_end, frames, width):
    # tsconfを読み込む
    with open(filename, "r") as f:
        tsconf = [x.rstrip() for x in f.readlines()]

    # ファイル名を取得
    basename, options = parse_tsconf(tsconf)
    original_slit = int(options["--slit"][0])
    original_logbase = options["--log"][0]

    # 中間ファイルのディレクトリを作成
    with tempfile.TemporaryDirectory() as tempdir:
        for i, slit_percent in tqdm(
            enumerate(np.linspace(slit_start, slit_end, frames)),
            total=frames,
        ):
            slit_permill = int(slit_percent * 10)
            options["--slit"] = [str(slit_permill)]
            # stitch.pyを内部で呼びだす。
            run_stitch(
                basename,
                options,
                outfilename=f"{tempdir}/{i:06d}.png",
                width=width,
            )
        import os

        for i in range(frames):
            os.link(
                f"{tempdir}/{i:06d}.png",
                f"{tempdir}/{frames*2-1-i:06d}.png",
            )

        # 中間ファイルをffmpegで動画に
        import subprocess
        import os

        # 中間ファイルのパスを取得
        intermediate_files = f"{tempdir}/%06d.png"

        # ffmpegで動画に
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-r",
                "30",
                "-i",
                f"{intermediate_files}",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                f"{original_logbase}.quake.mp4",
            ]
        )


if __name__ == "__main__":
    main()
