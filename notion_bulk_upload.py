import requests
import json
import os
import re
import sys
import time
import getpass
import configparser
import argparse
from datetime import datetime

# ------------- コマンドライン引数の解析 -------------
def parse_args():
    parser = argparse.ArgumentParser(description='UpNoteからエクスポートしたマークダウンファイルをNotionにアップロードするスクリプト')
    parser.add_argument('--api-key', help='Notion APIキー（指定しない場合は対話的に入力を求めます）')
    parser.add_argument('--database-id', help='Notion データベースID（指定しない場合は対話的に入力を求めます）')
    parser.add_argument('--notes-dir', default=os.path.expanduser("~/src/up_note_to_notion/exported_notes"),
                        help='マークダウンファイルが格納されているディレクトリのパス')
    parser.add_argument('--use-config', action='store_true', help='保存された設定を使用する')
    parser.add_argument('--save-config', action='store_true', help='入力した設定を保存する')
    parser.add_argument('--no-interactive', action='store_true', help='対話モードを無効にする（APIキーとデータベースIDが必要）')
    parser.add_argument('--dry-run', action='store_true', help='実際にアップロードせずに処理内容を確認する')
    parser.add_argument('--image-property', default='画像', help='Notionデータベースの画像プロパティ名（デフォルト: 画像）')
    parser.add_argument('--no-cover-image', action='store_true', help='ページのカバー画像を設定しない')
    parser.add_argument('--no-image-property', action='store_true', help='画像プロパティを設定しない')
    parser.add_argument('--no-icon', action='store_true', help='ページのアイコンを設定しない')
    parser.add_argument('--readme', action='store_true', help='使用方法の詳細を表示して終了')

    args = parser.parse_args()

    # READMEの表示
    if args.readme:
        show_readme()
        sys.exit(0)

    return args

def show_readme():
    """使用方法の詳細を表示"""
    readme = """
==========================================================
UpNote → Notion インポートツール 使用方法
==========================================================

【概要】
このスクリプトは、UpNoteからエクスポートしたマークダウンファイルを
Notion APIを使用してNotionデータベースにインポートするツールです。

【準備】
1. UpNoteからノートをエクスポート（マークダウン形式）
2. エクスポートしたファイルを ~/src/up_note_to_notion/exported_notes/ に配置
3. Notion APIキーを取得（https://www.notion.so/my-integrations）
4. NotionデータベースIDを取得
5. Notionデータベースと統合を接続

【基本的な使用方法】
$ python notion_bulk_upload.py

【オプション】
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
--readme               : この使用方法を表示

【使用例】
# 基本的な使用方法（対話モード）
$ python notion_bulk_upload.py

# APIキーとデータベースIDを指定
$ python notion_bulk_upload.py --api-key "secret_..." --database-id "1aa2ab4c..."

# 保存された設定を使用
$ python notion_bulk_upload.py --use-config

# ドライラン（実際にアップロードせず確認のみ）
$ python notion_bulk_upload.py --use-config --dry-run

# カスタムディレクトリを指定
$ python notion_bulk_upload.py --notes-dir "/path/to/notes"

# 画像プロパティ名を変更
$ python notion_bulk_upload.py --image-property "サムネイル"

# カバー画像を使用せず、画像プロパティのみ設定
$ python notion_bulk_upload.py --no-cover-image

# アイコンを設定しない
$ python notion_bulk_upload.py --no-icon

【サポートされるマークダウン形式】
- 見出し（# ## ###）
- リスト（- * 1.）
- 引用（>）
- コードブロック（```）
- 太字（**text**）
- 罫線（---）
- <br>タグ（空のブロックに変換）

【注意事項】
- 画像ファイルはレンタルサーバーにアップロードされている必要があります
- 画像URLは設定されたベースURLに画像ファイル名を結合して生成されます
- 最初の画像がカバー画像およびプロパティの画像として使用されます
- 本文の内容から自動的にページアイコン（絵文字）が設定されます
"""
    print(readme)

# ------------- 設定ファイルの読み込み -------------
CONFIG_FILE = os.path.expanduser("~/src/up_note_to_notion/notion_config.ini")

