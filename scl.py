# Share by Hoang Anh
# t.me/HgAnh_7
# Update date: 4/24/2025

import re
import json
import time
import random
import telebot
import requests

soundcloud_data = {}
PLATFORM = "soundcloud"
API_BASE = "https://api-v2.soundcloud.com"
CONFIG_PATH = "config.json"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]
ACCEPT_LANGUAGES = ["en-US,en;q=0.9", "fr-FR,fr;q=0.9", "es-ES,es;q=0.9", "de-DE,de;q=0.9", "zh-CN,zh;q=0.9"]

# TÔN TRỌNG TÁC GIẢ, KHÔNG XÓA DÒNG NÀY
# SOURCE API SOUNDCLOUD SEARCH AND DOWNLOAD BY HOANG ANH

token = os.getenv("TELEGRAM_TOKEN")
if not token:
    raise ValueError("Missing TELEGRAM_TOKEN in environment variables")

bot = telebot.TeleBot(token)

def get_random_element(array):
    return random.choice(array)

def get_headers():
    return {
        "User-Agent": get_random_element(USER_AGENTS),
        "Accept-Language": get_random_element(ACCEPT_LANGUAGES),
        "Referer": "https://soundcloud.com/",
        "Upgrade-Insecure-Requests": "1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }

def get_client_id():
    try:
        import os
        config = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            if config.get('client_id'):
                return config['client_id']

        response = requests.get("https://soundcloud.com/", headers=get_headers())
        response.raise_for_status()
        script_tags = re.findall(r'<script crossorigin src="([^"]+)"', response.text)
        script_urls = [url for url in script_tags if url.startswith("https")]

        if not script_urls:
            raise ValueError("No script URLs found")

        script_response = requests.get(script_urls[-1], headers=get_headers())
        script_response.raise_for_status()
        client_id_match = re.search(r',client_id:"([^"]+)"', script_response.text)
        if not client_id_match:
            raise ValueError("Client ID not found in script")

        client_id = client_id_match.group(1)

        config['client_id'] = client_id
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)

        return client_id
    except Exception as e:
        print(f"Error fetching client ID: {e}")
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            return config.get('client_id', 'W00nmY7TLer3uyoEo1sWK3Hhke5Ahdl9')
        return 'W00nmY7TLer3uyoEo1sWK3Hhke5Ahdl9'

def get_music_info(question, limit=10):
    try:
        client_id = get_client_id()
        response = requests.get(
            f"{API_BASE}/search/tracks",
            params={
                "q": question,
                "variant_ids": "",
                "facet": "genre",
                "client_id": client_id,
                "limit": limit,
                "offset": 0,
                "linked_partitioning": 1,
                "app_locale": "en",
            },
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching music info: {e}")
        return None

def get_music_stream_url(track):
    try:
        client_id = get_client_id()
        api_url = f"{API_BASE}/resolve?url={track['permalink_url']}&client_id={client_id}"
        response = requests.get(api_url, headers=get_headers())
        response.raise_for_status()
        data = response.json()

        progressive_url = next(
            (t['url'] for t in data.get('media', {}).get('transcodings', []) if t['format']['protocol'] == 'progressive'),
            None
        )
        if not progressive_url:
            raise ValueError("No progressive transcoding URL found")

        stream_response = requests.get(
            f"{progressive_url}?client_id={client_id}&track_authorization={data.get('track_authorization', '')}",
            headers=get_headers()
        )
        stream_response.raise_for_status()
        return stream_response.json()['url']
    except Exception as e:
        print(f"Error getting music stream URL: {e}")
        return None

@bot.message_handler(commands=['scl'])
def soundcloud(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "🚫 Vui lòng nhập tên bài hát muốn tìm kiếm.\nVí dụ: /scl Tên bài hát", parse_mode='HTML')
        return
    keyword = args[1].strip()
    music_info = get_music_info(keyword)
    if not music_info or not music_info.get('collection') or len(music_info['collection']) == 0:
        bot.reply_to(message, "🚫 Không tìm thấy bài hát nào khớp với từ khóa.", parse_mode='HTML')
        return
    tracks = [track for track in music_info['collection'] if track.get('artwork_url')]
    if not tracks:
        bot.reply_to(message, "🚫 Không tìm thấy bài hát nào có hình ảnh.", parse_mode='HTML')
        return
    response_text = "<b>🎵 Kết quả tìm kiếm trên SoundCloud</b>\n\n"
    for i, track in enumerate(tracks):
        response_text += f"<b>{i + 1}. {track['title']}</b>\n"
        response_text += f"👤 Nghệ sĩ: {track['user']['username']}\n"
        response_text += f"📊 Lượt nghe: {track['playback_count']:,} | Thích: {track['likes_count']:,}\n"
        response_text += f"🆔 ID: {track['id']}\n\n"
    response_text += "<b>💡 Trả lời tin nhắn này bằng số từ 1-10 để chọn bài hát!</b>"
    sent = bot.reply_to(message, response_text, parse_mode='HTML')
    soundcloud_data[sent.message_id] = {
        "user_id": message.from_user.id,
        "tracks": tracks
    }

@bot.message_handler(func=lambda msg: msg.reply_to_message and msg.reply_to_message.message_id in soundcloud_data)
def handle_soundcloud_selection(msg):
    reply_id = msg.reply_to_message.message_id
    if reply_id not in soundcloud_data:
        return
    user_id = msg.from_user.id
    data = soundcloud_data[reply_id]
    if user_id != data['user_id']:
        return
    text = msg.text.strip().lower()
    try:
        index = int(text.split()[0]) - 1
        if index < 0 or index >= len(data["tracks"]):
            bot.reply_to(msg, "🚫 Số không hợp lệ. Hãy nhập số từ 1-10.", parse_mode='HTML')
            return
    except (ValueError, IndexError):
        bot.reply_to(msg, "🚫 Vui lòng nhập số từ 1-10.", parse_mode='HTML')
        return
    track = data["tracks"][index]
    bot.reply_to(msg, f"🧭 Đang tải: {track['title']}", parse_mode='HTML')
    audio_url = get_music_stream_url(track)
    thumbnail_url = track.get('artwork_url', '').replace("-large", "-t500x500")
    if not audio_url or not thumbnail_url:
        bot.reply_to(msg, "🚫 Không tìm thấy nguồn audio hoặc thumbnail.", parse_mode='HTML')
        return
    caption = f"<b>🎵 {track['title']}</b>\n"
    caption += f"👤 Nghệ sĩ: {track['user']['username']}\n"
    caption += f"📊 Lượt nghe: {track['playback_count']:,} | Thích: {track['likes_count']:,}\n"
    caption += f"🎧 Nguồn: SoundCloud\n"
    caption += f"🎉 Chúc bạn thưởng thức âm nhạc vui vẻ!"
    try:
        bot.delete_message(msg.chat.id, reply_id)
    except:
        pass
    bot.send_photo(msg.chat.id, thumbnail_url, caption=caption, parse_mode='HTML')
    bot.send_audio(msg.chat.id, audio_url, title=track['title'], performer=track['user']['username'])
    del soundcloud_data[reply_id]

def main():
    print("Bot đang hoạt động...")
    bot.polling(none_stop=True)

if __name__ == "__main__":
    main()
