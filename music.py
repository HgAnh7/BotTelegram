# Telegram: @HgAnh_7
import os
import re
import json
import random
import logging
import telebot
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

# --- CẤU HÌNH ---
# Lấy token từ biến môi trường
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Thiết lập logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# User-Agent và Accept-Language chung cho cả hai bot
def get_random_element(array):
    return random.choice(array)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]
ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9", "fr-FR,fr;q=0.9", "es-ES,es;q=0.9",
    "de-DE,de;q=0.9", "zh-CN,zh;q=0.9"
]

def get_headers(referer: str = None) -> dict:
    headers = {
        "User-Agent": get_random_element(USER_AGENTS),
        "Accept-Language": get_random_element(ACCEPT_LANGUAGES),
    }
    if referer:
        headers['Referer'] = referer
    return headers

# --- DATA STORAGE ---
soundcloud_data = {}
nct_data = {}

# =========================
# 1. SOUNDCLOUD FUNCTIONS
# =========================
PLATFORM_SC = "soundcloud"
API_BASE = "https://api-v2.soundcloud.com"
CONFIG_PATH = "config.json"

# Lấy client_id cho SoundCloud
def get_client_id():
    try:
        config = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            if config.get('client_id'):
                return config['client_id']
        # Tải trang để tìm script chứa client_id
        resp = requests.get("https://soundcloud.com/", headers=get_headers("https://soundcloud.com/"))
        resp.raise_for_status()
        # Tìm URL script chứa client_id
        scripts = re.findall(r'<script crossorigin src="([^\"]+)"', resp.text)
        script_urls = [url for url in scripts if url.startswith("https")]
        script_resp = requests.get(script_urls[-1], headers=get_headers(script_urls[-1]))
        script_resp.raise_for_status()
        match = re.search(r',client_id:"([^"]+)"', script_resp.text)
        client_id = match.group(1) if match else None
        if client_id:
            config['client_id'] = client_id
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
            return client_id
    except Exception as e:
        logging.error(f"Error fetching SoundCloud client_id: {e}")
    # Fallback
    return 'W00nmY7TLer3uyoEo1sWK3Hhke5Ahdl9'

# Tìm kiếm bài hát trên SoundCloud
def get_music_info(keyword, limit=10):
    try:
        client_id = get_client_id()
        params = {
            'q': keyword,
            'client_id': client_id,
            'limit': limit,
            'variant_ids': '',
            'linked_partitioning': 1,
            'app_locale': 'en'
        }
        resp = requests.get(f"{API_BASE}/search/tracks", params=params, headers=get_headers("https://soundcloud.com/"))
        resp.raise_for_status()
        return resp.json().get('collection', [])
    except Exception as e:
        logging.error(f"Error fetching SoundCloud tracks: {e}")
        return []

# Lấy URL stream audio
def get_music_stream_url(track):
    try:
        client_id = get_client_id()
        resolve_url = f"{API_BASE}/resolve?url={track['permalink_url']}&client_id={client_id}"
        resp = requests.get(resolve_url, headers=get_headers("https://soundcloud.com/"))
        resp.raise_for_status()
        data = resp.json()
        # Tìm progressive link
        progressive = next((t['url'] for t in data.get('media', {}).get('transcodings', []) if t['format']['protocol'] == 'progressive'), None)
        if not progressive:
            raise ValueError("No progressive URL")
        stream_resp = requests.get(f"{progressive}?client_id={client_id}&track_authorization={data.get('track_authorization','')}", headers=get_headers(track['permalink_url']))
        stream_resp.raise_for_status()
        return stream_resp.json().get('url')
    except Exception as e:
        logging.error(f"Error getting SoundCloud stream URL: {e}")
        return None

# Xử lý lệnh /scl
@bot.message_handler(commands=['scl'])
def handle_scl(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "🚫 Vui lòng nhập tên bài hát. Ví dụ: /scl Tên bài hát", parse_mode='HTML')
        return
    keyword = parts[1].strip()
    tracks = [t for t in get_music_info(keyword) if t.get('artwork_url')]
    if not tracks:
        bot.reply_to(message, "🚫 Không tìm thấy bài hát nào khớp.", parse_mode='HTML')
        return
    text = "<b>🎵 Kết quả tìm kiếm trên SoundCloud</b>\n\n"
    for i, t in enumerate(tracks, 1):
        text += f"<b>{i}. {t['title']}</b>\n👤 {t['user']['username']} | ❤️ {t['likes_count']:,}\nID: {t['id']}\n\n"
    text += "<b>💡 Trả lời số (1-10) để chọn!</b>"
    sent = bot.reply_to(message, text, parse_mode='HTML')
    soundcloud_data[sent.message_id] = {'user_id': message.from_user.id, 'tracks': tracks}