def load_config():
    """設定ファイルから設定を読み込む"""
    config = configparser.ConfigParser()

    if os.path.exists(CONFIG_FILE):
        try:
            config.read(CONFIG_FILE)
            if 'Notion' in config and 'api_key' in config['Notion'] and 'database_id' in config['Notion']:
                result = {
                    'api_key': config['Notion']['api_key'],
                    'database_id': config['Notion']['database_id']
                }

                # オプション設定の読み込み
                if 'Options' in config:
                    if 'image_property' in config['Options']:
                        result['image_property'] = config['Options']['image_property']
                    if 'use_cover_image' in config['Options']:
                        result['use_cover_image'] = config['Options'].getboolean('use_cover_image')
                    if 'use_image_property' in config['Options']:
                        result['use_image_property'] = config['Options'].getboolean('use_image_property')
                    if 'use_icon' in config['Options']:
                        result['use_icon'] = config['Options'].getboolean('use_icon')

                return result
        except Exception as e:
            print(f"⚠️ 設定ファイルの読み込みに失敗しました: {e}")

    return None

def save_config(api_key, database_id, image_property=None, use_cover_image=None, use_image_property=None, use_icon=None):
    """設定をファイルに保存する"""
    try:
        config = configparser.ConfigParser()
        config['Notion'] = {
            'api_key': api_key,
            'database_id': database_id
        }

        # オプション設定の保存
        config['Options'] = {}
        if image_property is not None:
            config['Options']['image_property'] = image_property
        if use_cover_image is not None:
            config['Options']['use_cover_image'] = str(use_cover_image)
        if use_image_property is not None:
            config['Options']['use_image_property'] = str(use_image_property)
        if use_icon is not None:
            config['Options']['use_icon'] = str(use_icon)

        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)

        # 設定ファイルのパーミッションを制限（所有者のみ読み書き可能）
        os.chmod(CONFIG_FILE, 0o600)
        print("✅ 設定を保存しました")
    except Exception as e:
        print(f"⚠️ 設定の保存に失敗しました: {e}")

