#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
tsposファイルをコマンドラインでプロットするツール
"""

import sys
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')  # GUIなしのバックエンド
import matplotlib.pyplot as plt
from logging import getLogger


def plot_tspos(
    tspos_file: str,
    output_file: str = None,
    show_cumsum: bool = True,
    show_dx: bool = True,
    show_dy: bool = True,
    frame_interval: int = 1,
    time_axis: bool = False
):
    """
    tsposファイルをプロットする
    
    Args:
        tspos_file: tsposファイルのパス
        output_file: 出力画像ファイルのパス（Noneの場合は自動生成）
        show_cumsum: 累積変位を表示するかどうか
        show_dx: X方向変位を表示するかどうか
        show_dy: Y方向変位を表示するかどうか
        frame_interval: フレーム間隔（間引き）
        time_axis: X軸を時間で表示するかどうか
    """
    
    # データを読み込み
    try:
        data = np.loadtxt(tspos_file)
        if data.shape[1] < 3:
            raise ValueError("tsposファイルには最低3列のデータが必要です")
    except Exception as e:
        print(f"エラー: ファイルの読み込みに失敗しました: {e}")
        return False
    
    # フレーム間隔による間引き
    if frame_interval > 1:
        indices = np.arange(0, len(data), frame_interval)
        data = data[indices]
    
    # X軸データの準備
    if time_axis:
        x_data = data[:, 0] / 30.0  # 時間（30fpsと仮定）
        x_label = "時間 (秒)"
    else:
        x_data = data[:, 0]  # フレーム番号
        x_label = "フレーム番号"
    
    # プロットの作成
    plt.style.use('default')
    
    if show_cumsum:
        # 累積変位をプロット
        fig, ax = plt.subplots(figsize=(12, 8))
        
        if show_dx:
            cumsum_x = np.cumsum(data[:, 1])
            ax.plot(x_data, cumsum_x, 'b-', label='X方向累積変位', linewidth=2)
            
        if show_dy:
            cumsum_y = np.cumsum(data[:, 2])
            ax.plot(x_data, cumsum_y, 'r-', label='Y方向累積変位', linewidth=2)
            
        ax.set_ylabel('累積変位 (ピクセル)')
        ax.set_title('tspos累積変位プロット')
        
    else:
        # フレーム間変位をプロット
        if show_dx and show_dy:
            # 2つのサブプロット
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            
            ax1.plot(x_data, data[:, 1], 'b-', linewidth=1)
            ax1.set_ylabel('X方向変位 (ピクセル)')
            ax1.set_title('tspos変位プロット')
            ax1.grid(True, alpha=0.3)
            
            ax2.plot(x_data, data[:, 2], 'r-', linewidth=1)
            ax2.set_ylabel('Y方向変位 (ピクセル)')
            ax2.set_xlabel(x_label)
            ax2.grid(True, alpha=0.3)
            
        else:
            # 1つのプロット
            fig, ax = plt.subplots(figsize=(12, 8))
            
            if show_dx:
                ax.plot(x_data, data[:, 1], 'b-', label='X方向変位', linewidth=2)
                
            if show_dy:
                ax.plot(x_data, data[:, 2], 'r-', label='Y方向変位', linewidth=2)
                
            ax.set_ylabel('変位 (ピクセル)')
            ax.set_title('tspos変位プロット')
    
    # 共通の設定
    if 'ax' in locals():
        ax.set_xlabel(x_label)
        ax.grid(True, alpha=0.3)
        if len(ax.get_legend_handles_labels()[0]) > 0:
            ax.legend()
    
    plt.tight_layout()
    
    # 出力ファイル名の決定
    if output_file is None:
        base_name = Path(tspos_file).stem
        output_file = f"{base_name}_plot.png"
    
    # 保存
    try:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"プロットを保存しました: {output_file}")
        
        # 統計情報を表示
        frame_count = len(data)
        dx_total = np.sum(np.abs(data[:, 1]))
        dy_total = np.sum(np.abs(data[:, 2]))
        
        print(f"\n統計情報:")
        print(f"  フレーム数: {frame_count}")
        print(f"  X変位合計: {dx_total:.1f}px")
        print(f"  Y変位合計: {dy_total:.1f}px")
        
        return True
        
    except Exception as e:
        print(f"エラー: 保存に失敗しました: {e}")
        return False
    
    finally:
        plt.close()


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="tsposファイルをプロットします",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 基本的なプロット
  tspos_plot sample.mov.12345.tspos

  # 出力ファイル名を指定
  tspos_plot sample.mov.12345.tspos -o my_plot.png

  # フレーム間変位のみ表示
  tspos_plot sample.mov.12345.tspos --no-cumsum

  # X方向変位のみ表示
  tspos_plot sample.mov.12345.tspos --no-dy

  # 時間軸で表示
  tspos_plot sample.mov.12345.tspos --time

  # フレーム間隔を指定
  tspos_plot sample.mov.12345.tspos --interval 5
        """
    )
    
    parser.add_argument("tspos_file", help="tsposファイルのパス")
    parser.add_argument("-o", "--output", help="出力画像ファイルのパス")
    parser.add_argument("--no-cumsum", action="store_true", help="累積変位を表示しない")
    parser.add_argument("--no-dx", action="store_true", help="X方向変位を表示しない")
    parser.add_argument("--no-dy", action="store_true", help="Y方向変位を表示しない")
    parser.add_argument("--time", action="store_true", help="X軸を時間で表示")
    parser.add_argument("--interval", type=int, default=1, help="フレーム間隔（間引き）")
    
    args = parser.parse_args()
    
    if not Path(args.tspos_file).exists():
        print(f"エラー: ファイルが見つかりません: {args.tspos_file}")
        sys.exit(1)
    
    success = plot_tspos(
        tspos_file=args.tspos_file,
        output_file=args.output,
        show_cumsum=not args.no_cumsum,
        show_dx=not args.no_dx,
        show_dy=not args.no_dy,
        frame_interval=args.interval,
        time_axis=args.time
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

