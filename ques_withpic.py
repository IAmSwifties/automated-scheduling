import base64
import os
import time
import json
import random
import re
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from google import genai
from openai import OpenAI
from datetime import datetime

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
TZUYIN_CHAT_ID = os.getenv("TZUYIN_CHAT_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

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
    {"day": "週二", "name": "營養素日"},
    {"day": "週三", "name": "症狀觀察日"},
    {"day": "週四", "name": "飲食選擇日"},
    {"day": "週五", "name": "生活習慣日"},
]

# ===== 題庫紀錄管理 =====
def load_used_topics():
    try:
        with open(TOPICS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
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
    if not remaining:
        print(f"  🔄 {theme_name} 題庫已用完，重置！")
        used_data[theme_name] = []
        remaining = pool
    topic = random.choice(remaining)
    used_data[theme_name].append(topic)
    return topic

# ===== AI 生成題目＋選項＋逐字稿 =====
def generate_content(theme, topic):
    client = genai.Client(api_key=GEMINI_KEY)

    prompt = f"""
    你是一位健康知識的社群內容創作者，專門為一般大眾製作淺顯易懂的衛教內容。

    今天的主題日是「{theme['name']}」，指定主題是「{topic}」。

    請生成以下三個部分，並嚴格按照以下格式輸出，不要有任何其他說明：

    【題目】
    一個吸引人的問題（一句話）

    【選項】
    A. 選項一
    B. 選項二
    C. 選項三
    D. 選項四

    【答案】
    正確答案是（A/B/C/D）：簡短說明原因

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
                print("等待 30 秒後重試...")
                time.sleep(30)
            else:
                return None

# ===== 解析 AI 回傳內容 =====
def parse_content(text):
    question = ""
    options = []
    answer = ""
    script = ""

    q_match = re.search(r'【題目】\n(.+?)(?=\n【)', text, re.DOTALL)
    if q_match:
        question = q_match.group(1).strip()

    o_match = re.search(r'【選項】\n(.+?)(?=\n【)', text, re.DOTALL)
    if o_match:
        options = [line.strip() for line in o_match.group(1).strip().split('\n') if line.strip()]

    a_match = re.search(r'【答案】\n(.+?)(?=\n【)', text, re.DOTALL)
    if a_match:
        answer = a_match.group(1).strip()

    s_match = re.search(r'【逐字稿】\n(.+?)$', text, re.DOTALL)
    if s_match:
        script = s_match.group(1).strip()

    return question, options, answer, script

# ===== DALL-E 3 生成插圖 =====
def generate_illustration(topic):
    client = OpenAI(api_key=OPENAI_KEY)
    prompt = f"A cute flat illustration style image related to '{topic}' in the context of health and wellness. Minimalist, pastel colors, no text, simple background, friendly and approachable style."
    try:
        result = client.images.generate(
            model="gpt-image-2",
            prompt=prompt
        )
        image_base64 = result.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)
        return Image.open(BytesIO(image_bytes))
    except Exception as e:
        print(f"  ⚠️ 插圖生成失敗：{e}")
        return None

def create_image_card(question, options, theme_name, topic, illustration):
    card_width = 1080
    card_height = 1350  # 字變大內容變多，高度拉高
    padding = 60
    bg_color = "#FFF8F0"
    header_color = "#FF8C69"
    text_color = "#333333"
    option_bg_color = "#FFFFFF"
    option_border_color = "#FFB347"

    card = Image.new("RGB", (card_width, card_height), bg_color)
    draw = ImageDraw.Draw(card)

    font_paths_bold = [
        "/tmp/NotoSansTC.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJKtc-Bold.otf",
    ]
    font_paths_regular = [
        "/tmp/NotoSansTC.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJKtc-Regular.otf",
    ]

    def find_font(paths, size):
        for path in paths:
            if os.path.exists(path):
                print(f"  ✅ 找到字型：{path}")
                return ImageFont.truetype(path, size)
        print("  ⚠️ 找不到中文字型，使用預設字型")
        return ImageFont.load_default()

    font_title = find_font(font_paths_bold, 52)    # 42 → 52
    font_question = find_font(font_paths_regular, 46)  # 36 → 46
    font_option = find_font(font_paths_regular, 42)    # 32 → 42
    font_tag = find_font(font_paths_bold, 36)      # 28 → 36

    # Header（高度加高配合大字）
    draw.rectangle([(0, 0), (card_width, 150)], fill=header_color)
    draw.text((padding, 45), f"{theme_name}｜{topic}", font=font_title, fill="#FFFFFF")

    # 插圖
    y_cursor = 160
    if illustration:
        illus_size = 400
        illustration = illustration.resize((illus_size, illus_size))
        illus_x = (card_width - illus_size) // 2
        card.paste(illustration, (illus_x, y_cursor))
        y_cursor += illus_size + 30

    # 自動換行題目
    max_width = card_width - padding * 2
    line = ""
    lines = []
    for char in question:
        test_line = line + char
        bbox = draw.textbbox((0, 0), test_line, font=font_question)
        if bbox[2] > max_width:
            lines.append(line)
            line = char
        else:
            line = test_line
    if line:
        lines.append(line)

    for line in lines:
        draw.text((padding, y_cursor), line, font=font_question, fill=text_color)
        y_cursor += 60  # 48 → 60 行距加大

    y_cursor += 24

    # 選項（方框加高配合大字）
    for option in options:
        opt_height = 90  # 70 → 90
        draw.rounded_rectangle(
            [(padding, y_cursor), (card_width - padding, y_cursor + opt_height)],
            radius=16, fill=option_bg_color, outline=option_border_color, width=2
        )
        draw.text((padding + 20, y_cursor + 22), option, font=font_option, fill=text_color)
        y_cursor += opt_height + 20  # 間距也加大

    return card

# ===== 送出 Telegram =====
def send_image_to_telegram(image, caption):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    # for chat_id in [TG_CHAT_ID]:
    for chat_id in [TG_CHAT_ID, TZUYIN_CHAT_ID]:
        if not chat_id:
            continue
        files = {"photo": ("card.png", img_byte_arr, "image/png")}
        data = {"chat_id": chat_id, "caption": caption}
        response = requests.post(url, data=data, files=files)
        img_byte_arr.seek(0)
        print(f"Telegram 圖片狀態碼 (chat_id={chat_id}): {response.status_code}")

def send_text_to_telegram(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    # for chat_id in [TG_CHAT_ID]:
    for chat_id in [TG_CHAT_ID, TZUYIN_CHAT_ID]:
        if not chat_id:
            continue
        payload = {"chat_id": chat_id, "text": text}
        response = requests.post(url, json=payload)
        print(f"Telegram 文字狀態碼 (chat_id={chat_id}): {response.status_code}")

# ===== 主程式 =====
if __name__ == "__main__":
    print("開始生成本週主題內容...")
    week = datetime.now().strftime('%Y 第 %W 週')

    used_data = load_used_topics()
    send_text_to_telegram(f"📅 {week} 主題內容已生成！")
    time.sleep(1)

    for theme in THEMES:
        topic = pick_topic(theme['name'], used_data)
        print(f"\n正在生成 {theme['day']} {theme['name']}（主題：{topic}）...")

        raw_content = generate_content(theme, topic)
        if not raw_content:
            send_text_to_telegram(f"⚠️ {theme['day']} {theme['name']} 生成失敗，請稍後再試")
            continue

        question, options, answer, script = parse_content(raw_content)

        print("  🎨 正在生成插圖...")
        illustration = generate_illustration(topic)

        print("  🖼️ 正在合成圖卡...")
        card = create_image_card(question, options, theme['name'], topic, illustration)

        caption = f"{theme['day']}｜{theme['name']}｜{topic}"
        send_image_to_telegram(card, caption)
        time.sleep(1)

        message = (
            f"{'='*30}\n"
            f"📝 答案\n{answer}\n\n"
            f"🎬 逐字稿\n{script}"
        )
        send_text_to_telegram(message)
        print(f"✅ {theme['name']} 已送出！")
        time.sleep(60)

    save_all_topics(used_data)
    print("\n所有內容生成完畢！")
