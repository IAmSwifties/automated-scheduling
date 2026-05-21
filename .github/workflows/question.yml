import os
import time
from google import genai
from datetime import datetime
import requests

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TZUYIN_CHAT_ID = os.getenv("TZUYIN_CHAT_ID")

THEMES = [
    {
        "day": "週二",
        "name": "營養素日",
        "description": "聚焦在一個關鍵營養素，例如：鐵、維生素D、鎂、膳食纖維"
    },
    {
        "day": "週三",
        "name": "症狀觀察日",
        "description": "聚焦在一個身體訊號，例如：疲勞、便秘、脹氣、睡不好"
    },
    {
        "day": "週四",
        "name": "飲食選擇日",
        "description": "聚焦在每天會面對的飲食選擇，例如：早餐、外食、手搖飲"
    },
    {
        "day": "週五",
        "name": "生活習慣日",
        "description": "聚焦在一個日常行為，例如：喝水、睡眠、久坐、壓力管理"
    },
]

def generate_content(theme):
    client = genai.Client(api_key=GEMINI_KEY)

    prompt = f"""
    你是一位健康知識的社群內容創作者，專門為一般大眾製作淺顯易懂的衛教內容。

    今天的主題日是「{theme['name']}」。
    主題說明：{theme['description']}

    請自行選定一個具體主題（例如：主題是「營養素日」就選一個具體的營養素），然後生成以下內容：

    【題目】
    一個吸引人的問題，讓觀眾想知道答案（一句話即可）

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
            return response.text
        except Exception as e:
            print(f"第 {attempt + 1} 次嘗試失敗：{e}")
            if attempt < max_retries - 1:
                print("等待 10 秒後重試...")
                time.sleep(10)
            else:
                return "AI 生成失敗，請稍後再試 😭"

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
    }
    response = requests.post(url, json=payload)
    payload = {
        "chat_id": TZUYIN_CHAT_ID,
        "text": text,
    }
    response = requests.post(url, json=payload)
    print(f"Telegram 狀態碼: {response.status_code}")

if __name__ == "__main__":
    print("開始生成本週主題內容...")
    week = datetime.now().strftime('%Y 第 %W 週')

    # 送出標題訊息
    send_to_telegram(f"📅 {week} 主題內容已生成！")
    time.sleep(1)

    for theme in THEMES:
        print(f"\n正在生成 {theme['day']} {theme['name']}...")
        content = generate_content(theme)

        message = f"{'='*30}\n{theme['day']}｜{theme['name']}\n{'='*30}\n\n{content}"
        send_to_telegram(message)

        print(f"✅ {theme['name']} 已送出！")
        time.sleep(2)  # 避免 Telegram 頻率限制

    print("\n所有內容生成完畢！")
