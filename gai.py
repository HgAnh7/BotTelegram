import os
import time
import telebot
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['girl'])
def handle_buff(message):
    try:
        api_url = "https://api-l8y6.onrender.com/api/random-video"
        response = requests.get(api_url, timeout=5).json()
        video_url = response['video_url']

        bot.send_video(
            chat_id=message.chat.id,
            video=video_url,
            reply_to_message_id=message.message_id
        )

    except Exception as e:
        bot.reply_to(message, f"Lỗi khi gọi API: {str(e)}")

# Khởi chạy bot
print("Bot random video gái đang chạy...")
bot.infinity_polling()
