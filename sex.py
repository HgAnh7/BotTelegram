import os
import telebot
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['sex'])
def handle_sex(message):
    try:
        # Lấy video URL
        api_url = "https://api-hganh7.onrender.com/api/sex"
        response = requests.get(api_url, timeout=10).json()
        video_url = response['video_url']
        
        try:
            # Gửi video
            bot.send_video(
                chat_id=message.chat.id,
                video=video_url,
                reply_to_message_id=message.message_id,
                timeout=20
            )
        except:
            # Lỗi gửi video - URL bị lỗi
            bot.reply_to(message, f"Link lỗi: {video_url}")
            
    except:
        # Lỗi gọi API
        bot.reply_to(message, "Lỗi API!")

# Khởi chạy bot
print("Bot random video sex đang chạy...")
bot.infinity_polling()