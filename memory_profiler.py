#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TrainScannerのメモリー使用量をプロファイリングするためのスクリプト
"""

import sys
import argparse
import subprocess
import time
from pathlib import Path
from trainscanner.memory_monitor import create_memory_monitor_with_logger


def run_trainscanner_with_memory_monitoring(
    trainscanner_args: list[str],
    log_file: str = "trainscanner_memory.csv",
    interval: float = 1.0,
):
    """
    TrainScannerを実行しながらメモリー使用量を監視する

    Args:
        trainscanner_args: TrainScannerに渡す引数のリスト
        log_file: メモリー使用量ログファイルのパス
        interval: 監視間隔（秒）
    """
    print(f"TrainScannerを起動してメモリー使用量を監視します...")
    print(f"ログファイル: {log_file}")
    print(f"監視間隔: {interval}秒")

    # TrainScannerプロセスを開始
    trainscanner_cmd = [
        "python",
        "-m",
        "trainscanner.gui.trainscanner",
    ] + trainscanner_args
    print(f"実行コマンド: {' '.join(trainscanner_cmd)}")

    try:
        # TrainScannerプロセスを開始
        process = subprocess.Popen(trainscanner_cmd)

        # メモリーモニターを作成して監視開始
        monitor = create_memory_monitor_with_logger(log_file, interval)

        def print_memory_info(info):
            from trainscanner.memory_monitor import MemoryInfo

            print(
                f"[{time.strftime('%H:%M:%S')}] "
                f"RSS: {monitor.format_bytes(info.rss)}, "
                f"VMS: {monitor.format_bytes(info.vms)}, "
                f"システム: {info.percent:.1f}%"
            )

        # コンソール出力とログ出力を組み合わせ
        original_callback = monitor.callback

        def combined_callback(info):
            if original_callback:
                original_callback(info)
            print_memory_info(info)

        monitor.callback = combined_callback
        monitor.start_monitoring()

        # プロセスの終了を待機
        process.wait()

        # メモリー監視を停止
        monitor.stop_monitoring()

        print(f"\nTrainScannerが終了しました（終了コード: {process.returncode}）")
        print(f"メモリー使用量ログが保存されました: {log_file}")

    except KeyboardInterrupt:
        print("\n\nユーザーによって中断されました")
        if "process" in locals():
            process.terminate()
        if "monitor" in locals():
            monitor.stop_monitoring()
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        if "process" in locals():
            process.terminate()
        if "monitor" in locals():
            monitor.stop_monitoring()


def analyze_memory_log(log_file: str):
    """
    メモリー使用量ログファイルを分析して統計情報を表示する

    Args:
        log_file: 分析するログファイルのパス
    """
    try:
        import pandas as pd
        import numpy as np

        # CSVファイルを読み込み
        df = pd.read_csv(log_file)

        print(f"\n=== メモリー使用量分析結果: {log_file} ===")
        print(f"測定期間: {df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]:.1f}秒")
        print(f"測定回数: {len(df)}回")

        print(f"\n--- RSS（物理メモリー使用量）---")
        print(f"平均: {df['rss_mb'].mean():.1f} MB")
        print(f"最大: {df['rss_mb'].max():.1f} MB")
        print(f"最小: {df['rss_mb'].min():.1f} MB")
        print(f"標準偏差: {df['rss_mb'].std():.1f} MB")

        print(f"\n--- VMS（仮想メモリー使用量）---")
        print(f"平均: {df['vms_mb'].mean():.1f} MB")
        print(f"最大: {df['vms_mb'].max():.1f} MB")
        print(f"最小: {df['vms_mb'].min():.1f} MB")
        print(f"標準偏差: {df['vms_mb'].std():.1f} MB")

        print(f"\n--- システムメモリー使用率 ---")
        print(f"平均: {df['system_percent'].mean():.1f}%")
        print(f"最大: {df['system_percent'].max():.1f}%")
        print(f"最小: {df['system_percent'].min():.1f}%")

    except ImportError:
        print("詳細分析にはpandasが必要です。基本統計のみ表示します。")

        # pandasなしでの基本分析
        with open(log_file, "r") as f:
            lines = f.readlines()[1:]  # ヘッダーをスキップ

        rss_values = []
        vms_values = []
        system_percent_values = []

        for line in lines:
            parts = line.strip().split(",")
            if len(parts) >= 5:
                rss_values.append(float(parts[1]))
                vms_values.append(float(parts[2]))
                system_percent_values.append(float(parts[3]))

        if rss_values:
            print(f"\n=== メモリー使用量分析結果: {log_file} ===")
            print(f"測定回数: {len(rss_values)}回")

            print(f"\n--- RSS（物理メモリー使用量）---")
            print(f"平均: {sum(rss_values)/len(rss_values):.1f} MB")
            print(f"最大: {max(rss_values):.1f} MB")
            print(f"最小: {min(rss_values):.1f} MB")

            print(f"\n--- VMS（仮想メモリー使用量）---")
            print(f"平均: {sum(vms_values)/len(vms_values):.1f} MB")
            print(f"最大: {max(vms_values):.1f} MB")
            print(f"最小: {min(vms_values):.1f} MB")

            print(f"\n--- システムメモリー使用率 ---")
            print(f"平均: {sum(system_percent_values)/len(system_percent_values):.1f}%")
            print(f"最大: {max(system_percent_values):.1f}%")
            print(f"最小: {min(system_percent_values):.1f}%")
        else:
            print("ログファイルにデータが見つかりませんでした。")

    except FileNotFoundError:
        print(f"ログファイルが見つかりません: {log_file}")
    except Exception as e:
        print(f"ログファイルの分析中にエラーが発生しました: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="TrainScannerのメモリー使用量をプロファイリングします",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # TrainScannerをメモリー監視付きで実行
  python memory_profiler.py --run

  # 特定のファイルでTrainScannerを実行してメモリー監視
  python memory_profiler.py --run --trainscanner-args="sample.mov"

  # メモリーログファイルを分析
  python memory_profiler.py --analyze trainscanner_memory.csv

  # カスタム設定でメモリー監視
  python memory_profiler.py --run --log memory.csv --interval 0.5
        """,
    )

    parser.add_argument(
        "--run", action="store_true", help="TrainScannerを実行してメモリー使用量を監視"
    )
    parser.add_argument(
        "--analyze", metavar="LOG_FILE", help="メモリー使用量ログファイルを分析"
    )
    parser.add_argument(
        "--log",
        default="trainscanner_memory.csv",
        help="メモリー使用量ログファイルのパス（デフォルト: trainscanner_memory.csv）",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="メモリー監視間隔（秒、デフォルト: 1.0）",
    )
    parser.add_argument(
        "--trainscanner-args",
        default="",
        help="TrainScannerに渡す引数（スペース区切り）",
    )

    args = parser.parse_args()

    if args.run:
        # TrainScannerを実行してメモリー監視
        trainscanner_args = (
            args.trainscanner_args.split() if args.trainscanner_args else []
        )
        run_trainscanner_with_memory_monitoring(
            trainscanner_args, args.log, args.interval
        )
    elif args.analyze:
        # ログファイルを分析
        analyze_memory_log(args.analyze)
    else:
        # 引数が指定されていない場合はヘルプを表示
        parser.print_help()

        # 既存のメモリーログファイルがあれば一覧表示
        current_dir = Path(".")
        memory_logs = list(current_dir.glob("*memory*.csv"))
        if memory_logs:
            print(f"\n既存のメモリーログファイル:")
            for log_file in memory_logs:
                print(f"  {log_file}")
            print(f"\n分析するには: python {sys.argv[0]} --analyze <ログファイル>")


if __name__ == "__main__":
    main()
