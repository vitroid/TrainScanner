## [] - 2025-08-02

### 変更

- 9f1402c 逆順動画作成
- 588497c 差分表現の改良
- 27a8c46 subpixel対応
- eb4bd1e PyQt5対応
- 10dc8c7 旧MacOSとの互換性のため、PyQt5に戻す。
- 93d238c Refactor subpixel matching and motion detection logic to support variable fit widths and improve accuracy. Updated `subpixel_match` to use CCOEFF method and adjusted handling of maximum acceleration in `motion` function. Enhanced parameter handling for improved flexibility in image processing.

### 追加

### 修正

## [] - 2025-08-02

### 変更

- 588497c 差分表現の改良
- 27a8c46 subpixel対応
- eb4bd1e PyQt5対応
- 10dc8c7 旧MacOSとの互換性のため、PyQt5に戻す。
- 93d238c Refactor subpixel matching and motion detection logic to support variable fit widths and improve accuracy. Updated `subpixel_match` to use CCOEFF method and adjusted handling of maximum acceleration in `motion` function. Enhanced parameter handling for improved flexibility in image processing.

### 追加

### 修正

## [] - 2025-08-02

### 変更

- 27a8c46 subpixel対応
- eb4bd1e PyQt5対応
- 10dc8c7 旧MacOSとの互換性のため、PyQt5に戻す。
- 93d238c Refactor subpixel matching and motion detection logic to support variable fit widths and improve accuracy. Updated `subpixel_match` to use CCOEFF method and adjusted handling of maximum acceleration in `motion` function. Enhanced parameter handling for improved flexibility in image processing.

### 追加

### 修正

## [] - 2025-08-02

### 変更

- eb4bd1e PyQt5対応
- 10dc8c7 旧MacOSとの互換性のため、PyQt5に戻す。
- 93d238c Refactor subpixel matching and motion detection logic to support variable fit widths and improve accuracy. Updated `subpixel_match` to use CCOEFF method and adjusted handling of maximum acceleration in `motion` function. Enhanced parameter handling for improved flexibility in image processing.

### 追加

### 修正

## [] - 2025-08-02

### 変更

- 10dc8c7 旧MacOSとの互換性のため、PyQt5に戻す。
- 93d238c Refactor subpixel matching and motion detection logic to support variable fit widths and improve accuracy. Updated `subpixel_match` to use CCOEFF method and adjusted handling of maximum acceleration in `motion` function. Enhanced parameter handling for improved flexibility in image processing.

### 追加

### 修正

## [0.29.3] - 2025-06-24

### 修正

- a7adc6b CHANGELOG.md の自動更新機能を削除し、手動でのコミットを推奨するように変更しました。

## [0.29.0] - 2025-01-XX

### 追加

- サブピクセルマッチング処理の fit_width パラメータを追加
- オプションのヘルプテキストのフォーマットを改善
- 範囲指定をカンマからコロンに修正
- オプションの値の範囲を取得するロジックを改善
- spec を使用して値の選択肢を提供する機能を追加

### 変更

- motion 関数のサブピクセルマッチング処理を改善
- maxaccel が 1 の場合の値変更ロジックを実装
- Pass1 クラスの動作判定ロジックを改善
- coldstart 状態での動きの受け入れ処理を追加
- guess_mode を in_action に置き換え
- 動きが antishake 水準を超えた際の処理を整理
- サブピクセル処理が失敗しても破綻しないように調整
- Stitcher クラス内の tspos ファイルの読み込み処理で列のデータ型を整数から浮動小数点数に変更
- shake_reduction.py のアンチシェイク処理を改善
- サブピクセルシフトの計算を追加
- 最大シフト量を 10 に変更
- 画像の平行移動と回転処理を最適化
- GUI の MatcherUI クラスに成功フラグを追加

### 修正

- 標準化処理を追加し、画像の差分計算を最適化
- preprocess.py から不要なデバッグ出力を削除

## [0.28.1] - 2025-01-XX

### 変更

- バージョンを 0.27.1 から 0.28.1 に更新
- README.md に新しいバージョン番号を反映
- GUI の MatcherUI クラスに成功フラグを追加
- preprocess.py から不要なデバッグ出力を削除

## [0.28.0] - 2025-01-XX

### 変更

- motion 関数のサブピクセルマッチング処理を改善
- 標準化処理を追加
- diffImage 関数でも標準化を適用
- 画像の差分計算を最適化
- subpixel_match 関数にサブピクセルオプションを追加
- サブピクセル処理が失敗しても破綻しないように調整
- Stitcher クラス内の tspos ファイルの読み込み処理で列のデータ型を整数から浮動小数点数に変更
- 計算精度が向上

