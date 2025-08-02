#!/usr/bin/env python3
"""
連番画像ファイルの番号を逆順に変更するスクリプト

使用方法:
python reverse_image_sequence.py <フォルダーパス>

例: python reverse_image_sequence.py ./images/
"""

import os
import sys
import re
import glob
from pathlib import Path


def reverse_image_sequence(folder_path):
    """
    指定フォルダー内の連番画像ファイル（000000.png形式）の番号を逆順に変更

    Args:
        folder_path (str): 画像ファイルが含まれるフォルダーのパス
    """

    # フォルダーパスの確認
    folder = Path(folder_path)
    if not folder.exists():
        print(f"エラー: フォルダー '{folder_path}' が見つかりません")
        return False

    if not folder.is_dir():
        print(f"エラー: '{folder_path}' はフォルダーではありません")
        return False

    # 連番画像ファイルを検索（6桁の数字.png形式）
    pattern = os.path.join(folder_path, "[0-9][0-9][0-9][0-9][0-9][0-9].png")
    image_files = glob.glob(pattern)

    if not image_files:
        print(
            f"警告: フォルダー '{folder_path}' に連番画像ファイル（000000.png形式）が見つかりません"
        )
        return False

    # ファイル名から番号を抽出してソート
    file_info = []
    for file_path in image_files:
        filename = os.path.basename(file_path)
        # 6桁の数字部分を抽出
        match = re.match(r"(\d{6})\.png$", filename)
        if match:
            number = int(match.group(1))
            file_info.append((file_path, number, filename))

    # 番号順にソート
    file_info.sort(key=lambda x: x[1])

    print(f"検出されたファイル数: {len(file_info)}")
    print(f"番号範囲: {file_info[0][1]:06d} ～ {file_info[-1][1]:06d}")

    # 確認プロンプト
    response = input("ファイル名を逆順に変更しますか？ (y/N): ")
    if response.lower() not in ["y", "yes"]:
        print("キャンセルされました")
        return False

    try:
        # ステップ1: 一時的な名前に変更（重複を避けるため）
        print("ステップ1: ファイルを一時的な名前に変更中...")
        temp_files = []
        for i, (file_path, original_number, original_filename) in enumerate(file_info):
            temp_name = f"temp_{i:06d}.png"
            temp_path = os.path.join(folder, temp_name)
            os.rename(file_path, temp_path)
            temp_files.append((temp_path, original_number, original_filename))
            print(f"  {original_filename} → {temp_name}")

        # ステップ2: 逆順の番号で最終的な名前に変更
        print("ステップ2: 逆順の番号でファイル名を変更中...")
        max_number = file_info[-1][1]  # 最大の番号
        min_number = file_info[0][1]  # 最小の番号

        for i, (temp_path, original_number, original_filename) in enumerate(temp_files):
            # 逆順の番号を計算
            new_number = max_number - (original_number - min_number)
            new_filename = f"{new_number:06d}.png"
            new_path = os.path.join(folder, new_filename)

            os.rename(temp_path, new_path)
            print(f"  {original_filename} → {new_filename}")

        print("✅ 完了: 全てのファイルの番号が逆順に変更されました")
        return True

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        print("一部のファイルが一時的な名前のままの可能性があります")
        return False


def main():
    """メイン関数"""
    if len(sys.argv) != 2:
        print("使用方法: python reverse_image_sequence.py <フォルダーパス>")
        print("例: python reverse_image_sequence.py ./images/")
        sys.exit(1)

    folder_path = sys.argv[1]
    success = reverse_image_sequence(folder_path)

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
