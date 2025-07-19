import os
import time
import telebot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = "-1002795920037"  # ID kênh

bot = telebot.TeleBot(TOKEN)

def send_images():
	with open("urls.txt", "r") as f:
		urls = [line.strip() for line in f if line.strip()]

	for url in urls:
		try:
			if url.lower().endswith(".gif"):
				bot.send_animation(CHANNEL_ID, url)
			else:
				bot.send_photo(CHANNEL_ID, url)
		except Exception as e:
			error_msg = f"⚠️ Không gửi được:\n{url}\nLý do: {e}"
			bot.send_message(CHANNEL_ID, error_msg)
		time.sleep(5)

if __name__ == "__main__":
	send_images()