## [0.26.1] - 2025-01-XX

### 変更

- shake_reduction.py のアンチシェイク処理を改善
- サブピクセルシフトの計算を追加
- 最大シフト量を 10 に変更
- 画像の平行移動と回転処理を最適化
- 画像処理の精度が向上

## [0.26.0] - 2025-01-XX

### 追加

- 動画生成処理に進捗通知機能を追加
- make_movie 関数に進捗コールバックを実装
- ffmpeg の実行中に進捗を表示
- GUI 側でプログレスバーを表示
- 進捗を更新する処理を追加
- converter_control_widget 関数を追加
- オプションの表示と制御を改善

### 変更

- movie.py の make_movie 関数をリファクタリング
- ffmpeg の呼び出しを新しい video モジュールに移動
- フレームのファイル名生成を簡素化
- 新たに ffmpeg.py を追加
- ffmpeg コマンドの実行を管理する関数を実装
- ffmpeg のインストール状況に応じて movie オプションの制御を追加
- ffmpeg が未インストールの場合、CRF とエンコーダーオプションを無効化
- imageseq オプションを強制的にチェック状態で無効化
- 動画ファイル選択ダイアログに.mkv 形式を追加
- 対応するファイル形式を拡張
- 動画ファイルの読み込み処理を video_loader_factory に変更
- コードの一貫性を向上
- cv2toQImage 関数を trainscanner.widget モジュールからインポート
- EditorGUI および AsyncImageLoader クラス内での使用を更新
- 不要な cv2toQImage 関数の定義を削除
- コードの重複を排除し、可読性を向上

### 修正

- shake_reduction.py の標準化関数を修正
- データ型を float32 に変更
- アンチシェイク処理内での焦点管理を改善
- マッチエリアの処理を最適化
- 画像処理の精度と効率が向上

## [0.25.0] - 2025-01-XX

### 追加

- 手ぶれ補正ツール「antishake」を追加
- README に手ぶれ補正の説明を追加
- ショートカット機能を実装
- ウィンドウを閉じる操作を簡素化

### 変更

- 動画作成関数の引数を変更
- ビットレートから CRF（可変ビットレート）に切り替え
- ヘルプメッセージを更新
- CRF のデフォルト値を設定
- ヘルプオーバーレイをヘルプダイアログに名称変更
- 操作方法の説明を改善
- 不要なコードを削除
- ダイアログの表示位置を調整する機能を削除
- 画像選択ウィンドウにドラッグ＆ドロップ機能を追加
- ファイルをドロップした際に動画を処理する機能を実装
- ヘルプオーバーレイを追加
- 操作方法を説明するテキストを表示する機能を実装
- 動画処理の際にヘルプを初回のみ表示
- 画像選択ウィンドウに処理開始ボタンを追加
- ボタンのスタイルを設定
- 画像の表示サイズを調整
- 長方形の座標制限を改善
- キーボード操作で長方形を全て消去できる機能を追加

### 修正

- 手ぶれ補正機能のデバッグ用に、マッチエリアの表示を一時的に無効化
- 手ぶれ補正機能の改善：新たにパディング計算を追加
- マッチエリアの比較方法を修正
- マッチ領域が画面外にはみでても動くようになりました
- 描画される長方形の線の太さとテキストのスケールを変更
- 出力ファイル名をコンソールに表示するように修正

## [0.24.2] - 2025-01-XX

### 変更

- ファイル配置を変更

## [0.24.0] - 2025-01-XX

### 追加

- 新しい画像選択ウィンドウを追加
- 動画のフレームを表示・選択できる機能を実装
- 選択した領域に基づいて動画の手ぶれ補正を行うための処理を追加
- 日本語訳を追加
- i18n 関数を使用して、GUI 内のテキストを国際化
- 翻訳機能が強化され、ユーザーインターフェースの多言語対応が向上
- Qt の i18n に依存するのをやめ、自前の i18n 関数を準備
- linguist 互換とする
- コマンドライン引数のパーサーを各コンバーターファイルに追加
- 翻訳機能を実装
- GUI に関連するオプションの説明を日本語と英語で整備
- 各種オプションのデフォルト値やヘルプメッセージを改善
- パラメータの取得方法を改善
- スライダーの実装を強化
- QFloatSlider と QLogSlider を追加
- GUI のオプションを動的に取得できるように
- 動画の長さにデフォルト値を設定
- エラーハンドリングを強化
- オプションの GUI 化は 8 割がた完成
- GUI の自動生成(途上)
- コマンドライン引数のパーサーを各コンバーターファイルに追加
- クリックライブラリから argparse ライブラリに移行
- 引数の処理が統一され、可読性が向上
- SettingsGUI のタブウィジェットのラベルを辞書形式に変更
- ffmpeg が未インストールの場合にタブを無効化する処理を追加
- 未使用のプログレスバー関連のコードを削除
- SettingsGUI にタブウィジェットを追加
- 画像処理オプションを整理
- 未使用のラジオボタンと関連コードをコメントアウト

