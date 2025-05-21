# TrainScannerのWindowsインストーラ作成手順

以下はTrainScannerのWindowsインストーラ(`msi`形式)を作成する手順のメモです。Windows11 64bit版で動作確認を行っています。

## Python for Windowsのインストール

[Pythonの公式サイト](https://www.python.org/downloads/)からWindows用のPythonインストーラ(`python-3.xx.xx-amd64.exe`)をダウンロードしてインストールしてください。

## TrainScannerのソースコードのダウンロード

[GitHub](https://github.com/vitroid/TrainScanner)からTrainScannerのソースコードをダウンロードします(`Code`ボタンを押して`Download ZIP`をクリックする)。ダウンロードしたZIPファイルは作業フォルダーに展開します。

[Git for Windows](https://gitforwindows.org/)が使える場合は、以下のコマンドでTrainScannerのソースコードをクローンできます。

```powershell
git clone https://github.com/vitroid/TrainScanner.git
```

## Pythonの仮想環境の構築

WindowsのターミナルアプリでPowerShellを開いて、TrainScannerのソースコードのあるフォルダーで以下のようにコマンドを入力します。

```powershell
py.exe -m venv venv
venv\Scripts\Activate.ps1
```

PowerShellのプロンプト先頭に`(venv)`が表示されて、`python`コマンドや`pip`コマンドが使えるようになります。

TrainScannerのソースコードのあるフォルダーで以下のコマンドを実行すると、Pythonの仮想環境の中にTrainScannerがインストールされます。

```powershell
pip install .
```

## cx_Freezeのインストールとmsiのビルド

[cx_Freeze](https://cx-freeze.readthedocs.io/en/stable/)をインストールします。

```powershell
pip install cx_Freeze~=8.3
```

Pythonの仮想環境にTrainScannerのインストールが済んでいれば、TrainScannerの`win`フォルダーに移動してインストーラを作成するコマンドを実行します。

```powershell
cd .\win
python setup.py bdist_msi
```

`win`フォルダーの中に`build`フォルダーと`dist`フォルダーが作成され、`dist`フォルダーの中にファイル拡張子が`.msi`のWindowsインストーラーパッケージが保存されます。

Windowsのエクスプローラーで`dist`フォルダーを開き、Windowsインストーラーパッケージを開いてTrainScannerをインストールします。インストール後はWindowsのスタートメニューに`TrainScanner`が出来ます。
