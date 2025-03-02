# UpNote → Notion インポートツール

## 概要

このスクリプト `notion_bulk_upload.py` は、UpNoteからエクスポートしたマークダウンファイルをNotion APIを使用してNotionデータベースにインポートするツールです。マークダウン形式のノートとその画像を、Notionのデータベースエントリとして一括アップロードします。

## 特徴

- マークダウンファイルの一括アップロード
- 画像の自動処理とアップロード
- Notionページのカバー画像設定
- 画像プロパティへの画像追加
- 自動アイコン（絵文字）設定
- 設定の保存と再利用
- 進捗表示とエラーハンドリング
- ドライラン機能
- 詳細なコマンドラインオプション

## 準備

1. UpNoteからノートをエクスポート（マークダウン形式）
2. エクスポートしたファイルを `~/src/up_note_to_notion/exported_notes/` に配置
3. Notion APIキーを取得（https://www.notion.so/my-integrations）
4. NotionデータベースIDを取得
5. Notionデータベースと統合を接続

## インストール

必要なライブラリをインストールします：

```bash
pip install requests
```

## 使用方法

### 基本的な使用方法

```bash
python notion_bulk_upload.py
```

初回実行時は、Notion APIキーとデータベースIDの入力を求められます。

### コマンドラインオプション

```
--api-key KEY          : Notion APIキーを指定
--database-id ID       : Notion データベースIDを指定
--notes-dir DIR        : マークダウンファイルのディレクトリを指定
--use-config           : 保存された設定を使用
--save-config          : 設定を保存
--no-interactive       : 対話モードを無効化
--dry-run              : 実際にアップロードせずに処理内容を確認
--image-property NAME  : 画像プロパティ名を指定（デフォルト: 画像）
--no-cover-image       : ページのカバー画像を設定しない
--no-image-property    : 画像プロパティを設定しない
--no-icon              : ページのアイコンを設定しない
--readme               : 使用方法の詳細を表示して終了
```

### 使用例

#### APIキーとデータベースIDを指定

```bash
python notion_bulk_upload.py --api-key "secret_..." --database-id "1aa2ab4c..."
```

#### 保存された設定を使用

```bash
python notion_bulk_upload.py --use-config
```

#### ドライラン（実際にアップロードせず確認のみ）

```bash
python notion_bulk_upload.py --use-config --dry-run
```

#### カスタムディレクトリを指定

```bash
python notion_bulk_upload.py --notes-dir "/path/to/notes"
```

#### 画像プロパティ名を変更

```bash
python notion_bulk_upload.py --image-property "サムネイル"
```

#### カバー画像を使用せず、画像プロパティのみ設定

```bash
python notion_bulk_upload.py --no-cover-image
```

#### アイコンを設定しない

```bash
python notion_bulk_upload.py --no-icon
```

## サポートされるマークダウン形式

- 見出し（# ## ###）
- リスト（- * 1.）
- 引用（>）
- コードブロック（```）
- 太字（**text**）
- 罫線（---、\--）
- <br>タグ（空のブロックに変換）

## 画像処理

- 画像ファイルはレンタルサーバーにアップロードされている必要があります
- 画像URLは設定されたベースURLに画像ファイル名を結合して生成されます
- 最初の画像がカバー画像として使用されます
- すべての画像がプロパティの画像として使用されます
- 画像は本文内にも挿入されます

## アイコン設定

本文の内容から自動的にページアイコン（絵文字）が設定されます。キーワードに基づいて適切な絵文字が選択されます。

## 設定ファイル

設定は `notion_config.ini` に保存されます。このファイルにはAPIキー、データベースID、画像プロパティ名などの設定が含まれます。

### 設定ファイルの作成方法

1. `notion_config.ini.org` ファイルをコピーして `notion_config.ini` という名前で保存します。
2. `notion_config.ini` ファイルを開き、以下の情報を入力します。
   - `[Notion]` セクションに、`api_key` と `database_id` を入力します。
   - `[Options]` セクションで、必要に応じてオプションを設定します。

以下は `notion_config.ini` のサンプルです：

```
[Notion]
api_key = your_api_key_here
database_id = your_database_id_here

[Options]
image_property = 画像
use_cover_image = true
use_image_property = true
use_icon = true
```

> **注意:** `notion_config.ini` ファイルは `.gitignore` に追加されており、Gitリポジトリには含まれません。

## 注意事項

- 画像ファイルはレンタルサーバー上に存在する必要があります
- 大量のノートをアップロードする場合、Notion APIのレート制限に注意してください
- APIキーは安全に保管されます（設定ファイルのパーミッションは600に設定）

## エラーハンドリング

- ネットワークエラーやAPIエラーが発生した場合、自動的にリトライします
- 失敗したファイルのリストが表示されます
- 詳細なエラーメッセージが表示されます

## ライセンス

このスクリプトは自由に使用・改変できます。