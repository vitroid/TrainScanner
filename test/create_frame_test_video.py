#!/usr/bin/env python3
"""
フレーム番号を表示するテスト動画を作成するスクリプト

このスクリプトは、各フレームにフレーム番号を表示するテスト動画を生成します。
動画の解析やフレーム同期のテストに使用できます。
"""

import cv2
import numpy as np
import os
import tempfile
import argparse
import logging

# プロジェクトのffmpegモジュールをインポート
try:
    from trainscanner.video import ffmpeg
except ImportError:
    print("警告: trainscanner.video.ffmpegモジュールをインポートできませんでした。")
    print("ffmpegコマンドを直接実行します。")
    ffmpeg = None


def create_frame_with_number(
    frame_number,
    width=1920,
    height=1080,
    bg_color=(50, 50, 50),
    text_color=(255, 255, 255),
):
    """
    フレーム番号を表示するフレーム画像を作成

    Args:
        frame_number: フレーム番号
        width: 画像幅
        height: 画像高さ
        bg_color: 背景色 (B, G, R)
        text_color: テキスト色 (B, G, R)

    Returns:
        numpy.ndarray: 生成されたフレーム画像
    """
    # 背景フレームを作成
    frame = np.full((height, width, 3), bg_color, dtype=np.uint8)

    # フレーム番号を表示
    text = f"Frame {frame_number:06d}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 4.0 * width / 1920
    thickness = (8 * width + 1919) // 1920

    # テキストサイズを取得
    (text_width, text_height), baseline = cv2.getTextSize(
        text, font, font_scale, thickness
    )

    # テキストを中央に配置
    x = (width - text_width) // 2
    y = (height + text_height) // 2

    # テキストを描画
    cv2.putText(frame, text, (x, y), font, font_scale, text_color, thickness)

    # タイムコードも表示（30fps想定）
    seconds = frame_number / 30.0
    minutes = int(seconds // 60)
    seconds = seconds % 60
    timecode = f"{minutes:02d}:{seconds:06.3f}"

    # タイムコード用の小さいフォント
    timecode_font_scale = 1.5 * width / 1920
    timecode_thickness = (3 * width + 1919) // 1920
    (tc_width, tc_height), _ = cv2.getTextSize(
        timecode, font, timecode_font_scale, timecode_thickness
    )

    # タイムコードを右下に配置
    tc_x = width - tc_width - 50
    tc_y = height - 50
    cv2.putText(
        frame,
        timecode,
        (tc_x, tc_y),
        font,
        timecode_font_scale,
        (200, 200, 255),
        timecode_thickness,
    )

    # フレームレート情報を左上に表示
    fps_text = "30 FPS"
    fps_font_scale = 1
    fps_thickness = 2
    cv2.putText(
        frame, fps_text, (50, 50), font, fps_font_scale, (255, 200, 200), fps_thickness
    )

    return frame


def create_frame_test_video(
    output_file="frame_test_video.mp4",
    duration=10.0,
    fps=30,
    width=1920,
    height=1080,
    encoder="libx264",
    crf=21,
    progress_callback=None,
):
    """
    フレーム番号を表示するテスト動画を作成

    Args:
        output_file: 出力ファイル名
        duration: 動画の長さ（秒）
        fps: フレームレート
        width: 動画の幅
        height: 動画の高さ
        encoder: 動画エンコーダー
        crf: CRF値（品質設定）
        progress_callback: 進捗通知用コールバック関数
    """
    total_frames = int(duration * fps)
    logging.info(f"フレームテスト動画を作成中: {output_file}")
    logging.info(
        f"設定: {width}x{height}, {fps}fps, {duration}秒, {total_frames}フレーム"
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        logging.info(f"一時ディレクトリ: {temp_dir}")

        # 各フレームを生成して保存
        for frame_num in range(total_frames):
            frame = create_frame_with_number(
                frame_num, width=width, height=height  # 1から開始
            )

            frame_path = os.path.join(temp_dir, f"{frame_num:06d}.png")
            cv2.imwrite(frame_path, frame)

            # フレーム生成の進捗を通知（全体の50%まで）
            if progress_callback:
                progress = int((frame_num + 1) / total_frames * 50)
                progress_callback(progress)

            if (frame_num + 1) % 30 == 0:  # 1秒ごとにログ出力
                logging.info(f"フレーム生成中: {frame_num + 1}/{total_frames}")

        logging.info("フレーム生成完了。動画エンコード開始...")

        # ffmpegで動画を生成
        input_pattern = os.path.join(temp_dir, "%06d.png")

        if ffmpeg is not None:
            # プロジェクトのffmpegモジュールを使用
            def ffmpeg_progress_callback(ffmpeg_progress):
                if progress_callback:
                    # ffmpegの進捗を50%-100%の範囲にマッピング
                    overall_progress = 50 + int(ffmpeg_progress * 0.5)
                    progress_callback(overall_progress)

            ffmpeg.run(
                input_filename=input_pattern,
                output_filename=output_file,
                fps=fps,
                encoder=encoder,
                crf=crf,
                total_frames=total_frames,
                progress_callback=ffmpeg_progress_callback,
            )
        else:
            # ffmpegコマンドを直接実行
            import subprocess

            cmd = [
                "ffmpeg",
                "-y",
                "-framerate",
                str(fps),
                "-i",
                input_pattern,
                "-c:v",
                encoder,
                "-pix_fmt",
                "yuv420p",
            ]
            if crf:
                cmd.extend(["-crf", str(crf)])
            cmd.append(output_file)

            logging.info(f"ffmpegコマンド実行: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logging.error(f"ffmpeg実行エラー: {result.stderr}")
                raise RuntimeError(f"ffmpeg実行に失敗しました: {result.stderr}")

            if progress_callback:
                progress_callback(100)

    # 出力ファイルの確認
    if os.path.exists(output_file):
        file_size = os.path.getsize(output_file)
        logging.info(f"動画作成完了: {output_file}")
        logging.info(
            f"ファイルサイズ: {file_size:,} バイト ({file_size / 1024 / 1024:.2f} MB)"
        )
    else:
        logging.error("出力ファイルが作成されませんでした")


def progress_callback(progress):
    """進捗表示用コールバック関数"""
    print(f"\r進捗: {progress}%", end="", flush=True)
    if progress >= 100:
        print()  # 改行


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="フレーム番号を表示するテスト動画を作成"
    )

    parser.add_argument(
        "-o",
        "--output",
        default="frame_test_video.mp4",
        help="出力ファイル名 (デフォルト: frame_test_video.mp4)",
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=float,
        default=10.0,
        help="動画の長さ（秒） (デフォルト: 10.0)",
    )
    parser.add_argument(
        "-f", "--fps", type=int, default=30, help="フレームレート (デフォルト: 30)"
    )
    parser.add_argument(
        "-W", "--width", type=int, default=1920, help="動画の幅 (デフォルト: 1920)"
    )
    parser.add_argument(
        "-H", "--height", type=int, default=1080, help="動画の高さ (デフォルト: 1080)"
    )
    parser.add_argument(
        "-e",
        "--encoder",
        default="libx264",
        help="動画エンコーダー (デフォルト: libx264)",
    )
    parser.add_argument(
        "-c",
        "--crf",
        type=int,
        default=21,
        help="CRF値（品質設定、小さいほど高品質） (デフォルト: 21)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細なログを表示")

    args = parser.parse_args()

    # ログ設定
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    try:
        create_frame_test_video(
            output_file=args.output,
            duration=args.duration,
            fps=args.fps,
            width=args.width,
            height=args.height,
            encoder=args.encoder,
            crf=args.crf,
            progress_callback=progress_callback,
        )
        print(f"✓ フレームテスト動画の作成が完了しました: {args.output}")

    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")
        print(f"✗ エラー: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
