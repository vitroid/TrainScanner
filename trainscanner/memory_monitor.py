#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TrainScannerのメモリー使用量を監視するためのモジュール
"""

import os
import psutil
import time
import threading
from typing import Optional, Callable
from dataclasses import dataclass
from logging import getLogger


@dataclass
class MemoryInfo:
    """メモリー使用量の情報を格納するデータクラス"""

    rss: int  # Resident Set Size (物理メモリー使用量) in bytes
    vms: int  # Virtual Memory Size (仮想メモリー使用量) in bytes
    percent: float  # システム全体のメモリー使用率
    available: int  # 利用可能メモリー in bytes
    timestamp: float  # 測定時刻


class MemoryMonitor:
    """メモリー使用量を監視するクラス"""

    def __init__(
        self,
        interval: float = 1.0,
        callback: Optional[Callable[[MemoryInfo], None]] = None,
    ):
        """
        Args:
            interval: 監視間隔（秒）
            callback: メモリー情報更新時に呼び出されるコールバック関数
        """
        self.interval = interval
        self.callback = callback
        self.process = psutil.Process(os.getpid())
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.logger = getLogger(__name__)
        self._last_memory_info: Optional[MemoryInfo] = None

    def get_current_memory_info(self) -> MemoryInfo:
        """現在のメモリー使用量を取得"""
        try:
            # プロセス固有のメモリー情報
            memory_info = self.process.memory_info()

            # システム全体のメモリー情報
            system_memory = psutil.virtual_memory()

            info = MemoryInfo(
                rss=memory_info.rss,
                vms=memory_info.vms,
                percent=system_memory.percent,
                available=system_memory.available,
                timestamp=time.time(),
            )

            self._last_memory_info = info
            return info

        except Exception as e:
            self.logger.error(f"メモリー情報の取得に失敗しました: {e}")
            # デフォルト値を返す
            return MemoryInfo(0, 0, 0.0, 0, time.time())

    def format_bytes(self, bytes_value: int) -> str:
        """バイト数を人間が読みやすい形式に変換"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"

    def get_memory_summary(self) -> str:
        """メモリー使用量のサマリーを文字列で取得"""
        info = self.get_current_memory_info()
        return (
            f"RSS: {self.format_bytes(info.rss)}, "
            f"VMS: {self.format_bytes(info.vms)}, "
            f"システム使用率: {info.percent:.1f}%, "
            f"利用可能: {self.format_bytes(info.available)}"
        )

    def start_monitoring(self):
        """メモリー監視を開始"""
        if self.is_monitoring:
            self.logger.warning("メモリー監視は既に開始されています")
            return

        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info(f"メモリー監視を開始しました（間隔: {self.interval}秒）")

    def stop_monitoring(self):
        """メモリー監視を停止"""
        if not self.is_monitoring:
            self.logger.warning("メモリー監視は開始されていません")
            return

        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=self.interval + 1.0)
        self.logger.info("メモリー監視を停止しました")

    def _monitor_loop(self):
        """メモリー監視のメインループ"""
        while self.is_monitoring:
            try:
                info = self.get_current_memory_info()
                if self.callback:
                    self.callback(info)
                time.sleep(self.interval)
            except Exception as e:
                self.logger.error(f"メモリー監視中にエラーが発生しました: {e}")
                break

    @property
    def last_memory_info(self) -> Optional[MemoryInfo]:
        """最後に取得したメモリー情報を返す"""
        return self._last_memory_info


class MemoryLogger:
    """メモリー使用量をログファイルに記録するクラス"""

    def __init__(self, log_file: str):
        self.log_file = log_file
        self.logger = getLogger(__name__)

        # ログファイルのヘッダーを書き込み
        try:
            with open(self.log_file, "w") as f:
                f.write("timestamp,rss_mb,vms_mb,system_percent,available_mb\n")
        except Exception as e:
            self.logger.error(f"ログファイルの初期化に失敗しました: {e}")

    def log_memory_info(self, info: MemoryInfo):
        """メモリー情報をログファイルに記録"""
        try:
            with open(self.log_file, "a") as f:
                f.write(
                    f"{info.timestamp:.3f},"
                    f"{info.rss / 1024 / 1024:.2f},"
                    f"{info.vms / 1024 / 1024:.2f},"
                    f"{info.percent:.2f},"
                    f"{info.available / 1024 / 1024:.2f}\n"
                )
        except Exception as e:
            self.logger.error(f"メモリー情報のログ記録に失敗しました: {e}")


def create_memory_monitor_with_logger(
    log_file: str, interval: float = 1.0
) -> MemoryMonitor:
    """ログ機能付きのメモリーモニターを作成"""
    logger = MemoryLogger(log_file)
    monitor = MemoryMonitor(interval=interval, callback=logger.log_memory_info)
    return monitor


# 使用例とテスト用の関数
def main():
    """メモリーモニターのテスト用メイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="TrainScanner メモリーモニター")
    parser.add_argument("--log", help="ログファイルのパス", default="memory_usage.csv")
    parser.add_argument("--interval", type=float, help="監視間隔（秒）", default=1.0)
    parser.add_argument("--duration", type=float, help="監視時間（秒）", default=60.0)

    args = parser.parse_args()

    def print_memory_info(info: MemoryInfo):
        print(
            f"RSS: {info.rss / 1024 / 1024:.1f} MB, "
            f"VMS: {info.vms / 1024 / 1024:.1f} MB, "
            f"システム: {info.percent:.1f}%"
        )

    # ログ機能付きモニターを作成
    monitor = create_memory_monitor_with_logger(args.log, args.interval)

    # コンソール出力も追加
    original_callback = monitor.callback

    def combined_callback(info: MemoryInfo):
        if original_callback:
            original_callback(info)
        print_memory_info(info)

    monitor.callback = combined_callback

    print(f"メモリー監視を開始します（{args.duration}秒間）")
    monitor.start_monitoring()

    try:
        time.sleep(args.duration)
    except KeyboardInterrupt:
        print("\nユーザーによって中断されました")

    monitor.stop_monitoring()
    print(f"ログファイル: {args.log}")


if __name__ == "__main__":
    main()
