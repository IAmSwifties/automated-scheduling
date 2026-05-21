import os
import time
import json
import random
import re
import requests
from google import genai
from datetime import datetime

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
TZUYIN_CHAT_ID = os.getenv("TZUYIN_CHAT_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

TOPICS_FILE = "used_topics.json"

# ===== 題庫 =====
TOPIC_POOL = {
    "營養素日": [
        "鐵", "鈣", "維生素D", "維生素C", "鎂", "鋅", "膳食纖維",
        "Omega-3", "維生素B12", "葉酸", "鉀", "碘", "維生素A", "硒"
    ],
    "症狀觀察日": [
        "疲勞", "便秘", "脹氣", "睡不好", "頭痛", "掉髮",
        "皮膚乾燥", "眼睛乾澀", "手腳冰冷", "水腫", "注意力不集中", "口臭"
    ],
    "飲食選擇日": [
        "早餐", "外食", "手搖飲", "消夜", "超商食物",
        "泡麵", "自助餐", "早午餐", "下午茶", "運動後飲食", "素食"
    ],
    "生活習慣日": [
        "喝水", "睡眠", "久坐", "壓力", "運動",
        "3C使用", "曬太陽", "飯後散步", "間歇性斷食", "細嚼慢嚥"
    ]
}

THEMES = [
    {
        "day": "週二",
        "name": "營養素日",
        "description": "聚焦在一個關鍵營養素"
    },
    {
        "day": "週三",
        "name": "症狀觀察日",
        "description": "聚焦在一個身體訊號或不適症狀"
    },
    {
        "day": "週四",
        "name": "飲食選擇日",
        "description": "聚焦在每天會面對的飲食選擇"
    },
    {
        "day": "週五",
        "name": "生活習慣日",
        "description": "聚焦在一個日常行為習慣"
    },
]

# ===== 題庫紀錄管理 =====
def load_used_topics():
    try:
        with open(TOPICS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # 第一次執行時自動建立
        data = {theme["name"]: [] for theme in THEMES}
        save_all_topics(data)
        return data

def save_all_topics(data):
    with open(TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def pick_topic(theme_name, used_data):
    pool = TOPIC_POOL[theme_name]
    used_list = used_data.get(theme_name, [])
    remaining = [t for t in pool if t not in used_list]

    # 用完一輪就重置
    if not remaining:
        print(f"  🔄 {theme_name} 題庫已用完，重置！")
        used_data[theme_name] = []
        remaining = pool

    topic = random.choice(remaining)
    used_data[theme_name].append(topic)
    return topic

# ===== AI 生成 =====
def generate_content(theme, topic):
    client = genai.Client(api_key=GEMINI_KEY)

    prompt = f"""
    你是一位健康知識的社群內容創作者，專門為一般大眾製作淺顯易懂的衛教內容。

    今天的主題日是「{theme['name']}」，指定主題是「{topic}」。

    請生成以下兩個部分：

    【題目】
    一個吸引人的問題，讓觀眾想知道答案（一句話以及四個選項即可）

    【逐字稿】
    一段約 1 到 2 分鐘的短片逐字稿（約 200 到 300 字），由真人對著鏡頭說話。
    要求：
    - 語氣輕鬆自然，像朋友聊天
    - 開頭用題目勾住觀眾
    - 中間給出清楚的知識點
    - 結尾有一個簡單的行動建議
    - 使用繁體中文
    - 不要使用 Markdown 語法（不要 ** # 等符號）

    請直接輸出內容，不要有任何前言或說明。
    """

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-3-flash-preview',
                contents=prompt
            )
            if not response.text:
                raise ValueError("Gemini 回傳空值")
            return response.text
        except Exception as e:
            print(f"第 {attempt + 1} 次嘗試失敗：{e}")
            if attempt < max_retries - 1:
                print("等待 10 秒後重試...")
                time.sleep(10)
            else:
                return "AI 生成失敗，請稍後再試 😭"

# ===== 送出 Telegram =====
def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"

    # for chat_id in [TG_CHAT_ID, TZUYIN_CHAT_ID]:
    for chat_id in [TG_CHAT_ID]:
        if not chat_id:
            continue
        payload = {
            "chat_id": chat_id,
            "text": text,
        }
        response = requests.post(url, json=payload)
        print(f"Telegram 狀態碼 (chat_id={chat_id}): {response.status_code}")

# ===== 主程式 =====
if __name__ == "__main__":
    print("開始生成本週主題內容...")
    week = datetime.now().strftime('%Y 第 %W 週')

    used_data = load_used_topics()

    send_to_telegram(f"測試中...")
    send_to_telegram(f"📅 {week} 主題內容已生成！")
    time.sleep(1)

    for theme in THEMES:
        topic = pick_topic(theme['name'], used_data)
        print(f"\n正在生成 {theme['day']} {theme['name']}（主題：{topic}）...")

        content = generate_content(theme, topic)

        message = (
            f"{'='*30}\n"
            f"{theme['day']}｜{theme['name']}｜{topic}\n"
            f"{'='*30}\n\n"
            f"{content}"
        )
        send_to_telegram(message)
        print(f"✅ {theme['name']} 已送出！")
        time.sleep(2)

    # 所有主題跑完才統一儲存，避免中途失敗造成紀錄不一致
    save_all_topics(used_data)
    print("\n所有內容生成完畢！")
