# Git Hooks

このディレクトリには、TrainScanner プロジェクト用の Git hooks が含まれています。

## 設定方法

### 1. 手動設定

```bash
# pre-commitフックを設定
cp hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# post-commitフックを設定
cp hooks/post-commit .git/hooks/post-commit
chmod +x .git/hooks/post-commit
```

### 2. 自動設定（推奨）

```bash
# 全てのhooksを自動的に設定
make setup-hooks
```

## 機能

### pre-commit フック

- コミット時にバージョン番号を自動的に増加（patch）
- README.md の自動更新は現在無効化されています
- 更新されたファイルをステージングエリアに追加

### post-commit フック

- コミット後にバージョンタグを自動的に作成
- CHANGELOG.md に前バージョンからの変更点を記録
- 既存のタグがある場合はスキップ

## 動作例

```bash
# ファイルを変更してコミット
git add .
git commit -m "バグ修正"

# 自動的に以下が実行される：
# 1. バージョン番号が増加（例：0.29.0 → 0.29.1）
# 2. README.md が更新される
# 3. コミットが完了
# 4. CHANGELOG.md に新しいエントリが追加
# 5. バージョンタグが作成される

# CHANGELOG.md の変更を手動でコミット（必要に応じて）
git add CHANGELOG.md
git commit -m "CHANGELOG.md を更新"
```

## 処理フロー

1. **pre-commit**: バージョン番号増加 → README.md 更新 → ファイルをステージング
2. **コミット実行**: 通常のコミット処理
3. **post-commit**: CHANGELOG.md 更新 → バージョンタグ作成
4. **手動コミット**: CHANGELOG.md の変更をコミット（推奨）

## 注意事項

- この hooks は、Cursor でコミットする際にも自動的に実行されます
- バージョン番号は毎回 patch レベルで増加します
- コミットログはそのまま CHANGELOG.md に記録されるので、後で手動で分類してください
- CHANGELOG.md の更新は post-commit で実行されますが、無限ループを避けるため手動でコミットする必要があります
- CHANGELOG.md の変更はステージングされていないので、必要に応じて `git add CHANGELOG.md` してからコミットしてください
