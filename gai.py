import os
import logging
import telebot
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Thiết lập logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

@bot.message_handler(commands=['girl'])
def handle_girl(message):
    try:
        api_url = "https://api-l8y6.onrender.com/api/random-video"
        response = requests.get(api_url, timeout=5).json()
        video_url = response['video_url']

        try:
            bot.send_video(
                chat_id=message.chat.id,
                video=video_url,
                reply_to_message_id=message.message_id
            )
        except Exception as send_err:
            logging.error(f"Lỗi khi gửi video: {send_err}")
            bot.reply_to(
                message,
                f"Link lỗi: {video_url}"
            )

    except Exception as err:
        logging.error(f"[handle_girl] Lỗi: {err}")
        return

# Khởi chạy bot
print("Bot random video gái đang chạy...")
bot.infinity_polling()
