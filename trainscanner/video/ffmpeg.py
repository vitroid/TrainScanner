import subprocess
import re
import sys


def run(
    input_filename: str,
    output_filename: str,
    fps: int,
    encoder: str,
    crf: int,
    total_frames: int,
    progress_callback=None,
):
    """
    ffmpegを実行してビデオを生成する

    Args:
        input_filename: 入力ファイル名（フレームパターン）
        output_filename: 出力ファイル名
        fps: フレームレート
        encoder: エンコーダー
        crf: CRF値
        progress_callback: 進捗通知用のコールバック関数（0-100の値を引数として受け取る）
    """
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
        "-progress",
        "pipe:1",  # 進捗情報を標準出力に出力
    ]
    cmd = " ".join(cmd)
    print(cmd)

    # 進捗パターンをコンパイル
    frame_pattern = re.compile(r"frame=(\d+)")
    fps_pattern = re.compile(r"fps=(\d+\.?\d*)")
    q_pattern = re.compile(r"q=(\d+\.?\d*)")
    size_pattern = re.compile(r"size=\s*(\d+)kB")
    time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
    bitrate_pattern = re.compile(r"bitrate=\s*(\d+\.?\d*)kbits/s")

    # プロセスを開始
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1,
    )

    last_progress = -1

    try:
        for line in process.stdout:
            line = line.strip()

            # フレーム進捗を取得
            frame_match = frame_pattern.search(line)
            if frame_match and total_frames:
                current_frame = int(frame_match.group(1))
                progress = min(100, int((current_frame / total_frames) * 100))

                # 1%以上進んだ場合のみ通知
                if progress > last_progress and progress_callback:
                    progress_callback(progress)
                    last_progress = progress
                    print(
                        f"フレーム {current_frame}/{total_frames} ({progress}%)",
                        file=sys.stderr,
                    )

            # その他の進捗情報も表示
            fps_match = fps_pattern.search(line)
            if fps_match:
                current_fps = fps_match.group(1)
                print(f"FPS: {current_fps}", file=sys.stderr)

            # エラー出力も表示
            print(line, file=sys.stderr)

    except KeyboardInterrupt:
        process.terminate()
        raise

    # プロセスが終了するまで待機
    process.wait()

    # 完了時は100%を通知
    if progress_callback and last_progress < 100:
        progress_callback(100)


def test_image_sequence_to_video():
    """
    指定されたディレクトリの画像シーケンスを読み込んで動画に変換するテスト関数
    """
    import os
    import glob

    # テスト用のディレクトリとファイル名を設定
    input_dir = "examples/sample.mov.dir"  # 画像シーケンスのディレクトリ
    input_dir = "/Users/matto/Downloads/Freight Train Passing Unmanned Level Crossing  Canada  Canadian Trains .mp4.dir"
    output_file = "test_output.mp4"  # 出力動画ファイル
    fps = 30  # フレームレート
    encoder = "libx264"  # エンコーダー
    crf = 21  # CRF値

    # ディレクトリが存在するかチェック
    if not os.path.exists(input_dir):
        print(f"エラー: ディレクトリ '{input_dir}' が存在しません")
        return

    # 画像ファイルを検索（PNG形式を想定）
    image_pattern = os.path.join(input_dir, "*.png")
    image_files = sorted(glob.glob(image_pattern))

    if not image_files:
        print(f"エラー: ディレクトリ '{input_dir}' にPNGファイルが見つかりません")
        return

    print(f"見つかった画像ファイル数: {len(image_files)}")
    print(f"最初のファイル: {image_files[0]}")
    print(f"最後のファイル: {image_files[-1]}")

    # 進捗コールバック関数
    def progress_callback(progress):
        print(f"進捗: {progress}%")

    # 入力ファイル名パターンを作成（ffmpeg用）
    # 例: examples/sample3.mov.dir/%06d.png
    input_pattern = os.path.join(input_dir, "%06d.png")

    print(f"変換開始: {input_pattern} -> {output_file}")
    print(f"設定: FPS={fps}, エンコーダー={encoder}, CRF={crf}")

    try:
        # ffmpegで変換実行
        run(
            input_filename=input_pattern,
            output_filename=output_file,
            fps=fps,
            encoder=encoder,
            crf=crf,
            progress_callback=progress_callback,
        )

        print(f"変換完了: {output_file}")

        # 出力ファイルのサイズを確認
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(
                f"出力ファイルサイズ: {file_size:,} バイト ({file_size / 1024 / 1024:.2f} MB)"
            )
        else:
            print("警告: 出力ファイルが作成されませんでした")

    except Exception as e:
        print(f"エラーが発生しました: {e}")


if __name__ == "__main__":
    # テスト実行
    test_image_sequence_to_video()
