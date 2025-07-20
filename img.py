import os
import time
import telebot

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

def send_images(channel_id):
    with open("urls.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        try:
            if url.lower().endswith(".gif"):
                bot.send_animation(channel_id, url)
            else:
                bot.send_photo(channel_id, url)
        except Exception as e:
            error_msg = f"⚠️ Không gửi được:\n{url}\nLý do: {e}"
            bot.send_message(channel_id, error_msg)
        time.sleep(5)

@bot.message_handler(commands=['img'])
def handle_img(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❗ Bạn cần nhập kèm ID kênh.\nVí dụ: `/img -1001234567890`", parse_mode="Markdown")
        return

    channel_id = args[1]
    bot.reply_to(message, f"Đang gửi ảnh vào kênh `{channel_id}`...", parse_mode="Markdown")
    send_images(channel_id)

if __name__ == "__main__":
    print("Bot đang chạy...")
    bot.infinity_polling()
