import requests
import json

# 🔹 Notion APIの設定
NOTION_API_KEY = "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"  # ① Notion APIキーをここに入力！
DATABASE_ID = "1aa2ab4c5c0e807181f6f3219236db9a"  # ② NotionのデータベースIDをここに入力！

# 🔹 Notion APIのエンドポイント
url = "https://api.notion.com/v1/pages"

# 🔹 アップロードするデータ（JSONの構造ミスを修正）
new_page_data = {
    "parent": {"database_id": DATABASE_ID},
    "properties": {
        "タイトル": {
            "title": [
                {"text": {"content": "初めてのNotion APIアップロード！"}}
            ]
        },
        "本文": {
            "rich_text": [
                {"text": {"content": "PythonからNotionに書き込めるでござる！🎉"}}
            ]
        }
    }
}

# 🔹 APIリクエストのヘッダー
headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# 🔹 Notion APIにデータを送信
response = requests.post(url, headers=headers, data=json.dumps(new_page_data))

# 🔹 レスポンスを確認
if response.status_code == 200:
    print("✅ Notionにデータを追加できたでござる！🎉")
else:
    print(f"❌ エラーが発生: {response.status_code}")
    print(response.text)