# ------------- メイン処理 -------------
def main():
    # コマンドライン引数の解析
    args = parse_args()

    # ディレクトリの設定
    global NOTES_DIR, IMAGE_PROPERTY_NAME, USE_COVER_IMAGE, USE_IMAGE_PROPERTY, USE_ICON
    NOTES_DIR = args.notes_dir
    IMAGE_PROPERTY_NAME = args.image_property
    USE_COVER_IMAGE = not args.no_cover_image
    USE_IMAGE_PROPERTY = not args.no_image_property
    USE_ICON = not args.no_icon

    if not os.path.exists(NOTES_DIR):
        print(f"❌ エラー: {NOTES_DIR} が存在しません。フォルダを確認してください。")
        sys.exit(1)

    print("✅ ノートフォルダのチェック完了")
    print(f"✅ 画像プロパティ名: {IMAGE_PROPERTY_NAME if USE_IMAGE_PROPERTY else '使用しない'}")
    print(f"✅ カバー画像: {'使用する' if USE_COVER_IMAGE else '使用しない'}")
    print(f"✅ ページアイコン: {'使用する' if USE_ICON else '使用しない'}")

    # APIキーとデータベースIDの取得
    global NOTION_API_KEY, DATABASE_ID

    try:
        # 非対話モードの場合
        if args.no_interactive:
            if args.api_key and args.database_id:
                NOTION_API_KEY = args.api_key
                DATABASE_ID = args.database_id
            elif args.use_config:
                config = load_config()
                if config:
                    NOTION_API_KEY = config['api_key']
                    DATABASE_ID = config['database_id']

                    # オプション設定の読み込み
                    if 'image_property' in config and not args.image_property:
                        IMAGE_PROPERTY_NAME = config['image_property']
                    if 'use_cover_image' in config and not args.no_cover_image:
                        USE_COVER_IMAGE = config['use_cover_image']
                    if 'use_image_property' in config and not args.no_image_property:
                        USE_IMAGE_PROPERTY = config['use_image_property']
                    if 'use_icon' in config and not args.no_icon:
                        USE_ICON = config['use_icon']

                    print("✅ 保存された設定を読み込みました")
                else:
                    print("❌ 保存された設定が見つかりません。--api-key と --database-id を指定するか、対話モードを使用してください。")
                    sys.exit(1)
            else:
                print("❌ 非対話モードでは --api-key と --database-id を指定するか、--use-config を指定する必要があります。")
                sys.exit(1)
        # 対話モード
        else:
            # コマンドライン引数で指定された場合
            if args.api_key and args.database_id:
                NOTION_API_KEY = args.api_key
                DATABASE_ID = args.database_id
            # 設定ファイルを使用する場合
            elif args.use_config or (not args.api_key and not args.database_id):
                config = load_config()
                if config and (args.use_config or input("💾 保存された設定を使用しますか？ (y/n): ").lower() == 'y'):
                    NOTION_API_KEY = config['api_key']
                    DATABASE_ID = config['database_id']

                    # オプション設定の読み込み
                    if 'image_property' in config and not args.image_property:
                        IMAGE_PROPERTY_NAME = config['image_property']
                    if 'use_cover_image' in config and not args.no_cover_image:
                        USE_COVER_IMAGE = config['use_cover_image']
                    if 'use_image_property' in config and not args.no_image_property:
                        USE_IMAGE_PROPERTY = config['use_image_property']
                    if 'use_icon' in config and not args.no_icon:
                        USE_ICON = config['use_icon']

                    print("✅ 保存された設定を読み込みました")
                else:
                    NOTION_API_KEY = getpass.getpass("🔑 Notion APIキーを入力: ")
                    DATABASE_ID = input("🗂️ Notion データベースIDを入力: ")

            # 設定を保存するか確認
            if args.save_config or (not args.use_config and not args.no_interactive and
                                   input("💾 この設定を保存しますか？ (y/n): ").lower() == 'y'):
                save_config(
                    NOTION_API_KEY,
                    DATABASE_ID,
                    image_property=IMAGE_PROPERTY_NAME,
                    use_cover_image=USE_COVER_IMAGE,
                    use_image_property=USE_IMAGE_PROPERTY,
                    use_icon=USE_ICON
                )

        if not NOTION_API_KEY or not DATABASE_ID:
            print("❌ APIキーまたはデータベースIDが空です！正しく入力してください。")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n❌ 処理が中断されました。")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 入力処理中にエラーが発生しました: {e}")
        sys.exit(1)

    # Notion API の設定
    global url, headers
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    print("✅ Notion API の設定完了")

    # マークダウンファイルの処理
    try:
        md_files = [f for f in os.listdir(NOTES_DIR) if f.endswith(".md")]
        total_files = len(md_files)

        if total_files == 0:
            print(f"❌ エラー: {NOTES_DIR} にマークダウンファイルが見つかりません。")
            sys.exit(1)

        print(f"📊 合計 {total_files} 個のマークダウンファイルを処理します...")

        success_count = 0
        failed_files = []

        for index, filename in enumerate(md_files, 1):
            file_path = os.path.join(NOTES_DIR, filename)
            print(f"\n📝 処理中 ({index}/{total_files}): {filename}")
            note_data = parse_markdown(file_path)

            if args.dry_run:
                print(f"🔍 ドライラン: {note_data['title']} をアップロードします（実際には実行されません）")
                success_count += 1
            else:
                if upload_to_notion(note_data):
                    success_count += 1
                else:
                    failed_files.append(filename)

            show_progress(index, total_files)
            time.sleep(1)  # APIレート制限を考慮した待機時間

        # 結果サマリーを表示
        print(f"\n✅ 処理完了！")
        print(f"📊 結果サマリー:")
        print(f"  - 合計ファイル数: {total_files}")
        print(f"  - 成功: {success_count}")
        print(f"  - 失敗: {len(failed_files)}")

        if failed_files:
            print("\n❌ 失敗したファイル:")
            for failed_file in failed_files:
                print(f"  - {failed_file}")
    except KeyboardInterrupt:
        print("\n❌ 処理が中断されました。")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 処理中に予期せぬエラーが発生しました: {e}")
        sys.exit(1)

# ------------- 画像URLの生成（レンタルサーバー版） -------------
BASE_IMAGE_URL = "https://www.soratomo.com/img_UpNote_diary/"

def generate_image_url(filename):
    """ファイル名からレンタルサーバー上の画像URLを生成"""
    # 画像ファイルの拡張子を小文字に統一（大文字の拡張子対応）
    name, ext = os.path.splitext(filename)
    normalized_filename = f"{name}{ext.lower()}"

    # 画像ファイルの存在確認（ローカルの Files ディレクトリ内）
    local_image_path = os.path.join(NOTES_DIR, "Files", filename)
    if not os.path.exists(local_image_path):
        print(f"⚠️ 警告: 画像ファイル {filename} がローカルに見つかりません。URLは生成されますが、サーバー上に存在するか確認してください。")

    return f"{BASE_IMAGE_URL}{normalized_filename}"

