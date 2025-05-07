# TÔN TRỌNG TÁC GIẢ, KHÔNG XÓA DÒNG NÀY
# SOURCE API NHACCUATUI SEARCH AND DOWNLOAD BY HOANGANH

import os
import re
import random
import logging
import telebot
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus, urljoin

# --- CẤU HÌNH ---
# Nhận token từ người dùng nhập vào
token = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(token)

# Khởi tạo session để lưu cookies
debug = True  # Bật/tắt chế độ debug
session = requests.Session()

# Cấu hình logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Thông tin API NhacCuaTui
BASE_URL = 'https://www.nhaccuatui.com'
API_SEARCH = BASE_URL + '/tim-kiem/bai-hat'

# Lưu tạm dữ liệu cho mỗi lần tìm kiếm
nct_data = {}

# User-Agent để tránh chặn
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]
ACCEPT_LANGUAGES = ["en-US,en;q=0.9", "fr-FR,fr;q=0.9", "es-ES,es;q=0.9", "de-DE,de;q=0.9", "zh-CN,zh;q=0.9"]

# Tạo headers ngẫu nhiên
def get_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': random.choice(ACCEPT_LANGUAGES),
        'Referer': BASE_URL,
    }

# 1. Tìm kiếm bài hát, trả về danh sách track với title, artist, id, detail_url
def search_nhaccuatui(keyword, limit=10):
    session.get(BASE_URL, headers=get_headers())  # Lấy cookie
    params = {'q': keyword, 'b': 'keyword', 'l': 'tat-ca', 's': 'default'}
    try:
        resp = session.get(API_SEARCH, params=params, headers=get_headers())
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
                artist_link = artist_elem.select_one('a')
                if artist_link:
                    artist = artist_link.get_text(strip=True)
                else:
                    artist = artist_elem.get_text(strip=True)
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
    try:
        resp = session.get(detail_url, headers=get_headers())
        resp.raise_for_status()
        html = resp.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Lỗi request đến trang chi tiết ({detail_url}): {e}")
        return None

    # Trích xmlURL trong JS
    xml_match = re.search(r"peConfig\.xmlURL\s*=\s*['\"](https://www\.nhaccuatui\.com/flash/xml\?html5=true&key1=[^'\"]+)['\"]", html)
    if not xml_match:
        if debug:
            logging.warning(f"Không tìm thấy xmlURL trong trang: {detail_url}")
        return None
    xml_url = xml_match.group(1)

    try:
        xml_resp = session.get(xml_url, headers={**get_headers(), 'Referer': detail_url})
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

# /nct command
@bot.message_handler(commands=['nct'])
def cmd_nct_search(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, '🚫 Vui lòng nhập từ khóa. Ví dụ: /nct Tên bài hát')
        return
    keyword = parts[1].strip()
    tracks = search_nhaccuatui(keyword)
    if not tracks:
        bot.reply_to(message, '🚫 Không tìm thấy kết quả.')
        return
    text = ''
    for i, t in enumerate(tracks, 1):
        text += f"{i}. {t['title']}\n"
        text += f"👤 Nghệ sĩ: {t['artist']}\n"
        text += f"🆔 ID: {t['id']}\n\n"
    text += '💡 Trả lời tin nhắn này bằng số từ 1-10 để chọn bài hát!'
    sent = bot.reply_to(message, text)
    nct_data[sent.message_id] = {'user_id': message.from_user.id, 'tracks': tracks}

# Xử lý chọn bài
@bot.message_handler(func=lambda m: m.reply_to_message and m.reply_to_message.message_id in nct_data)
def handle_nct_selection(msg):
    data = nct_data[msg.reply_to_message.message_id]
    if msg.from_user.id != data['user_id']:
        return
    try:
        idx = int(msg.text.strip()) - 1
        if idx < 0 or idx >= len(data['tracks']): raise ValueError
    except ValueError:
        bot.reply_to(msg, '🚫 Số không hợp lệ.')
        return
    track = data['tracks'][idx]
    bot.reply_to(msg, f"🧭 Đang tải: {track['title']}")
    audio_url = get_download_url(track)
    if not audio_url:
        bot.reply_to(msg, '🚫 Không thể tải nhạc. Vui lòng kiểm tra log để biết thêm chi tiết.')
        return
    bot.send_audio(msg.chat.id, audio_url, title=track['title'], performer=track['artist'])
    del nct_data[msg.reply_to_message.message_id]

if __name__ == '__main__':
    print('Bot NhacCuaTui đang chạy...')
    bot.polling(none_stop=True)
