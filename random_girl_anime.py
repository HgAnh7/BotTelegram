import os
import time
import telebot
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Hàm dùng chung để xử lý API và gửi video
def fetch_and_send_video(message, api_url):
    try:
        response = requests.get(api_url, timeout=10).json()
    except:
        time.sleep(5)  # đợi 3 giây và thử lại
        try:
            response = requests.get(api_url, timeout=85).json()
        except Exception as e:
            bot.reply_to(message, "Lỗi API (sau khi thử lại)!")
            return

    video_url = response.get('video_url')
    if not video_url:
        bot.reply_to(message, "API không trả về video_url hợp lệ.")
        return

    try:
        bot.send_video(
            chat_id=message.chat.id,
            video=video_url,
            reply_to_message_id=message.message_id,
            timeout=20
        )
    except Exception as e:
        bot.reply_to(message, f"Link lỗi: {video_url}")
# Xử lý lệnh /anime
@bot.message_handler(commands=['anime'])
def handle_anime(message):
    fetch_and_send_video(message, "https://api-anime-0rz7.onrender.com/api/anime")

# Xử lý lệnh /girl
@bot.message_handler(commands=['girl'])
def handle_girl(message):
    fetch_and_send_video(message, "https://api-girl.onrender.com/api/girl")

# Khởi chạy bot
print("Bot random video gái và anime đang chạy...")
bot.infinity_polling()