# ------------- 日付フォーマットをNotion用（ISO 8601）に変換する関数 -------------
def format_date(date_str):
    """YYYY-MM-DD HH:MM:SS を ISO 8601 形式に変換"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception as e:
        print(f"⚠️ 日付フォーマット変換エラー: {date_str} - {e}")
        return None

# ------------- 本文からアイコンを推測する関数 -------------
def predict_icon_from_content(content, title):
    """本文の内容からNotionページのアイコン（絵文字）を推測する"""
    # キーワードと対応する絵文字のマッピング
    keyword_to_emoji = {
        # 朝勉関連
        "朝勉": "🌅",
        "勉強": "📚",
        "学習": "📝",
        "勤続": "🔄",
        "早起き": "🌄",
        "朝活": "☀️",

        # 時間関連
        "時間": "⏰",
        "スケジュール": "📅",
        "予定": "📆",
        "締め切り": "⏳",
        "期限": "⌛",

        # 感情関連
        "嬉しい": "😊",
        "楽しい": "😄",
        "悲しい": "😢",
        "辛い": "😣",
        "疲れ": "😩",
        "頑張": "💪",
        "がんば": "💪",

        # 場所関連
        "家": "🏠",
        "実家": "🏡",
        "学校": "🏫",
        "会社": "🏢",
        "オフィス": "🏢",
        "カフェ": "☕",

        # 食事関連
        "食事": "🍽️",
        "朝食": "🍳",
        "昼食": "🍱",
        "夕食": "🍲",
        "晩ごはん": "🍲",
        "コーヒー": "☕",
        "お茶": "🍵",

        # 天気関連
        "晴れ": "☀️",
        "雨": "🌧️",
        "雪": "❄️",
        "曇り": "☁️",
        "台風": "🌀",
        "寒い": "🥶",
        "暑い": "🥵",

        # 季節関連
        "春": "🌸",
        "夏": "🌞",
        "秋": "🍂",
        "冬": "⛄",
        "年末": "🎍",
        "年始": "🎍",
        "正月": "🎍",

        # イベント関連
        "誕生日": "🎂",
        "クリスマス": "🎄",
        "ハロウィン": "🎃",
        "旅行": "✈️",
        "旅": "🧳",
        "休暇": "🏖️",
        "休日": "🛌",

        # 仕事関連
        "仕事": "💼",
        "会議": "🗣️",
        "プレゼン": "📊",
        "資料": "📑",
        "メール": "📧",
        "電話": "📞",

        # 健康関連
        "健康": "🏥",
        "運動": "🏃",
        "ジム": "🏋️",
        "ヨガ": "🧘",
        "散歩": "🚶",
        "睡眠": "😴",

        # 趣味関連
        "読書": "📖",
        "映画": "🎬",
        "音楽": "🎵",
        "ゲーム": "🎮",
        "料理": "👨‍🍳",
        "写真": "📷",
        "絵": "🎨",

        # 交通関連
        "電車": "🚆",
        "バス": "🚌",
        "車": "🚗",
        "自転車": "🚲",
        "飛行機": "✈️",
        "通勤": "🚶",

        # コミュニケーション関連
        "友達": "👫",
        "家族": "👨‍👩‍👧‍👦",
        "恋人": "💑",
        "会話": "💬",
        "電話": "📱",
        "メッセージ": "💌",

        # テクノロジー関連
        "パソコン": "💻",
        "スマホ": "📱",
        "アプリ": "📲",
        "インターネット": "🌐",
        "SNS": "📱",
        "プログラミング": "👨‍💻",

        # その他
        "アイデア": "💡",
        "メモ": "📝",
        "計画": "📋",
        "目標": "🎯",
        "成功": "🏆",
        "失敗": "😓",
        "質問": "❓",
        "答え": "❗",
        "重要": "⚠️",
        "緊急": "🚨",
        "お金": "💰",
        "買い物": "🛒",
        "プレゼント": "🎁",
        "音楽": "🎵",
        "スポーツ": "⚽",
        "ニュース": "📰",

        # 追加キーワード（より多様なアイコンを提供）
        "考え": "🤔",
        "思考": "💭",
        "発見": "🔍",
        "気づき": "💫",
        "成長": "📈",
        "変化": "🔄",
        "挑戦": "🏔️",
        "達成": "🏅",
        "反省": "🔄",
        "振り返り": "🔙",
        "未来": "🔮",
        "希望": "✨",
        "夢": "💫",
        "願い": "🙏",
        "感謝": "🙏",
        "喜び": "🎊",
        "驚き": "😲",
        "焦り": "💦",
        "不安": "😰",
        "心配": "😟",
        "安心": "😌",
        "リラックス": "🧘",
        "集中": "🎯",
        "忙しい": "⏰",
        "余裕": "😎",
        "自信": "💪",
        "迷い": "🤷",
        "決断": "✅",
        "選択": "🔀",
        "整理": "🗂️",
        "片付け": "🧹",
        "掃除": "🧼",
        "準備": "🔧",
        "始まり": "🎬",
        "終わり": "🏁",
        "継続": "🔁",
        "習慣": "📆",
        "ルーティン": "🔄",
        "改善": "📈",
        "工夫": "🛠️",
        "創造": "🎨",
        "発明": "💡",
        "実験": "🧪",
        "分析": "📊",
        "調査": "🔎",
        "研究": "🔬",
        "学び": "🎓",
        "教育": "👨‍🏫",
        "指導": "👨‍🏫",
        "相談": "💬",
        "アドバイス": "💡",
        "協力": "🤝",
        "チーム": "👥",
        "グループ": "👪",
        "コミュニティ": "🏘️",
        "社会": "🌐",
        "世界": "🌍",
        "自然": "🌳",
        "環境": "🌱",
        "動物": "🐾",
        "植物": "🌿",
        "花": "🌸",
        "海": "🌊",
        "山": "⛰️",
        "川": "🏞️",
        "空": "☁️",
        "星": "⭐",
        "月": "🌙",
        "太陽": "☀️",
        "朝": "🌅",
        "昼": "🌞",
        "夕方": "🌇",
        "夜": "🌃",
        "深夜": "🌌",
        "睡眠": "💤",
        "夢": "💭",
        "瞑想": "🧘",
        "ヨガ": "🧘‍♀️",
        "ストレッチ": "🤸",
        "ウォーキング": "🚶",
        "ランニング": "🏃",
        "トレーニング": "🏋️",
        "スポーツ": "🏅",
        "サッカー": "⚽",
        "野球": "⚾",
        "テニス": "🎾",
        "バスケ": "🏀",
        "水泳": "🏊",
        "ゴルフ": "⛳",
        "釣り": "🎣",
        "キャンプ": "⛺",
        "ハイキング": "🥾",
        "登山": "🧗",
        "サイクリング": "🚴",
        "ドライブ": "🚗",
        "旅": "🧳",
        "観光": "🗿",
        "美術館": "🏛️",
        "博物館": "🏛️",
        "映画館": "🎦",
        "劇場": "🎭",
        "コンサート": "🎵",
        "ライブ": "🎤",
        "フェス": "🎪",
        "パーティー": "🎉",
        "お祝い": "🎊",
        "記念日": "🎂",
        "結婚": "💒",
        "出産": "👶",
        "育児": "👨‍👩‍👧",
        "子育て": "👨‍👩‍👧",
        "教育": "🏫",
        "学校": "🏫",
        "大学": "🎓",
        "卒業": "🎓",
        "就職": "💼",
        "転職": "🔄",
        "昇進": "📈",
        "退職": "🚪",
        "老後": "👴",
        "人生": "🌈",
    }

    # 本文の冒頭160文字を抽出（画像タグを除去）
    clean_content = re.sub(r"!\[(?:[^\]]*)\]\((?:Files/)?([^)]+)\)", "", content).strip()

    # ハッシュタグを除去
    clean_content = re.sub(r"#\S+", "", clean_content)

    # "朝勉勤続〜日目"のパターンを除去
    clean_content = re.sub(r"朝勉勤続\d+日目[。]?", "", clean_content)

    # 冒頭160文字を取得
    intro_content = clean_content[:160]

    print(f"🔍 アイコン推測用テキスト: {intro_content[:30]}...")

    # 本文からキーワードを検索（優先度高）
    found_emojis = []
    for keyword, emoji in keyword_to_emoji.items():
        if keyword in intro_content:
            found_emojis.append((keyword, emoji))

    # 見つかったキーワードがあれば、最初のものを使用
    if found_emojis:
        # 最長のキーワードを優先（より具体的な内容を反映）
        found_emojis.sort(key=lambda x: len(x[0]), reverse=True)
        print(f"✅ キーワード「{found_emojis[0][0]}」に基づくアイコン: {found_emojis[0][1]}")
        return found_emojis[0][1]

    # 本文からキーワードが見つからない場合、日付パターンを検出（優先度低）
    day_match = re.search(r'(\d+)日目', title)
    if day_match:
        day_num = int(day_match.group(1))
        # 100日ごとに特別な絵文字を使用
        if day_num % 100 == 0:
            return "🎉"  # 100の倍数の日は祝いの絵文字
        elif day_num % 50 == 0:
            return "🎊"  # 50の倍数の日は別の祝いの絵文字
        elif day_num % 10 == 0:
            return "🔟"  # 10の倍数の日は数字の絵文字

        # 日数に応じた絵文字（1〜9日目）
        if 1 <= day_num % 10 <= 9:
            number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
            return number_emojis[(day_num % 10) - 1]

    # デフォルトのアイコン
    return "📝"  # デフォルトは「メモ」の絵文字

# ------------- Markdownファイルを解析する関数 -------------
def parse_markdown(file_path):
    try:
        print(f"🔍 {file_path} の解析開始…")

        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # YAMLヘッダーを削除（より堅牢な方法）
        yaml_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        yaml_content = yaml_match.group(1) if yaml_match else ""
        if yaml_match:
            content = content[yaml_match.end():].strip()
            print("✅ YAMLヘッダーを検出して削除しました")

        # `created:` または `date:` のどちらかを取得（YAMLヘッダーからも検索）
        created_match = re.search(r"created:\s*([\d-]+\s[\d:]+)", content + "\n" + yaml_content)
        updated_match = re.search(r"date:\s*([\d-]+\s[\d:]+)", content + "\n" + yaml_content)

        created = format_date(created_match.group(1)) if created_match else datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        updated = format_date(updated_match.group(1)) if updated_match else created

        print(f"📅 作成日: {created}, 更新日: {updated}")

        # 画像を抽出（より堅牢な正規表現）
        image_matches = re.findall(r"!\[(?:[^\]]*)\]\((?:Files/)?([^)]+)\)", content)
        image_filenames = [img for img in image_matches if img]

        # 最初の画像をカバー画像として使用
        cover_image = image_filenames[0] if image_filenames else None

        print(f"🖼 画像ファイル: {image_filenames}")
        if cover_image:
            print(f"🖼 カバー画像: {cover_image}")

        # 本文から画像タグを削除し、適切なブロック変換
        clean_body = re.sub(r"!\[(?:[^\]]*)\]\((?:Files/)?([^)]+)\)", "", content).strip()

        # 罫線を `divider` に変換（「\--」や「---」などのパターンに対応）
        clean_body = re.sub(r"\n-{2,}\n", "\n<HORIZONTAL_LINE>\n", clean_body)

        # 行頭の「\--」や「---」も区切り線に変換
        clean_body = re.sub(r"^-{2,}$", "<HORIZONTAL_LINE>", clean_body, flags=re.MULTILINE)
        clean_body = re.sub(r"^\\-{2,}$", "<HORIZONTAL_LINE>", clean_body, flags=re.MULTILINE)

        # <br>タグを空のブロックに変換
        clean_body = re.sub(r"<br>", "<EMPTY_BLOCK>", clean_body)

        # 段落に分割
        paragraphs = []
        for p in clean_body.split("\n"):
            if p.strip():
                # 空でない段落を追加
                paragraphs.append(p)
            else:
                # 空の段落は<EMPTY_BLOCK>として追加
                paragraphs.append("<EMPTY_BLOCK>")

        # 連続する空のブロックを削除（2つ以上連続しないように）
        filtered_paragraphs = []
        prev_empty = False
        for p in paragraphs:
            if p == "<EMPTY_BLOCK>":
                if not prev_empty:
                    filtered_paragraphs.append(p)
                    prev_empty = True
            else:
                filtered_paragraphs.append(p)
                prev_empty = False

        # タイトルを「朝勉勤続〇〇日目」のみ抽出
        title_match = re.search(r"(朝勉勤続\d+日目[。]?)", content)
        if title_match:
            title = title_match.group(1)
            # タイトルの末尾の句点「。」を削除
            title = title.rstrip("。")
        else:
            # ファイル名からタイトルを抽出（.mdを除去）
            title = os.path.basename(file_path).replace(".md", "")
            # 長すぎるタイトルを切り詰める
            if len(title) > 100:
                title = title[:97] + "..."
            # タイトルの末尾の句点「。」を削除
            title = title.rstrip("。")

        # 本文からアイコンを推測
        icon = predict_icon_from_content(content, title) if USE_ICON else None
        if icon:
            print(f"🔮 推測されたアイコン: {icon}")

        return {
            "title": title,
            "created": created,
            "updated": updated,
            "paragraphs": filtered_paragraphs,
            "images": image_filenames,
            "cover_image": cover_image,
            "icon": icon
        }

    except Exception as e:
        print(f"❌ エラー: {file_path} の解析に失敗しました。 {e}")
        sys.exit(1)

# ------------- マークダウンをNotionブロックに変換する関数 -------------
def convert_markdown_to_notion_blocks(paragraphs):
    """マークダウンテキストをNotionブロックに変換する"""
    blocks = []

    for paragraph in paragraphs:
        if paragraph == "<HORIZONTAL_LINE>":
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        elif paragraph == "<EMPTY_BLOCK>":
            blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}})
        # "--"や"---"などの罫線表現を区切り線に変換
        elif paragraph.strip() == "\\--" or paragraph.strip() == "--" or re.match(r"^-{2,}$", paragraph.strip()):
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        else:
            # 見出し（#）の処理
            heading_match = re.match(r'^(#{1,3})\s+(.+)$', paragraph)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2)

                if level == 1:
                    blocks.append({
                        "object": "block",
                        "type": "heading_1",
                        "heading_1": {"rich_text": [{"text": {"content": text}}]}
                    })
                elif level == 2:
                    blocks.append({
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {"rich_text": [{"text": {"content": text}}]}
                    })
                elif level == 3:
                    blocks.append({
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {"rich_text": [{"text": {"content": text}}]}
                    })
            # リスト項目（- または *）の処理
            elif re.match(r'^[-*]\s+(.+)$', paragraph):
                text = re.match(r'^[-*]\s+(.+)$', paragraph).group(1)
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": [{"text": {"content": text}}]}
                })
            # 番号付きリスト（1. 2. など）の処理
            elif re.match(r'^\d+\.\s+(.+)$', paragraph):
                text = re.match(r'^\d+\.\s+(.+)$', paragraph).group(1)
                blocks.append({
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {"rich_text": [{"text": {"content": text}}]}
                })
            # 引用（>）の処理
            elif re.match(r'^>\s+(.+)$', paragraph):
                text = re.match(r'^>\s+(.+)$', paragraph).group(1)
                blocks.append({
                    "object": "block",
                    "type": "quote",
                    "quote": {"rich_text": [{"text": {"content": text}}]}
                })
            # コードブロック（```）の処理
            elif re.match(r'^```(.*)$', paragraph):
                # コードブロックの開始行を検出した場合は、次の```までを一つのブロックとして処理
                # 実際の実装では複数行の処理が必要になりますが、ここでは簡略化
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"text": {"content": paragraph.replace('```', '')}}],
                        "language": "plain_text"
                    }
                })
            # 通常の段落
            else:
                # 太字（**text**）の処理
                text = paragraph
                bold_matches = re.findall(r'\*\*(.*?)\*\*', text)
                rich_text = []

                if bold_matches:
                    # 太字がある場合は、テキストを分割して適切なフォーマットを適用
                    last_end = 0
                    for match in re.finditer(r'\*\*(.*?)\*\*', text):
                        # 太字の前のテキスト
                        if match.start() > last_end:
                            rich_text.append({"text": {"content": text[last_end:match.start()]}})

                        # 太字のテキスト
                        rich_text.append({
                            "text": {"content": match.group(1)},
                            "annotations": {"bold": True}
                        })

                        last_end = match.end()

                    # 最後の太字の後のテキスト
                    if last_end < len(text):
                        rich_text.append({"text": {"content": text[last_end:]}})
                else:
                    # 太字がない場合は、テキスト全体を1つのブロックとして追加
                    rich_text = [{"text": {"content": text}}]

                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": rich_text}
                })

    return blocks

# ------------- Notionにデータをアップロードする関数 -------------
def upload_to_notion(note, max_retries=3, retry_delay=2):
    """
    Notionにノートデータをアップロードする関数
    max_retries: 最大リトライ回数
    retry_delay: リトライ間の待機時間（秒）
    """
    retries = 0
    while retries <= max_retries:
        try:
            print(f"🚀 Notionへアップロード開始: {note['title']}")

            # ページのプロパティを設定
            new_page_data = {
                "parent": {"database_id": DATABASE_ID},
                "properties": {
                    "タイトル": {"title": [{"text": {"content": note["title"]}}]},
                    "作成日": {"date": {"start": note["created"]}},
                    "更新日": {"date": {"start": note["updated"]}},
                },
                "children": []
            }

            # アイコンを設定
            if note["icon"] and USE_ICON:
                new_page_data["icon"] = {
                    "type": "emoji",
                    "emoji": note["icon"]
                }

            # 画像がある場合の処理
            if note["images"]:
                # 最初の画像をカバー画像として使用
                cover_url = generate_image_url(note["cover_image"]) if note["cover_image"] else None

                # 画像プロパティを設定（すべての画像を含める）
                if USE_IMAGE_PROPERTY:
                    image_files = []
                    for img in note["images"]:
                        img_url = generate_image_url(img)
                        image_files.append({
                            "name": img,
                            "external": {"url": img_url}
                        })

                    # Notionのデータベースに画像プロパティを設定
                    new_page_data["properties"][IMAGE_PROPERTY_NAME] = {
                        "files": image_files
                    }

                # ページのカバー画像を設定（最初の画像のみ）
                if USE_COVER_IMAGE and cover_url:
                    new_page_data["cover"] = {
                        "type": "external",
                        "external": {"url": cover_url}
                    }

            # マークダウンをNotionブロックに変換
            blocks = convert_markdown_to_notion_blocks(note["paragraphs"])
            new_page_data["children"] = blocks

            # 画像を本文内に追加
            for filename in note["images"]:
                image_url = generate_image_url(filename)
                new_page_data["children"].append({
                    "object": "block",
                    "type": "image",
                    "image": {"external": {"url": image_url}}
                })

            response = requests.post(url, headers=headers, data=json.dumps(new_page_data), timeout=30)

            # レート制限対応
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', retry_delay))
                print(f"⚠️ レート制限に達しました。{retry_after}秒後にリトライします...")
                time.sleep(retry_after)
                retries += 1
                continue

            # 成功
            if response.status_code == 200:
                print(f"✅ {note['title']} をNotionに追加できたでござる！🎉")
                return True
            # その他のエラー
            else:
                print(f"❌ {note['title']} の追加に失敗: {response.status_code}")
                print(response.text)

                # 認証エラーなど致命的なエラーの場合はすぐに終了
                if response.status_code in [401, 403]:
                    print("❌ 認証エラーが発生しました。APIキーを確認してください。")
                    sys.exit(1)

                retries += 1
                if retries <= max_retries:
                    print(f"⚠️ {retries}/{max_retries}回目のリトライを{retry_delay}秒後に行います...")
                    time.sleep(retry_delay)
                else:
                    print(f"❌ 最大リトライ回数({max_retries}回)に達しました。処理を中止します。")
                    return False

        except requests.exceptions.RequestException as e:
            print(f"❌ ネットワークエラー: {e}")
            retries += 1
            if retries <= max_retries:
                print(f"⚠️ {retries}/{max_retries}回目のリトライを{retry_delay}秒後に行います...")
                time.sleep(retry_delay)
            else:
                print(f"❌ 最大リトライ回数({max_retries}回)に達しました。処理を中止します。")
                return False
        except Exception as e:
            print(f"❌ エラー: {note['title']} のアップロードに失敗しました。 {e}")
            return False

    return False

# ------------- 進捗表示関数 -------------
def show_progress(current, total, bar_length=50):
    """進捗バーを表示する関数"""
    percent = float(current) / total
    arrow = '=' * int(round(percent * bar_length) - 1) + '>'
    spaces = ' ' * (bar_length - len(arrow))

    sys.stdout.write(f"\r📊 進捗: [{arrow}{spaces}] {int(percent * 100)}% ({current}/{total})")
    sys.stdout.flush()

    if current == total:
        sys.stdout.write('\n')

if __name__ == "__main__":
    main()