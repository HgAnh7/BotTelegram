import os
import telebot
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['girl'])
def handle_girl(message):
    try:
        api_url = "https://api-l8y6.onrender.com/api/random-video"
        response = requests.get(api_url, timeout=10).json()
        video_url = response['video_url']
        
        try:
            bot.send_video(
                chat_id=message.chat.id,
                video=video_url,
                reply_to_message_id=message.message_id,
                timeout=20
            )
        except:
            bot.reply_to(message, f"Link video bị lỗi (cần xóa khỏi API): {video_url}")
            
    except:  # Bắt mọi lỗi từ API
        bot.reply_to(message, "❌ Lỗi khi lấy video từ API!")

# Khởi chạy bot
print("Bot random video gái đang chạy...")
bot.infinity_polling()
