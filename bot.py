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

ADMIN_ID = 6379209139
ADMIN_USERNAME = "HgAnh7"
TOKEN = os.getenv("TELEGRAM_TOKEN")

bot = telebot.TeleBot(TOKEN)

uploaded_files_dir = 'uploaded_bots'
bot_scripts = {}
stored_tokens = {}
user_subscriptions = {}  
user_files = {}  
active_users = set()  

bot_locked = False
free_mode = False  

if not os.path.exists(uploaded_files_dir):
    os.makedirs(uploaded_files_dir)

def init_db():
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

def load_data():
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

def save_subscription(user_id, expiry):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)', 
              (user_id, expiry.isoformat()))
    conn.commit()
    conn.close()

def remove_subscription_db(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def save_user_file(user_id, file_name):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT INTO user_files (user_id, file_name) VALUES (?, ?)', 
              (user_id, file_name))
    conn.commit()
    conn.close()

def remove_user_file_db(user_id, file_name):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('DELETE FROM user_files WHERE user_id = ? AND file_name = ?', 
              (user_id, file_name))
    conn.commit()
    conn.close()

def add_active_user(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO active_users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def remove_active_user(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('DELETE FROM active_users WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

init_db()
load_data()

def create_main_menu(user_id):
    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton('📤 Tải lên tệp', callback_data='upload'),
        types.InlineKeyboardButton('⚡ Tốc độ Bot', callback_data='speed'),
        types.InlineKeyboardButton('📞 Liên hệ admin', url=f'https://t.me/{ADMIN_USERNAME}')
    )

    if user_id == ADMIN_ID:
        markup.add(
            types.InlineKeyboardButton('💳 Đăng ký', callback_data='subscription'),
            types.InlineKeyboardButton('📊 Thống kê', callback_data='stats'),
            types.InlineKeyboardButton('🔒 Khóa Bot', callback_data='lock_bot'),
            types.InlineKeyboardButton('🔓 Mở khóa Bot', callback_data='unlock_bot'),
            types.InlineKeyboardButton('🔓 Free Mode', callback_data='free_mode'),
            types.InlineKeyboardButton('📢 Broadcast', callback_data='broadcast')
        )

    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if bot_locked:
        bot.send_message(message.chat.id, "⚠️ Hiện tại bot đang bị khóa. Vui lòng thử lại sau.")
        return

    user = message.from_user
    user_id = user.id
    user_name = user.first_name
    user_username = f"{user.username}" if user.username else "Không có"
    

    try:
        user_profile = bot.get_chat(user_id)
        user_bio = user_profile.bio or "No bio"
    except Exception:
        user_bio = "No bio"

    try:
        photos = bot.get_user_profile_photos(user_id, limit=1)
        photo_file_id = photos.photos[0][-1].file_id if photos.photos else None
    except Exception:
        photo_file_id = None

    if user_id not in active_users:
        active_users.add(user_id)  
        add_active_user(user_id)  

        try:
            admin_msg = (
                f"🎉 Người dùng mới tham gia bot!\n\n"
                f"👤 Name: {user_name}\n"
                f"📌 Username: @{user_username}\n"
                f"🆔 ID: {user_id}\n"
                f"📝 Bio: {user_bio}\n"
            )

            if photo_file_id:
                bot.send_photo(ADMIN_ID, photo_file_id, caption=admin_msg)
            else:
                bot.send_message(ADMIN_ID, admin_msg)
        except Exception:
            pass

    welcome_msg = (
        f"〽️┇Welcome: {user_name}\n"
        f"🆔┇Your ID: {user_id}\n"
        f"♻️┇Username: @{user_username}\n"
        f"📰┇Bio: {user_bio}\n\n"
        "〽️ I'm a Python file hosting bot 🎗 You can use the buttons below to control ♻️"
    )

    if photo_file_id:
        bot.send_photo(message.chat.id, photo_file_id, caption=welcome_msg, reply_markup=create_main_menu(user_id))
    else:
        bot.send_message(message.chat.id, welcome_msg, reply_markup=create_main_menu(user_id))

@bot.callback_query_handler(func=lambda call: call.data == 'broadcast')
def broadcast_callback(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⚠️ Bạn không có quyền.", show_alert=True)
        return

    bot.send_message(call.message.chat.id, "📝 Gửi nội dung bạn muốn thông báo đến tất cả người dùng:")
    bot.register_next_step_handler(call.message, process_broadcast_message)

def process_broadcast_message(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là admin.")
        return

    broadcast_message = message.text
    success_count = 0
    fail_count = 0

    for user_id in active_users:
        try:
            bot.send_message(user_id, broadcast_message)
            success_count += 1
        except Exception:
            fail_count += 1

    bot.send_message(message.chat.id, f"📢 Đã gửi thông báo:\n🎉 Thành công: {success_count}\n🤦 Thất bại: {fail_count}")

@bot.callback_query_handler(func=lambda call: call.data == 'speed')
def bot_speed_info(call):
    try:
        start_time = time.time()
        response = requests.get(f'https://api.telegram.org/bot{TOKEN}/getMe', timeout=5)
        latency = f"⚡ Độ trễ: {time.time() - start_time:.2f}s" if response.ok else "⚠️ Lỗi khi kiểm tra"
    except Exception as e:
        latency = f"❌ Lỗi kiểm tra tốc độ bot: {e}"

    bot.send_message(call.message.chat.id, latency)

@bot.callback_query_handler(func=lambda call: call.data == 'upload')
def ask_to_upload_file(call):
    user_id = call.from_user.id
    if bot_locked:
        bot.send_message(user_id, f"⚠️ Bot hiện đang bị khóa. Vui lòng liên hệ @{ADMIN_USERNAME}.")
        return

    if free_mode or (user_id in user_subscriptions and user_subscriptions[user_id]['expiry'] > datetime.now()):
        message = "📄 Gửi file .py hoặc .zip bạn muốn tải lên."
    else:
        message = f"⚠️ Bạn cần đăng ký để sử dụng tính năng này. Liên hệ @{ADMIN_USERNAME}."
    bot.send_message(user_id, message)

@bot.callback_query_handler(func=lambda call: call.data == 'subscription')
def subscription_menu(call):
    if call.from_user.id != ADMIN_ID:
        bot.send_message(call.message.chat.id, "⚠️ Bạn không phải là admin.")
        return

    markup = types.InlineKeyboardMarkup()
    add_subscription = types.InlineKeyboardButton('➕ Thêm đăng ký', callback_data='add_subscription')
    remove_subscription = types.InlineKeyboardButton('➖ Gỡ đăng ký', callback_data='remove_subscription')
    markup.add(add_subscription, remove_subscription)

    bot.send_message(call.message.chat.id, "Chọn thao tác bạn muốn thực hiện:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'stats')
def stats_menu(call):
    if call.from_user.id != ADMIN_ID:
        bot.send_message(call.message.chat.id, "⚠️ Bạn không phải là admin.")
        return

    total_files = sum(len(files) for files in user_files.values())
    total_users = len(user_files)
    active_users_count = len(active_users)
    
    text = (
        "📊 Thống kê bot:\n\n"
        f"📂 Tổng số file: {total_files}\n"
        f"👤 Tổng người dùng: {total_users}\n"
        f"✅ Người dùng đang hoạt động: {active_users_count}"
    )
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == 'add_subscription')
def add_subscription_callback(call):
    if call.from_user.id != ADMIN_ID:
        bot.send_message(call.message.chat.id, "⚠️ Bạn không phải là admin.")
        return

    bot.send_message(
        call.message.chat.id,
        "📥 Gửi `user_id` và số ngày theo định dạng:\n`/add_subscription <user_id> <days>`",
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == 'remove_subscription')
def remove_subscription_callback(call):
    if call.from_user.id != ADMIN_ID:
        bot.send_message(call.message.chat.id, "⚠️ Bạn không phải là admin.")
        return
    bot.send_message(
        call.message.chat.id,
        "🗑️ Gửi `user_id` cần xóa theo định dạng:\n`/remove_subscription <user_id>`",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['add_subscription'])
def add_subscription(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là admin.")
        return

    try:
        user_id = int(message.text.split()[1])
        days = int(message.text.split()[2])
        expiry_date = datetime.now() + timedelta(days=days)

        user_subscriptions[user_id] = {'expiry': expiry_date}
        save_subscription(user_id, expiry_date)

        bot.send_message(message.chat.id, f"✅ Đã thêm {days} ngày cho người dùng `{user_id}`.", parse_mode="Markdown")
        bot.send_message(user_id, f"🎉 Bạn đã được kích hoạt gói {days} ngày. Bắt đầu sử dụng bot nhé!")

    except ValueError:
        bot.send_message(message.chat.id, "⚠️ Sai định dạng. Dùng:\n`/add_subscription <user_id> <số ngày>`", parse_mode="Markdown")   
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Lỗi: {e}")

@bot.message_handler(commands=['remove_subscription'])
def remove_subscription(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là admin.")
        return

    try:
        user_id = int(message.text.split()[1])
        if user_id not in user_subscriptions:
            bot.send_message(message.chat.id, f"⚠️ Người dùng `{user_id}` không có gói nào.", parse_mode="Markdown")
            return

        del user_subscriptions[user_id]
        remove_subscription_db(user_id)

        bot.send_message(message.chat.id, f"✅ Đã xóa gói của người dùng `{user_id}`.", parse_mode="Markdown")
        bot.send_message(user_id, "⚠️ Gói của bạn đã bị hủy. Bạn không thể tiếp tục sử dụng bot.")

    except ValueError:
        bot.send_message(message.chat.id, "⚠️ Sai cú pháp. Dùng:\n`/remove_subscription <user_id>`", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Lỗi: {e}")

@bot.message_handler(commands=['user_files'])
def show_user_files(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là admin.")
        return

    try:
        user_id = int(message.text.split()[1])
        if user_id not in user_files or not user_files[user_id]:
            bot.send_message(message.chat.id, f"⚠️ Người dùng `{user_id}` chưa tải lên file nào.", parse_mode="Markdown")
            return

        files = "\n".join(f"📄 `{fname}`" for fname in user_files[user_id])
        bot.send_message(message.chat.id, f"📂 Danh sách file của `{user_id}`:\n{files}", parse_mode="Markdown")

    except ValueError:
            bot.send_message(message.chat.id, "⚠️ Sai cú pháp. Dùng:\n`/user_files <user_id>`", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Lỗi: {e}")

@bot.message_handler(commands=['lock'])
def lock_bot(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là admin.")
        return

    global bot_locked
    bot_locked = True

    bot.send_message(message.chat.id, "🔒 Bot đã được khóa.")

@bot.message_handler(commands=['unlock'])
def unlock_bot(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là admin.")
        return

    global bot_locked
    bot_locked = False

    bot.send_message(message.chat.id, "🔓 Bot đã được mở khóa.")

@bot.callback_query_handler(func=lambda call: call.data == 'lock_bot')
def lock_bot_callback(call):
    if call.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là admin.")
        return

    global bot_locked
    bot_locked = True
    
    bot.send_message(call.message.chat.id, "🔒 Đã khóa bot.")

@bot.callback_query_handler(func=lambda call: call.data == 'unlock_bot')
def unlock_bot_callback(call):
    if call.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là admin.")
        return

    global bot_locked
    bot_locked = False

    bot.send_message(call.message.chat.id, "🔓 Bot đã được mở khóa.")

@bot.callback_query_handler(func=lambda call: call.data == 'free_mode')
def toggle_free_mode(call):
    if call.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là admin.")
        return

    global free_mode
    free_mode = not free_mode
    status = "open" if free_mode else "closed"

    bot.send_message(call.message.chat.id, f"🔓 Chế độ miễn phí hiện tại là:: {status}.")

@bot.message_handler(content_types=['document'])
def handle_file(message):
    user_id = message.from_user.id
    if bot_locked:
        bot.reply_to(message, f"⚠️ Bot hiện đang bị khóa. Liên hệ @{ADMIN_USERNAME}.")
        return

    if not (free_mode or (user_id in user_subscriptions and user_subscriptions[user_id]['expiry'] > datetime.now())):
        return bot.reply_to(message, f"⚠️ Bạn cần đăng ký để sử dụng. Liên hệ @{ADMIN_USERNAME}.")

    file = message.document
    file_name = file.file_name

    if not file_name.endswith(('.py', '.zip')):
        bot.reply_to(message, "⚠️ Chỉ chấp nhận file Python (.py) hoặc file nén .zip.")
        return
    try:
        file_info = bot.get_file(file.file_id)
        file_data = bot.download_file(file_info.file_path)

        timestamp = int(time.time())
        safe_file_name = f"{user_id}_{timestamp}_{file_name}"

        if file_name.endswith('.zip'):
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, safe_file_name)
                with open(zip_path, 'wb') as f:
                    f.write(file_data)

                extract_path = os.path.join(temp_dir, 'unzipped')
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)

                extracted_files = []
                for root, _, files in os.walk(extract_path):
                    extracted_files.extend([os.path.join(root, f) for f in files])

                if len(extracted_files) > 50:
                    return bot.reply_to(message, "❌ File zip chứa quá nhiều file. Giới hạn là 50.")

                final_path = os.path.join(uploaded_files_dir, f"{file_name.split('.')[0]}_{user_id}_{timestamp}")
                os.makedirs(final_path, exist_ok=True)

                for file_path in extracted_files:
                    shutil.move(file_path, os.path.join(final_path, os.path.basename(file_path)))

                py_files = [f for f in os.listdir(final_path) if f.endswith('.py')]
                if not py_files:
                    return bot.send_message(message.chat.id, "❌ Không tìm thấy file `.py` trong file nén.")

                run_script(os.path.join(final_path, py_files[0]), message.chat.id, final_path, py_files[0], message)

        else:
            final_path = os.path.join(uploaded_files_dir, safe_file_name)
            with open(final_path, 'wb') as f:
                f.write(file_data)

            run_script(final_path, message.chat.id, uploaded_files_dir, safe_file_name, message)

        user_files.setdefault(user_id, []).append(file_name)
        save_user_file(user_id, file_name)

    except Exception as e:
        bot.reply_to(message, f"❌ Đã xảy ra lỗi xử lý file:\n`{e}`", parse_mode="Markdown")

def run_script(script_path, chat_id, folder_path, file_name, original_message):
    try:
        requirements_path = os.path.join(os.path.dirname(script_path), 'requirements.txt')
        if os.path.exists(requirements_path):
            bot.send_message(chat_id, "🔄 Đang cài requirements......")
            subprocess.check_call(['pip', 'install', '-r', requirements_path])

        bot.send_message(chat_id, f"🚀 Đang chạy bot: {file_name}...")
        process = subprocess.Popen(['python3', script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        bot_scripts[chat_id] = {'process': process, 'folder_path': folder_path}

        username = f"@{original_message.from_user.username}" if original_message.from_user.username else str(original_message.from_user.id)
        token = extract_token_from_script(script_path)
        
        if token:
            try:
                bot_username = requests.get(f'https://api.telegram.org/bot{token}/getMe').json()['result']['username']
                caption = f"📤 Người dùng {username} đã tải lên một bot mới. Bot username: @{bot_username}"
            except:
                caption = f"📤 Người dùng {username} đã tải lên bot nhưng không lấy được username"
        else:
            caption = f"📤 Người dùng {username} đã tải lên file không chứa token."

        with open(script_path, 'rb') as f:
            bot.send_document(ADMIN_ID, f, caption=caption)

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(f"🔴 Dừng {file_name}", callback_data=f'stop_{chat_id}_{file_name}'),
            types.InlineKeyboardButton(f"🗑️ Xóa {file_name}", callback_data=f'delete_{chat_id}_{file_name}')
        )
        bot.send_message(chat_id, "🎛️ Điều khiển bot bằng các nút bên dưới:", reply_markup=markup)  

    except Exception as e:
        bot.send_message(chat_id, f"❌ Lỗi khi chạy bot:\n{e}")

def extract_token_from_script(script_path):
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r"['\"](\d{9,10}:[\w-]+)['\"]", content)
        return match.group(1) if match else None
    except Exception as e:
        return None

def get_custom_file_to_run(message):
    chat_id = message.chat.id
    user_input = message.text.strip()

    # Kiểm tra người dùng đã chạy bot nào chưa
    if chat_id not in bot_scripts or 'folder_path' not in bot_scripts[chat_id]:
        bot.send_message(chat_id, "⚠️ Bạn chưa có bot nào đang chạy hoặc dữ liệu bị thiếu.")
        return

    folder_path = bot_scripts[chat_id]['folder_path']
    custom_file_path = os.path.join(folder_path, user_input)

    if not os.path.isfile(custom_file_path):
        bot.send_message(chat_id, f"❌ Không tìm thấy file `{user_input}`. Vui lòng kiểm tra tên file.", parse_mode="Markdown")
        return

    try:
        run_script(custom_file_path, chat_id, folder_path, user_input, message)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Lỗi khi chạy file: {e}")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data.startswith('stop_'):
        chat_id = int(call.data.split('_')[1])
        stop_running_bot(chat_id)
    elif call.data.startswith('delete_'):
        chat_id = int(call.data.split('_')[1])
        delete_uploaded_file(chat_id)

def stop_running_bot(chat_id):
    if chat_id in bot_scripts and 'process' in bot_scripts[chat_id]:
        kill_process_tree(bot_scripts[chat_id]['process'])
        bot.send_message(chat_id, "🔴 Bot stopped.")
    else:
        bot.send_message(chat_id, "⚠️ No bot is currently running.")

def delete_uploaded_file(chat_id):
    if chat_id in bot_scripts and 'folder_path' in bot_scripts[chat_id]:
        folder_path = bot_scripts[chat_id]['folder_path']
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            bot.send_message(chat_id, f"🗑️ Bot files deleted.")
        else:
            bot.send_message(chat_id, "⚠️ Files don't exist.")
    else:
        bot.send_message(chat_id, "⚠️ No bot files to delete.")

def kill_process_tree(process):
    try:
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
        for child in children:
            child.kill()
        parent.kill()
    except Exception as e:
        print(f"❌ Failed to kill process: {e}")

@bot.message_handler(commands=['delete_user_file'])
def delete_user_file(message):
    if message.from_user.id == ADMIN_ID:
        try:
            user_id = int(message.text.split()[1])
            file_name = message.text.split()[2]
            
            if user_id in user_files and file_name in user_files[user_id]:
                file_path = os.path.join(uploaded_files_dir, file_name)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    user_files[user_id].remove(file_name)
                    remove_user_file_db(user_id, file_name)
                    bot.send_message(message.chat.id, f"✅ Deleted file {file_name} for user {user_id}.")
                else:
                    bot.send_message(message.chat.id, f"⚠️ File {file_name} doesn't exist.")
            else:
                bot.send_message(message.chat.id, f"⚠️ User {user_id} hasn't uploaded file {file_name}.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Error: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ You are not the developer.")

@bot.message_handler(commands=['stop_user_bot'])
def stop_user_bot(message):
    if message.from_user.id == ADMIN_ID:
        try:
            user_id = int(message.text.split()[1])
            file_name = message.text.split()[2]
            
            if user_id in user_files and file_name in user_files[user_id]:
                for chat_id, script_info in bot_scripts.items():
                    if script_info.get('folder_path', '').endswith(file_name.split('.')[0]):
                        kill_process_tree(script_info['process'])
                        bot.send_message(chat_id, f"🔴 Stopped bot {file_name}.")
                        bot.send_message(message.chat.id, f"✅ Stopped bot {file_name} for user {user_id}.")
                        break
                else:
                    bot.send_message(message.chat.id, f"⚠️ Bot {file_name} is not running.")
            else:
                bot.send_message(message.chat.id, f"⚠️ User {user_id} hasn't uploaded file {file_name}.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Error: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ You are not the developer.")

bot.infinity_polling()
