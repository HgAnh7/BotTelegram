import io
import os
import re
import json
import time
import random
import telebot
import requests
from telebot import types

scl_data = {}
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
# SOURCE API SOUNDCLOUD SEARCH AND DOWNLOAD BY HOANGANH

token = os.getenv("TELEGRAM_TOKEN")
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
    
    # Tạo response text
    response_text = "<b>🎵 Kết quả tìm kiếm trên SoundCloud</b>\n\n"
    for i, track in enumerate(tracks):
        response_text += f"<b>{i + 1}. {track['title']}</b>\n"
        response_text += f"👤 Nghệ sĩ: {track['user']['username']}\n"
        response_text += f"📊 Lượt nghe: {track['playback_count']:,} | Thích: {track['likes_count']:,}\n\n"
    
    response_text += "<b>💡 Chọn số bài hát bạn muốn tải!</b>"
    
    # Tạo inline keyboard
    markup = types.InlineKeyboardMarkup(row_width=5)
    buttons = []
    for i in range(len(tracks)):
        button = types.InlineKeyboardButton(
            text=str(i + 1), 
            callback_data=f"scl_{message.from_user.id}_{i}"
        )
        buttons.append(button)
    
    markup.add(*buttons)
    
    # Gửi message với inline keyboard
    sent = bot.reply_to(message, response_text, parse_mode='HTML', reply_markup=markup)
    
    # Lưu data cho callback
    scl_data[f"{message.from_user.id}"] = {
        "tracks": tracks,
        "message_id": sent.message_id
    }

@bot.callback_query_handler(func=lambda call: call.data.startswith('scl_'))
def handle_soundcloud_callback(call):
    try:
        # Parse callback data
        parts = call.data.split('_')
        user_id = int(parts[1])
        track_index = int(parts[2])
        
        # Kiểm tra quyền truy cập
        if call.message.from_user.id != user_id:
            bot.answer_callback_query(call.id, "❌ Bạn không có quyền sử dụng nút này!", show_alert=True)
            return
        
        # Kiểm tra data tồn tại
        if str(user_id) not in scl_data:
            bot.answer_callback_query(call.id, "❌ Dữ liệu đã hết hạn!", show_alert=True)
            return
        
        data = scl_data[str(user_id)]
        tracks = data["tracks"]
        
        # Kiểm tra index hợp lệ
        if track_index >= len(tracks):
            bot.answer_callback_query(call.id, "❌ Lựa chọn không hợp lệ!", show_alert=True)
            return
        
        track = tracks[track_index]
        
        # Answer callback query
        bot.answer_callback_query(call.id, f"🎵 Đang tải: {track['title']}")
        
        # Edit message to show loading
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🧭 Đang tải: <b>{track['title']}</b>\n👤 Nghệ sĩ: {track['user']['username']}\n\n⏳ Vui lòng chờ...",
            parse_mode='HTML'
        )
        
        # Get audio URL and thumbnail
        audio_url = get_music_stream_url(track)
        thumbnail_url = track.get('artwork_url', '').replace("-large", "-t500x500")
        
        if not audio_url or not thumbnail_url:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="🚫 Không tìm thấy nguồn audio hoặc thumbnail.",
                parse_mode='HTML'
            )
            return
        
        caption = f"""<blockquote expandable>⭔───────────────⭓
 <b>{track['title']}</b>
 » <b>Nghệ sĩ:</b> {track['user']['username']}
 » <b>Lượt nghe:</b> {track['playback_count']:,} | <b>Lượt thích:</b> {track['likes_count']:,}
 » <b>Nguồn:</b> SoundCloud 🎶 
⭓───────────────⭔</blockquote>"""
        
        # Download and send audio
        try:
            resp = requests.get(audio_url, stream=True)
            resp.raise_for_status()
            audio_bytes = resp.content
            audio_buffer = io.BytesIO(audio_bytes)
            audio_buffer.name = f"{track['title']}.mp3"
            
            # Send photo and audio
            bot.send_photo(call.message.chat.id, thumbnail_url, caption=caption, parse_mode='HTML')
            bot.send_audio(
                chat_id=call.message.chat.id, 
                audio=audio_buffer, 
                title=track['title'], 
                performer=track['user']['username']
            )
            
            # Delete the search message
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            
            # Clean up data
            if str(user_id) in scl_data:
                del scl_data[str(user_id)]
                
        except Exception as e:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"🚫 Lỗi khi tải nhạc: {str(e)}",
                parse_mode='HTML'
            )
            
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Có lỗi xảy ra: {str(e)}", show_alert=True)
        print(f"Error in callback handler: {e}")

def main():
    print("Bot scl đang hoạt động...")
    bot.polling(none_stop=True)

if __name__ == "__main__":
    main()
