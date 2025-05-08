import logging
import subprocess
import os
import tempfile
import zipfile
from telegram import Update, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Đọc token bot từ biến môi trường để bảo mật
TOKEN = os.environ.get('TELEGRAM_TOKEN')

# Hàm đóng gói thư mục thành ZIP và gửi
def send_zip_dir(update: Update, dir_path: str, zip_name: str = 'site_mirror.zip'):
    zip_buffer = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    with zipfile.ZipFile(zip_buffer.name, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, dir_path)
                zf.write(file_path, arcname)
    zip_buffer.close()
    update.message.reply_document(document=InputFile(zip_buffer.name, filename=zip_name))
    os.remove(zip_buffer.name)

# Xử lý lệnh /sourceweb để tải full site như wget mirror
def sourceweb(update: Update, context: CallbackContext) -> None:
    if not context.args:
        update.message.reply_text('Vui lòng gửi URL dưới dạng: /sourceweb <url>')
        return
    url = context.args[0]
    # Tạo thư mục tạm để mirror
    with tempfile.TemporaryDirectory() as tmpdir:
        # Cấu hình lệnh wget
        cmd = [
            'wget',
            '--mirror',
            '--convert-links',
            '--adjust-extension',
            '--page-requisites',
            '--no-parent',
            '-P', tmpdir,
            url
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Gửi thư mục mirror dưới dạng ZIP
            send_zip_dir(update, tmpdir)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"Wget lỗi: {error_msg}")
            update.message.reply_text(f"Không thể mirror trang: {error_msg}")

# Xử lý tin nhắn chứa URL nếu không dùng lệnh
def echo_url(update: Update, context: CallbackContext) -> None:
    text = update.message.text.strip()
    if text.startswith('http'):
        context.args = [text]
        sourceweb(update, context)
    else:
        update.message.reply_text('Vui lòng gửi URL hợp lệ.')

# Hàm chính
def main() -> None:
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('sourceweb', sourceweb))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo_url))

    updater.start_polling()
    logger.info("Bot đã khởi động...")
    updater.idle()

if __name__ == '__main__':
    main()
