import os
import telebot
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Hàm dùng chung để xử lý API và gửi video
def fetch_and_send_video(message, api_url):
    try:
        response = requests.get(api_url, timeout=20).json()
        video_url = response['video_url']
        
        try:
            bot.send_video(
                chat_id=message.chat.id,
                video=video_url,
                reply_to_message_id=message.message_id,
                timeout=20
            )
        except:
            bot.reply_to(message, f"Link lỗi: {video_url}")
    except:
        bot.reply_to(message, "Lỗi API!")

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