import subprocess


def run(input_filename: str, output_filename: str, fps: int, encoder: str, crf: int):
    ext = "png"
    cmd = [
        "ffmpeg",
        "-y",
        f"-framerate {fps}",
        f'-i "{input_filename}"',
        f"-c:v {encoder}",
        "-pix_fmt yuv420p",
        f"-crf {crf}" if crf else "",
        f'"{output_filename}"',
    ]
    cmd = " ".join(cmd)
    print(cmd)
    subprocess.run(cmd, shell=True)