### 変更

- バージョンを 0.23.0 から 0.24.0 に更新
- README.md の内容を修正
- VideoLoader 関数をプラットフォームに応じて video_cv2 モジュールを直接呼び出すように修正
- 未使用のインポートを削除
- サポートされていないプラットフォームに対するエラーハンドリングを追加
- バージョン情報を削除
- SettingsGUI に「Ctrl+W」と「Ctrl+Q」のショートカットを追加
- ウィンドウを閉じたりアプリケーションを終了したりする操作が簡単に
- 画像処理の最適化を行い、OpenCV から QImage への変換処理を改善
- スリット幅の計算ロジックを修正
- 画像の中央を切り出す処理を追加
- 未使用のインポートを削除し、コードの可読性を向上
- キャンバスの境界計算を改善
- 画像追加時のキャンバスサイズ変更処理を最適化
- 未使用のフラグを削除し、コードの可読性を向上
- Editor ウィンドウのサイズを変えられるようにした
- Stitch ボタンを Editor ウィンドウに移設
- AsyncImageLoader クラスにエラーハンドリングを追加
- ビデオファイルの読み込みエラー時にシグナルを発信
- EditorGUI クラスでエラーメッセージを表示する機能を実装
- やっと EditorGUI のサイズが可変になった
- 未使用のメソッドを削除
- focus の検証メソッドを追加
- deformation_image_layout メソッド内でのレイアウト設定を修正
- 画像のスケーリング処理をアスペクト比を維持するように改善
- FrameInfo データクラスを追加
- AsyncImageLoader クラスでのフレーム管理を改善
- フレームの間引き処理を実装
- GUI の更新頻度を調整
- MyLabel クラスのマウスイベント処理を修正
- focus の更新を行うように
- ショートカット機能を追加
- 各 GUI クラスにおいて「Ctrl+W」でウィンドウを閉じることができるように

## [0.23.1] - 2025-01-XX

### 修正

- stitch_gui.py の Renderer クラスで、処理中に stitcher.after()の呼び出しをコメントアウト
- 処理の中断時の動作を改善

## [0.23.0] - 2025-01-XX

### 変更

- バージョンを 0.20.0 から 0.22.0 に更新
- README.md のバージョン表記を修正
- tspos に対して先頭および末尾のフレームを追加するメソッドを実装
- フレーム情報の管理を改善
- tspos の初期化方法を修正
- 出力形式を変更

### 修正

- bitrate の小さい動画を読みこむと末尾を読まない問題を解決
- AsyncImageLoader の最大フレーム数を 256 から 128 に変更
- SettingsGUI の加速度スライダーの範囲を 1 から 15 から 1 から 100 に拡張
- Stitcher の画像が巨大になる問題を修正
- AsyncImageLoader クラスにフレーム情報を管理する FrameInfo データクラスを追加
- フレームの間引き処理を改善
- updateTimeLine メソッドを修正
- フレーム情報を適切に受け取るように
- エラーハンドリングを強化
- ログ出力を追加

## [0.22.1] - 2025-01-XX

### 修正

- pass1_gui.py の cv2toQImage 関数を修正
- OpenCV を使用して色の順序を BGR から RGB に変換する処理を追加

## [0.22.0] - 2025-01-XX

### 変更

- バージョンを 0.19.10 に更新
- README.md のバージョン表記を修正

### 修正

- stitch_gui の画面表示が異常に遅くなる問題を修正

## [0.21.0] - 2025-01-XX

### 変更

- バージョンを 0.19.9 に更新
- README.md のバージョン表記を修正

### 修正

- pass1_gui.py の cv2toQImage 関数を修正
- 色の順序を反転させる処理を簡素化
- Worker クラスの finished シグナルに成功フラグを追加
- MatcherUI クラスの finishIt メソッドを更新
- 成功状態を保持するように
- pass1.py でモーションが検出されなかった場合のエラーログを追加
- trainscanner_gui.py で MatcherUI の成功状態を確認する条件を修正

