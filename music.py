# TÔN TRỌNG TÁC GIẢ, KHÔNG XÓA DÒNG NÀY
# SOURCE API NHACCUATUI SEARCH AND DOWNLOAD BY HOANGANH
# SOURCE API SOUNDCLOUD SEARCH AND DOWNLOAD BY HOANGANH

import os
import re
import json
import time
import random
import logging
import telebot
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

# --- CẤU HÌNH CHUNG ---
token = os.getenv("TELEGRAM_TOKEN")  # <-- Token người dùng
bot = telebot.TeleBot(token)
CONFIG_PATH = "config.json"

# Cấu hình logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# User-Agent để tránh chặn
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]
ACCEPT_LANGUAGES = ["en-US,en;q=0.9", "fr-FR,fr;q=0.9", "es-ES,es;q=0.9", "de-DE,de;q=0.9", "zh-CN,zh;q=0.9"]

# Lưu tạm dữ liệu cho mỗi lần tìm kiếm
nct_data = {}
soundcloud_data = {}

# --- PHẦN SOUNDCLOUD ---
PLATFORM = "soundcloud"
API_BASE = "https://api-v2.soundcloud.com"

def get_random_element(array):
    return random.choice(array)

def get_headers(referer="https://soundcloud.com/"):
    return {
        "User-Agent": get_random_element(USER_AGENTS),
        "Accept-Language": get_random_element(ACCEPT_LANGUAGES),
        "Referer": referer,
        "Upgrade-Insecure-Requests": "1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }

def get_nct_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': random.choice(ACCEPT_LANGUAGES),
        'Referer': BASE_URL,
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
        logging.error(f"Error fetching client ID: {e}")
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
        logging.error(f"Error fetching music info: {e}")
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
        logging.error(f"Error getting music stream URL: {e}")
        return None

# --- PHẦN NHACCUATUI ---
BASE_URL = 'https://www.nhaccuatui.com'
API_SEARCH = BASE_URL + '/tim-kiem/bai-hat'

# 1. Tìm kiếm bài hát, trả về danh sách track với title, artist, id, detail_url
def search_nhaccuatui(keyword, limit=10):
    params = {'q': keyword, 'b': 'keyword', 'l': 'tat-ca', 's': 'default'}
    try:
        resp = requests.get(API_SEARCH, params=params, headers=get_nct_headers())
        resp.raise_for_status()
        html = resp.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Lỗi request khi tìm kiếm: {e}")
        return []

    soup = BeautifulSoup(html, 'html.parser')
    items = soup.select('ul.sn_search_returns_list_song li.sn_search_single_song')[:limit]
    tracks = []
    for item in items:
        title_elem = item.select_one('h3.title_song a')
        artist_elem = item.select_one('h4.singer_song')
        detail_href = title_elem.get('href') if title_elem else None
        if title_elem and detail_href:
            track_id = detail_href.split('.')[-2]
            title = title_elem.get_text(separator=' ', strip=True)
            artist = 'Unknown'
            if artist_elem:
                artist_links = artist_elem.select('a')
                if artist_links:
                    artists = [a.get_text(separator=' ', strip=True) for a in artist_links]
                    artist = ', '.join(artists)
                else:
                    artist = artist_elem.get_text(separator=' ', strip=True)
            tracks.append({
                'title': title,
                'artist': artist,
                'id': track_id,
                'detail_url': urljoin(BASE_URL, detail_href)
            })
    return tracks

# 2. Lấy URL audio từ trang chi tiết qua XML API
def get_download_url(track):
    detail_url = track.get('detail_url')
    if not detail_url:
        return None
    # Khởi tạo thumbnail mặc định
    track['thumbnail'] = None
    try:
        resp = requests.get(detail_url, headers=get_nct_headers())
        resp.raise_for_status()
        html = resp.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Lỗi request đến trang chi tiết ({detail_url}): {e}")
        return None

    # --- BỔ SUNG: Trích thumbnail từ meta og:image ---
    try:
        soup = BeautifulSoup(html, 'html.parser')
        og_image = soup.select_one('meta[property="og:image"]')
        if og_image and og_image.has_attr('content'):
            thumb_url = og_image['content'].strip()
            # Chuẩn hóa URL nếu cần
            if thumb_url.startswith('//'):
                thumb_url = 'https:' + thumb_url
            track['thumbnail'] = thumb_url
    except Exception as e:
        logging.warning(f"Không lấy được thumbnail từ {detail_url}: {e}")
        track['thumbnail'] = None

    # Trích xmlURL trong JS
    xml_match = re.search(r"peConfig\.xmlURL\s*=\s*['\"](https://www\.nhaccuatui\.com/flash/xml\?html5=true&key1=[^'\"]+)['\"]", html)
    if not xml_match:
        logging.warning(f"Không tìm thấy xmlURL trong trang: {detail_url}")
        return None
    xml_url = xml_match.group(1)

    try:
        xml_resp = requests.get(xml_url, headers={**get_nct_headers(), 'Referer': detail_url})
        xml_resp.raise_for_status()
        xml_content = xml_resp.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Lỗi request đến XML API ({xml_url}): {e}")
        return None

    try:
        root = ET.fromstring(xml_content)
        loc = root.find('.//location')
        if loc is not None and loc.text:
            audio_url = loc.text.strip()
            if audio_url.startswith('//'):
                audio_url = 'https:' + audio_url
            elif audio_url.startswith('http://'):
                audio_url = 'https://' + audio_url[len('http://'):]
            return audio_url
    except ET.ParseError as e:
        logging.error(f"Lỗi parse XML từ ({xml_url}): {e}\nNội dung XML: {xml_content}")
        return None
    return None

# --- XỬ LÝ LỆNH BOT ---

# COMMAND SOUNDCLOUD
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
    for i, track in enumerate(tracks[:10], 1):
        response_text += f"<b>{i}. {track['title']}</b>\n"
        response_text += f"👤 Nghệ sĩ: {track['user']['username']}\n"
        response_text += f"📊 Lượt nghe: {track['playback_count']:,} | Thích: {track['likes_count']:,}\n"
        response_text += f"🆔 ID: {track['id']}\n\n"
    response_text += "<b>💡 Trả lời tin nhắn này bằng số từ 1-10 để chọn bài hát!</b>"
    sent = bot.reply_to(message, response_text, parse_mode='HTML')
    soundcloud_data[sent.message_id] = {
        "user_id": message.from_user.id,
        "tracks": tracks[:10]
    }

# COMMAND NHACCUATUI
@bot.message_handler(commands=['nct'])
def nhaccuatui(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, '🚫 Vui lòng nhập tên bài hát muốn tìm kiếm.\nVí dụ: /nct Tên bài hát', parse_mode='HTML')
        return
    keyword = args[1].strip()
    results = search_nhaccuatui(keyword)
    if not results:
        bot.reply_to(message, f'🚫 Không tìm thấy bài hát nào với từ khóa: {keyword}', parse_mode='HTML')
        return
    songs = results[:10]
    text = '<b>🎵 Kết quả tìm kiếm trên Nhaccuatui</b>\n\n'
    for i, song in enumerate(songs, 1):
        text += f"<b>{i}. {song['title']}</b>\n"
        text += f"👤 Nghệ sĩ: {song['artist']}\n"
        text += f"🆔 ID: {song['id']}\n\n"
    text += '<b>💡 Trả lời tin nhắn này bằng số từ 1-10 để chọn bài hát!</b>'
    sent = bot.reply_to(message, text, parse_mode='HTML')
    nct_data[sent.message_id] = {
        'user_id': message.from_user.id,
        'songs': songs
     }

# XỬ LÝ CHỌN BÀI SOUNDCLOUD
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
    caption = f"""
╭────────────────────⭓
│ Tên nhạc: <b>{track['title']}</b>
│ Nghệ sĩ: {track['user']['username']}
│ Lượt nghe: {track['playback_count']:,} | Lượt thích: {track['likes_count']:,}
│ Nguồn: <b>SoundCloud</b> 
╰────────────────────⭓
"""
    try:
        bot.delete_message(msg.chat.id, reply_id)
    except:
        pass
    bot.send_photo(msg.chat.id, thumbnail_url, caption=caption, parse_mode='HTML')
    bot.send_audio(msg.chat.id, audio_url, title=track['title'], performer=track['user']['username'])
    del soundcloud_data[reply_id]

# XỬ LÝ CHỌN BÀI NHACCUATUI
@bot.message_handler(func=lambda m: m.reply_to_message and m.reply_to_message.message_id in nct_data)
def handle_nct_selection(msg):
    reply_id = msg.reply_to_message.message_id
    if reply_id not in nct_data:
        return
    user_id = msg.from_user.id

    data = nct_data[reply_id]
    if user_id != data['user_id']:
        return
    text = msg.text.strip()
    if not text.isdigit():
        bot.reply_to(msg, '🚫 Vui lòng chỉ nhập số từ 1-10.', parse_mode='HTML')
        return
    idx = int(text) - 1
    if idx < 0 or idx >= len(data['songs']):
        bot.reply_to(msg, '🚫 Số không hợp lệ. Hãy nhập số từ 1-10.')
        return
    song = data['songs'][idx]
    bot.delete_message(msg.chat.id, reply_id)
    bot.reply_to(msg, f"🧭 Đang tải: {song['title']} - {song['artist']}")
    audio_url = get_download_url(song)
    if not audio_url:
        bot.reply_to(msg, '🚫 Không thể tải bài hát này.')
        return
    thumbnail_url = song.get("thumbnail")
    caption = f"""
╭────────────────────⭓
│ Tên nhạc: <b>{song['title']}</b>
│ Nghệ sĩ: {song['artist']}
│ Nguồn: <b>NhacCuaTui</b> 
╰────────────────────⭓
"""
    if thumbnail_url:
        try:
            bot.send_photo(msg.chat.id, thumbnail_url, caption=caption, parse_mode='HTML')
        except Exception:
            bot.reply_to(msg, caption + "\n🚫 Không thể tải thumbnail.", parse_mode='HTML')
    else:
        bot.reply_to(msg, caption, parse_mode='HTML')
    try:
        bot.send_audio(msg.chat.id, audio_url, title=song['title'], performer=song['artist'])
    except Exception:
        bot.reply_to(msg, '🚫 Không thể gửi audio.', parse_mode='HTML')
    del nct_data[reply_id]



if __name__ == '__main__':
    print('Bot nhạc đang chạy...')
    print('Hỗ trợ tìm kiếm từ: NhacCuaTui, SoundCloud')
    bot.polling(none_stop=True)
