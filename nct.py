# TÔN TRỌNG TÁC GIẢ, KHÔNG XÓA DÒNG NÀY
# SOURCE API SOUNDCLOUD SEARCH AND DOWNLOAD BY HOANGANH

import os
import random
import re
import requests
import telebot
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from functools import wraps

token_str = os.getenv("TELEGRAM_BOT_TOKEN")
if not token_str:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set.")

bot = telebot.TeleBot(token_str)
debug = True
session = requests.Session()
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
BASE_URL = 'https://www.nhaccuatui.com'
API_SEARCH = BASE_URL + '/tim-kiem/bai-hat'
nct_data = {}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile Safari/604.1",
]
ACCEPT_LANGUAGES = ["en-US,en;q=0.9", "vi-VN,vi;q=0.9"]

def get_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': random.choice(ACCEPT_LANGUAGES),
        'Referer': BASE_URL,
    }

def format_artist(name: str) -> str:
    name = re.sub(r'^(DJ)(?=\S)', r'\1 ', name)
    name = re.sub(r'(?<=[^\s])(?=[A-Z][a-z])', ' ', name)
    return name

def safe_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Exception in handler {func.__name__}: {e}", exc_info=True)
        return None
    return wrapper

@safe_handler
def search_nhaccuatui(keyword, limit=10):
    session.get(BASE_URL, headers=get_headers(), timeout=10)
    params = {'q': keyword, 'b': 'keyword', 'l': 'tat-ca', 's': 'default'}
    resp = session.get(API_SEARCH, params=params, headers=get_headers(), timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    items = soup.select('ul.sn_search_returns_list_song li.sn_search_single_song')[:limit]
    tracks = []
    for item in items:
        title_elem = item.select_one('h3.title_song a')
        artist_elem = item.select_one('h4.singer_song')
        if not title_elem:
            continue
        href = title_elem['href']
        track_id = href.split('.')[-2]
        title = title_elem.get_text(strip=True)
        if artist_elem:
            raw_name = artist_elem.get_text(strip=True)
            artist = format_artist(raw_name)
        else:
            artist = 'Unknown'
        tracks.append({'title': title, 'artist': artist, 'id': track_id, 'detail_url': urljoin(BASE_URL, href)})
    return tracks

@safe_handler
def get_download_url(track):
    resp = session.get(track['detail_url'], headers=get_headers(), timeout=10)
    resp.raise_for_status()
    match = re.search(r"peConfig\.xmlURL\s*=\s*['\"](https://www\.nhaccuatui\.com/flash/xml\?html5=true&key1=[^'\"]+)['\"]", resp.text)
    if not match:
        return None
    xml_resp = session.get(match.group(1), headers={**get_headers(), 'Referer': track['detail_url']}, timeout=10)
    xml_resp.raise_for_status()
    root = ET.fromstring(xml_resp.text)
    loc = root.find('.//location')
    if loc is None or not loc.text:
        return None
    url = loc.text.strip()
    if url.startswith('//'):
        url = 'https:' + url
    return url.replace('http://', 'https://')

@bot.message_handler(commands=['nct'])
@safe_handler
def cmd_nct_search(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, '🚫 Vui lòng nhập từ khóa. Ví dụ: /nct Tên bài hát')
        return
    tracks = search_nhaccuatui(parts[1])
    if not tracks:
        bot.reply_to(message, '🚫 Không tìm thấy kết quả.')
        return
    text = ''.join(f"{i+1}. {t['title']} | {t['artist']}\n" for i, t in enumerate(tracks))
    sent = bot.reply_to(message, text + '💡 Reply số 1-10 để chọn bài hát')
    nct_data[sent.message_id] = {'user_id': message.from_user.id, 'tracks': tracks, 'orig_id': message.message_id}

@bot.message_handler(func=lambda m: m.reply_to_message and m.reply_to_message.message_id in nct_data)
@safe_handler
def handle_nct_selection(msg):
    data = nct_data[msg.reply_to_message.message_id]
    idx = int(msg.text.strip()) - 1 if msg.text.isdigit() else -1
    if idx < 0 or idx >= len(data['tracks']):
        bot.reply_to(msg, '🚫 Số không hợp lệ.')
        return
    track = data['tracks'][idx]
    load_msg = bot.reply_to(msg, f"🧭 Đang tải: {track['title']}")
    url = get_download_url(track)
    if not url:
        bot.reply_to(msg, '🚫 Lỗi tải nhạc.')
    else:
        bot.send_audio(msg.chat.id, url, title=track['title'], performer=track['artist'], reply_to_message_id=data['orig_id'])

    for m_id in (msg.reply_to_message.message_id, msg.message_id, load_msg.message_id):
        try:
            bot.delete_message(msg.chat.id, m_id)
        except Exception:
            pass
    del nct_data[msg.reply_to_message.message_id]

if __name__ == '__main__':
    print('Bot NhacCuaTui đang chạy...')
    bot.infinity_polling(skip_pending=True)
