# @HgAnh7
import os
import time
import telebot
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['fl'])
def handle_buff(message):
    try:
        # Tách username từ tin nhắn
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Vui lòng nhập username. Ví dụ: /fl hganh_7")
            return
        
        username = args[1]

        # Gọi API có username
        api_url = f"https://anhcode.click/anhcode/api/fltt.php?key=anhcode&username={username}"
        response = requests.get(api_url)
        response.raise_for_status()

        data = response.json()

        if data.get("success"):
            reply = f"{data['message']}\n\n"
        else:
            reply = f"Lỗi: {data.get('message', 'Không rõ lỗi')}"

        bot.reply_to(message, reply, parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"Lỗi khi gọi API: {str(e)}")

# Khởi chạy bot
print("Bot fltik đang chạy...")
bot.infinity_polling()