## [0.20.2] - 2025-01-XX

### 変更

- 0.19.8 @yamakox さんの PR をマージして deploy

## [0.20.1] - 2025-01-XX

### 変更

- バージョンを 0.19.7 に更新
- README.md に mp4 エンコーダーオプションを追加

### 追加

- 依存関係に pillow を追加

### 修正

- Windows でファイルのドラッグ&ドロップが正常に動作しない不具合を修正
- ffmpeg のコマンドラインの output 引数を修正

### 追加

- ビデオエンコーダを指定するオプションを追加

### 変更

- Windows では symlink が作れないらしいので、hardlink に変更

## [0.20.0] - 2025-01-XX

### 変更

- StitcherUI の初期化時にパラメータを出力
- プレビュー比率の計算を改善
- 幅と高さの取得を整理

### 追加

- preprocessor 部の UI を別ファイルに分ける

### 修正

- draw_focus_area および draw_slit_position 関数のドキュメンテーションを修正
- diffImage 関数の引数を簡略化
- focus および slitpos の描画をコメントアウト
- EditorUI のウィンドウの中の要素を整理

### 変更

- バージョンを 0.19.5 に更新
- README.md のバージョン表記を修正

### 修正

- スライダーの最小高さ設定をコメントアウト
- レイアウトの柔軟性を向上

## [0.19.10] - 2025-01-XX

### 変更

- バージョンを 0.19.4 に更新
- README.md のバージョン表記を修正

### 修正

- trainscanner*gui.py 内の exec*メソッドを exec メソッドに変更
- app.exec\_()を修正

## [0.19.9] - 2025-01-XX

### 変更

- Refactor GUI components in trainscanner_gui.py to improve layout flexibility and responsiveness
- Changed fixed sizes to minimum sizes for various elements
- Updated method calls for compatibility
- Added resize event handling
- Introduced a new binary file **init**.pyc

### 修正

- Update ffmpeg command to use platform-specific codec for video encoding in movie2.py and scroll.py
- GUI の言語設定取得方法を改善
- 環境変数が未設定の場合に QLocale を使用するように修正
- movie2.py で viewport_height のチェックを追加

### 変更

- バージョンを 0.19.0 に更新
- README.md と temp_README.md に開発中の版を試すためのインストール方法を追加

### 追加

- 保存前に crop できるようになった

### 変更

- Makefile にタグ付け機能を追加
- デプロイターゲットを更新
- ビルド後に自動的にバージョンタグを作成できるように

## [0.19.8] - 2025-01-XX

### 変更

- バージョンを 0.18.0 に更新
- GUI の翻訳機能を強化
- 映画ファイルを開く際のメッセージを改善
- フランス語の翻訳ファイルを追加
- 言語設定の取得方法を環境変数に基づいて修正

### 修正

- Makefile と翻訳ファイルを更新
- converter_gui.py の参照を gui.py に変更
- trainscanner_ja.ts 内のメッセージの整形を行い、翻訳の一貫性を向上

### 追加

- pyproject.toml に tqdm ライブラリを追加
- movie2.py の make_movie 関数で進捗バーを実装

### 変更

- ビットレートのデフォルト値を None に変更
- ffmpeg コマンドの引数を修正

## [0.19.7] - 2025-01-XX

### 追加

- pyproject.toml の ts_converter エントリを更新
- converter_gui.py を新規作成
- GUI のコア機能と画像処理を実装
- ユーザーが画像をドラッグ＆ドロップできる機能
- 処理オプションを選択するためのラジオボタンを追加

### 変更

- Makefile に新しいターゲットを追加
- Markdown ファイルを生成するための replacer.py スクリプトを新規作成
- pyproject.toml のバージョンを 0.17.0 に更新
- movify 関数の実装を修正
- README.md を更新
- 各種コンバータの使用方法を明確に

## [0.19.6] - 2025-01-XX

### 追加

- CHANGELOG.md を新規作成
- バージョン 0.16.1 から 0.1.0 までの変更履歴を追加
- 新しい scroll.py を追加
- 横スクロール動画を生成する機能を実装
- 既存の movie2.py の make_movie 関数に新しい引数を追加
- 動画生成の柔軟性を向上
- converter_gui.py での動画生成処理を scroll モジュールに移行

### 変更

- ExtensibleCanvasWidget にドラッグ機能を追加
- 描画完了時の矩形表示を実装
- ボタンのテキストを「Crop + Finish」に変更

