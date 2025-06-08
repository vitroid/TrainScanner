![Banner](https://farm6.staticflickr.com/5763/30971813460_37996db7bb_o_d.jpg)

Version {{tool.poetry.version}}

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
{{ usage_helicify }}
```

### `rectify`: 長い画像を何段かに切りわけるツール

長い画像を、定型用紙に入るように「円筒に巻く」プログラムです。こちらは、画像がななめにならない代わり、円筒をのりづけする時にずらす必要があります。

```
rectify longimage.png
```

```
{{ usage_rectify }}
```

### `filmify`: 長い写真をフィルム風にするツール

長い写真の上下にフィルム風の穴を追加するだけのツールです。

```
filmify longimage.png
```

```
{{ usage_filmify }}
```

### `movify`: スクロール動画を生成するツール

スクロール動画を生成します。

```shell
movify longimage.png
```

```
{{ usage_movify }}
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

{% include "CHANGELOG.md" %}

## Memo/Reference

- [Python3 with OpenCV3](https://hackerslog.net/posts/softwares/opencv/opencv-install-with-python-on-mac/); downloading HEAD of openCV3 takes VERY long time.
- [Windows/Python3/OpenCV3/PyQt4/Anaconda](http://qiita.com/sugurunatsuno/items/ce3c0d486bdc93688192)
- [failed to build exe on Windows?](http://stackoverflow.com/questions/37815371/pyinstaller-failed-to-execute-script-pyi-rth-pkgres-and-missing-packages)
- Flickr account for TrainScanner development: [TrainScanner](https://www.flickr.com/photos/149573560@N03)
