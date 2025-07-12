import os
import time
import telebot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = "-1002795920037"  # hoặc -100xxxxxxxxxx

bot = telebot.TeleBot(TOKEN)

def send_images():
    with open("cosplay_links.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        try:
            bot.send_photo(CHANNEL_ID, url)
        except:
            pass
        time.sleep(3)

send_images()
