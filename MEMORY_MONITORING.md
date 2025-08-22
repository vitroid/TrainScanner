# TrainScanner メモリー使用量監視機能

TrainScanner にメモリー使用量を監視する機能が追加されました。この機能により、アプリケーションの実行中にメモリー使用量をリアルタイムで確認し、ログファイルに記録することができます。

## 機能概要

### 1. リアルタイムメモリー表示

- メイン GUI にメモリー使用量がリアルタイムで表示されます
- RSS（物理メモリー）、VMS（仮想メモリー）、システム使用率を表示

### 2. メモリー使用量ログ記録

- メモリー使用量を CSV ファイルに記録
- 後で分析可能な形式で保存

### 3. コマンドライン監視ツール

- 独立したメモリー監視スクリプト
- 詳細な分析機能付き

## 使用方法

### 基本的な使用方法

1. **GUI でのリアルタイム監視**

   ```bash
   trainscanner
   ```

   メインウィンドウの下部にメモリー使用量が表示されます。

2. **コマンドラインでのメモリー監視**

   ```bash
   # 基本的なメモリー監視
   python memory_profiler.py --run

   # ログファイルを指定してメモリー監視
   python memory_profiler.py --run --log my_memory_log.csv

   # 監視間隔を指定（0.5秒間隔）
   python memory_profiler.py --run --interval 0.5
   ```

3. **メモリー使用量ログの分析**

   ```bash
   # ログファイルを分析
   python memory_profiler.py --analyze trainscanner_memory.csv
   ```

4. **独立したメモリー監視**
   ```bash
   # メモリー監視のみ実行（60秒間）
   memory_monitor --duration 60 --log memory_test.csv
   ```

### 高度な使用方法

#### メモリー使用量の詳細分析

メモリーログファイル（CSV 形式）には以下の情報が記録されます：

- `timestamp`: 測定時刻
- `rss_mb`: RSS（物理メモリー使用量）[MB]
- `vms_mb`: VMS（仮想メモリー使用量）[MB]
- `system_percent`: システム全体のメモリー使用率[%]
- `available_mb`: 利用可能メモリー[MB]

#### プログラム内でのメモリー監視

```python
from trainscanner.memory_monitor import MemoryMonitor, MemoryInfo

def my_memory_callback(info: MemoryInfo):
    print(f"RSS: {info.rss / 1024 / 1024:.1f} MB")

# メモリー監視を開始
monitor = MemoryMonitor(interval=1.0, callback=my_memory_callback)
monitor.start_monitoring()

# 処理を実行...

# 監視を停止
monitor.stop_monitoring()
```

## メモリー使用量の最適化のヒント

### 1. 大きなメモリー使用量の原因

- 大きな画像データの読み込み
- フレームバッファーの蓄積
- OpenCV の画像処理バッファー

### 2. 最適化の提案

- フレーム数の制限（`max_frames`パラメータ）
- 画像サイズの縮小
- 不要なフレームの削除（ガベージコレクション）

### 3. 監視すべき指標

- **RSS**: 実際に使用している物理メモリー
- **VMS**: プロセスが確保している仮想メモリー
- **システム使用率**: 全体的なメモリー圧迫状況

## トラブルシューティング

### メモリー不足エラーが発生する場合

1. メモリー使用量ログを確認
2. ピークメモリー使用量を特定
3. 設定パラメータを調整（フレーム数制限など）

### メモリー監視が動作しない場合

1. `psutil`パッケージがインストールされているか確認
2. 権限の問題がないか確認
3. ログファイルの書き込み権限を確認

## 依存関係

- `psutil >= 5.9.0`: プロセスとシステムの情報取得
- `PyQt5`: GUI 統合（オプション）
- `pandas`: ログ分析の詳細統計（オプション）

## ライセンス

このメモリー監視機能は TrainScanner の MIT ライセンスの下で提供されます。
