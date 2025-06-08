![Banner](https://farm6.staticflickr.com/5763/30971813460_37996db7bb_o_d.jpg)

Version 0.25.0

# TrainScanner の使い方

## インストール

Terminal から以下のコマンドでインストール・起動して下さい。

```shell
pip install trainscanner
trainscanner
```

開発中の版を試してみたい場合はこちら。

```
pip install git+https://github.com/vitroid/TrainScanner.git
```

## ドキュメント

[Wiki](https://github.com/vitroid/TrainScanner/wiki)

## 前処理: 手ぶれ補正

手持ち撮影でもきれいにつながるように、`trainscanner`で列車をつなぐ前に、手ぶれをとりのぞくツールです。

```shell
antishake
```

ムービーが画像ファイルに展開されるので、それなりのディスク容量が必要です。生成した画像ファイルの束は、ディレクトリごと`trainscanner`で読みこめます。

## 後処理: 各種コンバータ

TrainScanner で作成した画像は巨大でしかも長大なので、そのままでは取り扱いにくいため、見易いようにいろんな変換プログラムを準備しました。

```shell
ts_converter
```

これは、次節のコマンドに GUI を付与したものです。

## コマンドラインからの利用

### `helicify`: 長い画像をらせんにするツール

長い画像を、定型用紙に入るように「円筒に巻く」プログラムです。

```
helicify longimage.png
```

```
usage: helix.py [-h] [--output OUTPUT] [--aspect ASPECT] [--width WIDTH]
                image_path

らせん画像を作る

positional arguments:
  image_path            入力ファイルのパス

options:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        出力ファイルのパス
  --aspect ASPECT, -a ASPECT
                        アスペクト比-- 0.1,10
  --width WIDTH, -W WIDTH
                        画像の幅 (ピクセル, 変更しないなら0)-- 0,10000

```

### `rectify`: 長い画像を何段かに切りわけるツール

長い画像を、定型用紙に入るように「円筒に巻く」プログラムです。こちらは、画像がななめにならない代わり、円筒をのりづけする時にずらす必要があります。

```
rectify longimage.png
```

```
usage: rect.py [-h] [--output OUTPUT] [--aspect ASPECT] [--overlap OVERLAP]
               [--head-right] [--thumbnail] [--width WIDTH]
               image_path

ぶつ切り山積み

positional arguments:
  image_path            入力ファイルのパス

options:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        出力ファイルのパス
  --aspect ASPECT, -a ASPECT
                        アスペクト比-- 0.1,10
  --overlap OVERLAP, -l OVERLAP
                        端の重複部分の幅 (パーセント)-- 0,100
  --head-right, -R      列車は右向きに進む
  --thumbnail, -t       Add a thumbnail image (Hans Ruijter's style)
  --width WIDTH, -W WIDTH
                        画像の幅 (ピクセル, 変更しないなら0)-- 0,10000

```

### `filmify`: 長い写真をフィルム風にするツール

長い写真の上下にフィルム風の穴を追加するだけのツールです。

```
filmify longimage.png
```

```
usage: film.py [-h] [--output OUTPUT]
               [--creative_commons_sign CREATIVE_COMMONS_SIGN]
               image_path

Add film perforations to the image

positional arguments:
  image_path            入力画像ファイルのパス

options:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        出力ファイルのパス
  --creative_commons_sign CREATIVE_COMMONS_SIGN, -c CREATIVE_COMMONS_SIGN
                        Creative Commons sign

```

### `movify`: スクロール動画を生成するツール

スクロール動画を生成します。

```shell
movify longimage.png
```

```
usage: movie.py [-h] [--output OUTPUT] [--duration DURATION] [--height HEIGHT]
                [--width WIDTH] [--head-right] [--fps FPS] [--crf CRF] [--png]
                [--alternating] [--accel] [--encoder ENCODER] [--thumbnail]
                image_path

列車の長い写真からムービーを作る

positional arguments:
  image_path            入力ファイルのパス

options:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        出力ファイルのパス
  --duration DURATION, -d DURATION
                        ムービーの尺 (秒)-- 10,1000
  --height HEIGHT, -H HEIGHT
                        ムービーの高さ (pixels)-- 100,4096
  --width WIDTH, -W WIDTH
                        ムービーの幅 (pixels)-- 100,4096
  --head-right, -R      列車は右向きに進む
  --fps FPS, -r FPS     フレームレート (fps)-- 1,120
  --crf CRF, -c CRF     CRF (Constant Rate Factor) -- 16,30
  --png, -p             高画質な中間ファイル
  --alternating, -a     行ったり来たり
  --accel, -A           加速
  --encoder ENCODER, -e ENCODER
                        mp4エンコーダ
  --thumbnail, -t       Add a thumbnail (Yamako style)

```

<!-- ### `shakereduction.py`: 手振れ補正 (試験中)

TrainScanner とおなじしくみを使って，ビデオの手振れを除くツールです．列車の場所ではなく，背景の一区画を`--focus`オプションで選ぶと，その部分が動かなくなるように，各コマを縦横にずらしたしたムービーを作成します．

```
./shakereduction.py -f L R T B -S skipframes filename.mov
```

今のところコマンドラインでの利用のみです．手振れだけでなく，たとえば柱に固定して撮影したけど，列車の振動でけっこう柱が揺れた場合(この場合，けっこう大きな加速度が加わるので，手振れよりも実は修正が大変です)にも使えます．

TrainScanner は基本的に三脚での撮影を前提としています．`shakereduction.py`を使っても，水平が傾いたりする場合までは対応できません． -->

### _2020-7-15 最近確認していません。動くかどうか保証できません_

`TrainScanner.app`は、`pass1.py`と`stitch.py`という 2 つのプログラムを呼びだすためのラッパーで、これらのプログラムは単独でも動作します。列車の移動量の検出がうまくいかなかった場合など、手直ししたい場合には、`tsconf`ファイルと`tspos`ファイルを手で修正して、より良い結果を得ることもできます。

それぞれのコマンドには多数のオプションがあります。`-h`オプションを付けて、使い方を見て下さい。ほとんどのオプションは`trainscanner_gui.py` (アプリケーション名は`TrainScanner.app`, `TrainScanner.exe`)上で指定できますので、グラフィック表示ができる環境であれば、GUI を使うことをお勧めします。ただし、`tsconf`ファイルと`tspos`ファイルを手で修正した場合は`stitch.py`を使いたくなるかもしれません。

### `trainscanner_pass1`: 照合プログラム

ビデオを読みこみ、列車の移動を検出し、移動量を`.tspos`という名前のファイルに出力します。

```
trainscanner_pass1 video.mov
```

### `trainscanner_stitch`: 結合プログラム

pass1.py の出力に従い、映像を連結して 1 枚の大きな写真を作ります。通常は、以下のように、pass1.py が出力した`.tsconf`ファイルを読みこんで使用します。

```
trainscanner_stitch @video.mov.12345.tsconf
```

`@`マークは、コマンドラインオプションをファイルからインクルードすることを意味します。この後ろに、さらにオプションを追加することで、スリット位置やフレーム間のぼかし幅を調節できます。例えば、あとからスリット位置と幅をそれぞれ 220 と 1.5 に変えたい場合は、

```
trainscanner_stitch @video.mov.12345.tsconf -s 220 -w 1.5
```

のようにします。GUI を使う場合には、設定を変える度に pass1.py も実行せざるをえませんが、stitch.py を直接使えば、よりすばやく結果を得られます。

### `trainscanner`: 統合ユーザーインターフェイス

`trainscanner_pass1`と`trainscanner_stitch`を統合し、オプションを対話的に設定できる UI を備えた TrainScanner の本体です。Windows の exe ファイルや macOS の App はこれをパッケージ化したものです。

<!-- ## Raspberry PI での使用

カメラの解像度を低めにすれば、RPi の処理能力でもかなりの速度で処理できるはずです。ただし、メモリ不足が深刻でしょうね。TrainScanner の処理のなかで一番メモリを必要とするのは、`stitch.py`の行っている、一枚の大きな写真を作るプロセスです。原理的に、大きな画像全体を非圧縮のまま一旦メモリに入れない限り、その大きさの写真が作れないからです。この問題を回避するために、小さな写真の断片でおおきな写真を表現する画像フォーマット[tiledimage](https://github.com/vitroid/tiledimage)を製作しました。 -->

## Revision History

# 変更履歴

## [0.16.1] - 2025-05-12

### 追加

- movify および movify2 のエントリを追加

## [0.16.0] - 2025-05-12

### 追加

- GUI に新しいラジオボタンを追加
- 横スクロール動画の生成機能を強化
- 画像処理のオプションに右端を先頭にする機能を追加
- 進捗バーの更新を改善
- ffmpeg の存在確認に基づいてボタンの有効/無効を制御するロジックを調整

## [0.15.0] - 2025-05-09

### 変更

- converter のパスを ts_conv から trainscanner.converter に変更
- 動画生成機能の高さ調整ロジックを改善

## [0.14.3] - 2025-05-08

### 変更

- Python の依存関係を 3.11 に変更
- ホームページの URL を追加

## [0.14.2] - 2025-05-08

### 変更

- Python の依存関係を 3.10 に変更
- Linux 環境でのビデオモジュールのインポートを修正

## [0.14.1] - 2025-05-08

### 追加

- scikit-video パッケージを追加

### 修正

- qrangeslider.py でのイベント処理において、座標を整数に変換する修正

## [0.13.2] - 2023-01-09

### 修正

- tsconf ファイルを開くときに発生するエラーを修正
- Apple M1 対応の改善

## [0.13] - 2023-01-04

### 変更

- PyQt6 への移行

## [0.12.0] - 2020-07-15

### 修正

- パスに空白が含まれる場合のバグを修正

### 変更

- コマンドラインオプションの更新

## [0.10] - 2017-04-13

### 追加

- Hansify コマンドを追加

## [0.7.3] - 2016-12-29

### 追加

- QRangeSlider の実装

### 修正

- 後半の thumbnail が無視される問題を解決

## [0.5.1] - 2016-11-27

### 変更

- スライダーの高さを変更

## [0.5.0] - 2016-11-25

### 追加

- 矩形フォーマットの導入

### 変更

- Python3 へのアップグレード
- Windows 対応の改善

## [0.4.0] - 2016-11-20

### 追加

- tsconf ファイルから設定を継承する機能

### 変更

- ジェネレーターの簡略化

## [0.3.0] - 2016-11-13

### 追加

- アルファ版リリース

### 変更

- チュートリアルの更新

## [0.2.0] - 2016-10-16

### 追加

- モーション検出エリア（フォーカスエリア）の指定機能
- スクロールバー付き GUI プロトタイプ
- 上下のクロップ機能

## [0.1.0] - 2016-08-31

### 追加

- Python2+OpenCV2 による完全な書き直し

## Memo/Reference

- [Python3 with OpenCV3](https://hackerslog.net/posts/softwares/opencv/opencv-install-with-python-on-mac/); downloading HEAD of openCV3 takes VERY long time.
- [Windows/Python3/OpenCV3/PyQt4/Anaconda](http://qiita.com/sugurunatsuno/items/ce3c0d486bdc93688192)
- [failed to build exe on Windows?](http://stackoverflow.com/questions/37815371/pyinstaller-failed-to-execute-script-pyi-rth-pkgres-and-missing-packages)
- Flickr account for TrainScanner development: [TrainScanner](https://www.flickr.com/photos/149573560@N03)
