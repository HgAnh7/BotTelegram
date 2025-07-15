import os
import time
import telebot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = "-1002795920037"  # ID kênh

bot = telebot.TeleBot(TOKEN)

def send_images():
    with open("cosplay_links.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        try:
            bot.send_photo(CHANNEL_ID, url)
        except Exception as e:
            print(f"Lỗi gửi ảnh: {e}")
        time.sleep(5)

@bot.message_handler(commands=['img'])
def handle_img(message):
    # Đảm bảo lệnh chỉ xử lý khi được gửi từ kênh (channel)
    if str(message.chat.id) == CHANNEL_ID:
        send_images()

if __name__ == "__main__":
    print("Bot đang chạy...")
    bot.infinity_polling()