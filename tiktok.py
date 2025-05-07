import os
import re
import telebot
import requests
from datetime import datetime

# Token Telegram Bot
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_bot = telebot.TeleBot(BOT_TOKEN)

# URL API TikWM
TIKWM_API_URL = "https://www.tikwm.com/api/"

def format_count(value):
    try:
        num = int(value)
        if num < 1000:
            return f"{num:,}".replace(",", ".")
        elif num < 1000000:
            return f"{num / 1000:.1f}".rstrip('0').rstrip('.') + "K"
        else:
            return f"{num / 1000000:.2f}".rstrip('0').rstrip('.') + " triệu"
    except (ValueError, TypeError):
        return str(value)

def strip_emojis(content):
    emoji_regex = re.compile(
        "[" u"\U0001F600-\U0001F64F" u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF" u"\U0001F700-\U0001F77F"
        u"\U0001F780-\U0001F7FF" u"\U0001F800-\U0001F8FF"
        u"\U0001F900-\U0001F9FF" u"\U0001FA00-\U0001FA6F"
        u"\U0001FA70-\U0001FAFF" u"\U00002700-\U000027BF"
        u"\U00002600-\U000026FF" "]+", flags=re.UNICODE
    )
    return emoji_regex.sub(r'', content)

@telegram_bot.message_handler(commands=['tiktok'])
def fetch_tiktok_data(message):
    try:
        command_args = message.text.split(" ", 1)
        if len(command_args) < 2:
            telegram_bot.reply_to(message, "• Vui lòng gửi link TikTok sau lệnh /tiktok")
            return

        tiktok_url = command_args[1]
        query_params = {'url': tiktok_url}
        response = requests.get(TIKWM_API_URL, params=query_params).json()

        if response.get("code") != 0:
            telegram_bot.reply_to(message, "• Không thể lấy dữ liệu video. Vui lòng thử lại!")
            return

        data = response.get("data", {})

        caption = data.get("title", "Không có tiêu đề")
        creator = data.get("author", {}).get("nickname", "Không rõ")
        video_duration = data.get("duration", 0)
        like_count = data.get("digg_count", 0)
        comment_count = data.get("comment_count", 0)
        share_count = data.get("share_count", 0)
        view_count = data.get("play_count", 0)
        is_verified = "Đã xác minh" if data.get("author", {}).get("verified", False) else "Chưa xác minh"
        tiktok_id = data.get("author", {}).get("unique_id", "Không có ID")
        follow_count = data.get("author", {}).get("following_count", 0)
        audio_link = data.get("music", {}).get("play_url", "Không có nhạc nền")

        summary_text = (
            f"🎥 [**THÔNG TIN VIDEO**]\n"
            f"━━━━━━━━━━━━━━\n"
            f"👁 Lượt xem: {format_count(view_count)}\n"
            f"❤️ Lượt thích: {format_count(like_count)}\n"
            f"💬 Bình luận: {format_count(comment_count)}\n"
            f"🔁 Chia sẻ: {format_count(share_count)}\n"
            f"👤 Người đăng: {creator}\n"
            f"📌 Caption: {strip_emojis(caption)}\n"
            f"⏳ Thời lượng: {video_duration} giây\n"
            f"🎵 Nhạc nền: {audio_link}\n"
            f"\n━━━━━━━━━━━━━━\n"
            f"🎭 **THÔNG TIN KÊNH**\n"
            f"🆔 TikTok ID: {tiktok_id}\n"
            f"✅ Xác minh: {is_verified}\n"
            f"👥 Đang theo dõi: {format_count(follow_count)}\n"
        )

        telegram_bot.reply_to(message, summary_text)

    except Exception as error:
        telegram_bot.reply_to(message, f"• Lỗi: {error}")

# ✅ Duy nhất dòng này in ra terminal
print("Bot TikTok đang hoạt động...")
telegram_bot.polling()
