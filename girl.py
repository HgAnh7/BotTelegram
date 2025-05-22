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
        
        bot.send_video(
            chat_id=message.chat.id,
            video=video_url,
            reply_to_message_id=message.message_id,
            timeout=20
        )
            
    except:
        if 'video_url' in locals():
            bot.reply_to(message, f"Link lỗi: {video_url}")
        else:
            bot.reply_to(message, "Lỗi API!")

# Khởi chạy bot
print("Bot random video gái đang chạy...")
bot.infinity_polling()