# TrainScannerのMac用ディスクイメージ(.dmg)作成手順

以下はTrainScannerのMac用ディスクイメージ(`.dmg`)を作成する手順のメモです。macOS 15.5 Sequoia (Intel/Apple Silicon)とPython 3.12 (Homebrew版)で動作確認を行っています。

## TrainScannerのソースコードのダウンロード

[GitHub](https://github.com/vitroid/TrainScanner)からTrainScannerのソースコードをダウンロードします(`Code`ボタンを押して`Download ZIP`をクリックする)。ダウンロードしたZIPファイルは作業フォルダーに展開します。

Gitが使える場合は、以下のコマンドでTrainScannerのソースコードをクローンできます。

```bash
git clone https://github.com/vitroid/TrainScanner.git
```

## Pythonの仮想環境の構築

ターミナルアプリを開いて、TrainScannerのソースコードのあるフォルダーで以下のようにコマンドを入力します。

```bash
python3 -m venv venv
. venv/bin/activate
```

続いて以下のコマンドを実行すると、Pythonの仮想環境の中にTrainScannerがインストールされます。

```bash
pip install .
```

## cx_Freezeのインストールとmsiのビルド

[cx_Freeze](https://cx-freeze.readthedocs.io/en/stable/)をインストールします。

```powershell
pip install cx_Freeze~=8.3
```

Pythonの仮想環境にTrainScannerのインストールが済んでいれば、TrainScannerの`mac`フォルダーに移動してインストーラを作成するコマンドを実行します。

```mac
cd ./mac
python setup.py bdist_dmg
```

`mac`フォルダーの中に`build`フォルダーが作成され、ファイル拡張子が`.dmg`のMac用ディスクイメージが保存されます。

Finderでディスクイメージファイルを開くと、TrainScannerのアプリアイコンとアプリケーションフォルダへのエイリアスが表示されるので、アプリアイコンをアプリケーションフォルダにコピーします。

## 補足

cx_Freezeの現在の実装では、ビルドしたアプリの言語が`English`固定になってしまうため、TrainScannerアプリを日本語化するためにはアプリの`Info.plist`を修正する必要があります。

```bash
nano /Applications/TrainScanner.app/Contents/Info.plist
```

テキストエディタで`Info.plist`を開いたら、以下の2行を削除して上書き保存します。

```Info.plist
        <key>CFBundleDevelopmentRegion</key>
        <string>English</string>
```