@bot.message_handler(func=lambda m: m.reply_to_message and m.reply_to_message.message_id in soundcloud_data)
def handle_scl_selection(msg):
    data = soundcloud_data[msg.reply_to_message.message_id]
    if msg.from_user.id != data['user_id']:
        return
    try:
        idx = int(msg.text.strip()) - 1
        track = data['tracks'][idx]
    except:
        bot.reply_to(msg, "🚫 Số không hợp lệ.", parse_mode='HTML')
        return
    bot.reply_to(msg, f"🧭 Đang tải: {track['title']}", parse_mode='HTML')
    audio_url = get_music_stream_url(track)
    thumb = track.get('artwork_url', '').replace('-large', '-t500x500')
    if not audio_url:
        bot.reply_to(msg, "🚫 Không thể tải audio.", parse_mode='HTML')
        return
    caption = f"<b>🎵 {track['title']}</b>\n👤 {track['user']['username']}"
    bot.send_photo(msg.chat.id, thumb, caption=caption, parse_mode='HTML')
    bot.send_audio(msg.chat.id, audio_url, title=track['title'], performer=track['user']['username'])
    del soundcloud_data[msg.reply_to_message.message_id]

# ===============================
# 2. NHAC CUA TUI FUNCTIONS
# ===============================
BASE_URL = 'https://www.nhaccuatui.com'
API_SEARCH_NCT = BASE_URL + '/tim-kiem/bai-hat'

# Tìm kiếm trên NhacCuaTui
def search_nhaccuatui(keyword, limit=10):
    session = requests.Session()
    session.get(BASE_URL, headers=get_headers(BASE_URL))
    try:
        resp = session.get(API_SEARCH_NCT, params={'q': keyword, 'b': 'keyword', 'l': 'tat-ca', 's': 'default'}, headers=get_headers(BASE_URL))
        resp.raise_for_status()
    except Exception as e:
        logging.error(f"NCT search error: {e}")
        return []
    soup = BeautifulSoup(resp.text, 'html.parser')
    items = soup.select('ul.sn_search_returns_list_song li.sn_search_single_song')[:limit]
    tracks = []
    for it in items:
        a = it.select_one('h3.title_song a')
        if not a: continue
        title = a.get_text(strip=True)
        href = a['href']
        track_id = href.split('.')[-2]
        artist_el = it.select_one('h4.singer_song')
        artist = ', '.join([x.get_text(strip=True) for x in artist_el.select('a')]) if artist_el else 'Unknown'
        tracks.append({'title': title, 'artist': artist, 'detail_url': urljoin(BASE_URL, href)})
    return tracks

# Lấy link audio từ trang chi tiết XML
def get_download_url(track):
    try:
        resp = requests.get(track['detail_url'], headers=get_headers(track['detail_url']))
        resp.raise_for_status()
        match = re.search(r"peConfig\.xmlURL\s*=\s*['\"](https://www\.nhaccuatui\.com/flash/xml\?html5=true&key1=[^'\"]+)['\"]", resp.text)
        xml_url = match.group(1) if match else None
        if not xml_url:
            return None
        xml_resp = requests.get(xml_url, headers={**get_headers(track['detail_url']), 'Referer': track['detail_url']})
        xml_resp.raise_for_status()
        root = ET.fromstring(xml_resp.text)
        loc = root.find('.//location')
        url = loc.text.strip() if loc is not None else None
        if url and url.startswith('//'):
            url = 'https:' + url
        elif url and url.startswith('http://'):
            url = 'https://' + url[len('http://'):]
        return url
    except Exception as e:
        logging.error(f"Error fetching NCT download URL: {e}")
        return None

# Xử lý lệnh /nct
@bot.message_handler(commands=['nct'])
def handle_nct(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "🚫 Vui lòng nhập từ khóa. Ví dụ: /nct Tên bài hát")
        return
    keyword = parts[1].strip()
    tracks = search_nhaccuatui(keyword)
    if not tracks:
        bot.reply_to(message, "🚫 Không tìm thấy kết quả.")
        return
    text = "<b>🎶 Kết quả tìm kiếm NhacCuaTui</b>\n\n"
    for i, t in enumerate(tracks, 1):
        text += f"{i}. {t['title']} - {t['artist']}\n"
    text += "<b>💡 Trả lời số (1-10) để chọn!</b>"
    sent = bot.reply_to(message, text, parse_mode='HTML')
    nct_data[sent.message_id] = {'user_id': message.from_user.id, 'tracks': tracks}

@bot.message_handler(func=lambda m: m.reply_to_message and m.reply_to_message.message_id in nct_data)
def handle_nct_selection(msg):
    data = nct_data[msg.reply_to_message.message_id]
    if msg.from_user.id != data['user_id']:
        return
    try:
        idx = int(msg.text.strip()) - 1
        track = data['tracks'][idx]
    except:
        bot.reply_to(msg, '🚫 Số không hợp lệ.')
        return
    bot.reply_to(msg, f"🧭 Đang tải: {track['title']}")
    audio_url = get_download_url(track)
    if not audio_url:
        bot.reply_to(msg, '🚫 Không thể tải nhạc.')
        return
    bot.send_audio(msg.chat.id, audio_url, title=track['title'], performer=track['artist'])
    del nct_data[msg.reply_to_message.message_id]

# =========================
# MAIN
# =========================
if __name__ == '__main__':
    print("Bot âm nhạc đang chạy...")
    bot.polling(none_stop=True)