## [0.19.5] - 2025-01-XX

### 修正

- tsconf ができない問題を修正

### 変更

- VideoLoader クラスの next メソッドを修正
- フレームの取得方法をディレクトリ内の PNG ファイルのソートされたリストから取得するように変更
- ファイル名がソート可能であれば自由に命名できるように

### 追加

- video ドライバーを別フォルダーに移転
- image の束のはいったディレクトリを D&D すると、ムービー同様に読む機能を追加
- ただし tsconf 等のファイル出力が動作していない

## [0.19.4] - 2025-01-XX

### 追加

- 新しい画像選択ウィンドウを追加
- 動画のフレームを表示・選択できる機能を実装
- 選択した領域に基づいて動画の手ぶれ補正を行うための処理を追加

### 変更

- 日本語訳を追加
- i18n 関数を使用して、GUI 内のテキストを国際化
- 翻訳機能が強化され、ユーザーインターフェースの多言語対応が向上

## [0.19.3] - 2025-01-XX

### 変更

- Qt の i18n に依存するのをやめ、自前の i18n 関数を準備
- linguist 互換とする

## [0.19.2] - 2025-01-XX

### 変更

- バージョンを 0.18.0 に更新
- README.md の内容を修正
- コマンドライン引数のパーサーを各コンバーターファイルに追加
- 翻訳機能を実装
- GUI に関連するオプションの説明を日本語と英語で整備
- 各種オプションのデフォルト値やヘルプメッセージを改善

### 追加

- パラメータの取得方法を改善
- スライダーの実装を強化
- QFloatSlider と QLogSlider を追加
- GUI のオプションを動的に取得できるように
- 動画の長さにデフォルト値を設定
- エラーハンドリングを強化

## [0.19.1] - 2025-01-XX

### 変更

- オプションの GUI 化は 8 割がた完成
- GUI の自動生成(途上)
- コマンドライン引数のパーサーを各コンバーターファイルに追加
- クリックライブラリから argparse ライブラリに移行
- 引数の処理が統一され、可読性が向上

### 追加

- SettingsGUI のタブウィジェットのラベルを辞書形式に変更
- ffmpeg が未インストールの場合にタブを無効化する処理を追加
- 未使用のプログレスバー関連のコードを削除
- SettingsGUI にタブウィジェットを追加
- 画像処理オプションを整理
- 未使用のラジオボタンと関連コードをコメントアウト

## [0.19.0] - 2025-01-XX

### 変更

- VideoLoader 関数をプラットフォームに応じて video_cv2 モジュールを直接呼び出すように修正
- 未使用のインポートを削除
- サポートされていないプラットフォームに対するエラーハンドリングを追加

### 追加

- バージョン情報を削除
- SettingsGUI に「Ctrl+W」と「Ctrl+Q」のショートカットを追加
- ウィンドウを閉じたりアプリケーションを終了したりする操作が簡単に

### 修正

- 画像処理の最適化を行い、OpenCV から QImage への変換処理を改善
- スリット幅の計算ロジックを修正
- 画像の中央を切り出す処理を追加
- 未使用のインポートを削除し、コードの可読性を向上

## [0.18.0] - 2025-01-XX

### 修正

- キャンバスの境界計算を改善
- 画像追加時のキャンバスサイズ変更処理を最適化
- 未使用のフラグを削除し、コードの可読性を向上

### 追加

- Editor ウィンドウのサイズを変えられるようにした
- Stitch ボタンを Editor ウィンドウに移設

### 変更

- AsyncImageLoader クラスにエラーハンドリングを追加
- ビデオファイルの読み込みエラー時にシグナルを発信
- EditorGUI クラスでエラーメッセージを表示する機能を実装

## [0.17.0] - 2025-01-XX

### 追加

- やっと EditorGUI のサイズが可変になった
- 未使用のメソッドを削除
- focus の検証メソッドを追加
- deformation_image_layout メソッド内でのレイアウト設定を修正
- 画像のスケーリング処理をアスペクト比を維持するように改善
- FrameInfo データクラスを追加
- AsyncImageLoader クラスでのフレーム管理を改善
- フレームの間引き処理を実装
- GUI の更新頻度を調整
- MyLabel クラスのマウスイベント処理を修正
- focus の更新を行うように
- ショートカット機能を追加
- 各 GUI クラスにおいて「Ctrl+W」でウィンドウを閉じることができるように

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

## [0.29.1] - 2025-06-24

### 変更

### 追加

### 修正
