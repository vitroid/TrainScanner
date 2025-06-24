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
- CHANGELOG.md に前バージョンからの変更点を記録
- README.md を更新（temp_README.md が存在する場合）
- 更新されたファイルをステージングエリアに追加

### post-commit フック

- コミット後にバージョンタグを自動的に作成
- 既存のタグがある場合はスキップ

## 動作例

```bash
# ファイルを変更してコミット
git add .
git commit -m "バグ修正"

# 自動的に以下が実行される：
# 1. バージョン番号が増加（例：0.29.0 → 0.29.1）
# 2. CHANGELOG.mdに新しいエントリが追加
# 3. README.mdが更新される
# 4. バージョンタグが作成される
```

## 注意事項

- この hooks は、Cursor でコミットする際にも自動的に実行されます
- バージョン番号は毎回 patch レベルで増加します
- コミットログはそのまま CHANGELOG.md に記録されるので、後で手動で分類してください
