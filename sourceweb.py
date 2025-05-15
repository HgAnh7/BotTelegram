import os
import re
import sys
import requests
import zipfile
import tempfile
import logging
import urllib.parse
import warnings
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Vô hiệu hóa tất cả các log của các thư viện
logging.getLogger().setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("telegram").setLevel(logging.CRITICAL)
logging.getLogger("apscheduler").setLevel(logging.CRITICAL)

# Vô hiệu hóa tất cả các cảnh báo, bao gồm cả từ zipfile
warnings.filterwarnings("ignore")

# Chuyển hướng stderr để loại bỏ các thông báo không mong muốn
class NullWriter:
    def write(self, arg):
        pass
    def flush(self):
        pass

# Lưu lại stderr gốc để có thể khôi phục nếu cần
original_stderr = sys.stderr
sys.stderr = NullWriter()

# Hàm in thông báo tùy chỉnh vào terminal
def print_message(message):
    print(message, flush=True)

# Token bot Telegram của bạn (thay YOUR_BOT_TOKEN bằng token thực)
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Tạo logger của riêng script này để không ảnh hưởng đến đầu ra terminal
logger = logging.getLogger("sourceweb_bot")
logger.setLevel(logging.CRITICAL)  # Không hiển thị log trừ khi nâng cấp độ

async def source_web(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tải xuống source code của trang web và gửi file zip."""
    # Kiểm tra xem có URL không
    if not context.args:
        await update.message.reply_text("Vui lòng cung cấp URL. Ví dụ: /sourceweb https://example.com")
        return

    url = context.args[0]
    
    # Kiểm tra URL có hợp lệ không
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        # Thông báo bắt đầu quá trình
        status_message = await update.message.reply_text(f"Đang bắt đầu tải xuống source code từ {url}...")
        
        # Tạo tên file từ URL
        domain = urllib.parse.urlparse(url).netloc
        zip_filename = f"{domain}_source.zip"
        
        # Tạo thư mục tạm thời để lưu các file
        with tempfile.TemporaryDirectory() as temp_dir:
            # Tải xuống và lưu các file
            downloaded_files = download_website(url, temp_dir)
            
            # Kiểm tra có tải được file nào không
            if not downloaded_files:
                await update.message.reply_text("Không thể tải xuống nội dung từ trang web này. Vui lòng kiểm tra URL và thử lại.")
                await status_message.delete()
                return
            
            # Tạo file zip
            zip_path = os.path.join(temp_dir, zip_filename)
            
            # Tạo một từ điển để theo dõi các file đã được thêm
            added_files = set()
            
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for file_path in downloaded_files:
                    relative_path = os.path.relpath(file_path, temp_dir)
                    # Kiểm tra nếu file đã tồn tại trong zip để tránh cảnh báo trùng lặp
                    if relative_path not in added_files:
                        zipf.write(file_path, relative_path)
                        added_files.add(relative_path)
            
            # Gửi file zip - đảm bảo file được đóng đúng cách
            with open(zip_path, 'rb') as zip_file:
                await update.message.reply_document(
                    document=zip_file,
                    filename=zip_filename,
                    caption=f"Source code của {url} ({len(added_files)} files)",
                    reply_to_message_id=update.message.message_id
                )
            
            # In thông báo tải thành công
            print_message(f"Đã tải source web: {url} ({len(added_files)} files)")
            
            # Xóa thông báo tải xuống
            await status_message.delete()
    
    except Exception as e:
        await update.message.reply_text(f"Xảy ra lỗi khi tải xuống: {str(e)}")
        # Cố gắng xóa thông báo trạng thái nếu có lỗi
        try:
            await status_message.delete()
        except:
            pass

def download_website(base_url, output_dir, max_files=1000):
    """Tải xuống toàn bộ website và lưu vào thư mục đầu ra."""
    processed_urls = set()
    downloaded_files = []
    url_queue = [base_url]
    base_domain = urllib.parse.urlparse(base_url).netloc
    file_count = 0
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    while url_queue and file_count < max_files:
        current_url = url_queue.pop(0)
        
        # Kiểm tra xem URL đã được xử lý chưa
        if current_url in processed_urls:
            continue
        
        # Đánh dấu URL đã được xử lý
        processed_urls.add(current_url)
        
        # Kiểm tra xem URL thuộc cùng domain
        parsed_url = urllib.parse.urlparse(current_url)
        if parsed_url.netloc and parsed_url.netloc != base_domain:
            continue
            
        try:
            # Tải nội dung từ URL
            response = requests.get(current_url, headers=headers)
            if response.status_code != 200:
                continue
                
            # Xác định kiểu nội dung
            content_type = response.headers.get('Content-Type', '').lower()
            
            # Chuẩn bị đường dẫn lưu file
            url_path = parsed_url.path
            if not url_path or url_path.endswith('/'):
                url_path += 'index.html'
                
            # Tránh các ký tự không hợp lệ trong tên file
            safe_path = re.sub(r'[?#].*$', '', url_path)
            
            # Tạo đường dẫn đầy đủ cho file đầu ra
            file_path = os.path.join(output_dir, base_domain, safe_path.lstrip('/'))
            
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Lưu nội dung vào file
            with open(file_path, 'wb') as f:
                f.write(response.content)
                
            downloaded_files.append(file_path)
            file_count += 1
            
            # Nếu là HTML, phân tích và tìm thêm URL
            if 'text/html' in content_type:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Tìm các link CSS
                for css_link in soup.find_all('link', rel='stylesheet'):
                    if css_link.get('href'):
                        css_url = urllib.parse.urljoin(current_url, css_link.get('href'))
                        url_queue.append(css_url)
                
                # Tìm các script JS
                for script in soup.find_all('script', src=True):
                    script_url = urllib.parse.urljoin(current_url, script.get('src'))
                    url_queue.append(script_url)
                
                # Tìm các hình ảnh
                for img in soup.find_all('img', src=True):
                    img_url = urllib.parse.urljoin(current_url, img.get('src'))
                    url_queue.append(img_url)
                
                # Tìm các link trong cùng trang web
                for a_tag in soup.find_all('a', href=True):
                    link_url = urllib.parse.urljoin(current_url, a_tag.get('href'))
                    if urllib.parse.urlparse(link_url).netloc == base_domain:
                        url_queue.append(link_url)
        
        except Exception as e:
            # Lỗi sẽ không hiển thị ra terminal
            pass
    
    return downloaded_files

def main() -> None:
    """Chạy bot."""
    # Tạo ứng dụng
    application = Application.builder().token(TOKEN).build()

    # Thêm command handler cho sourceweb
    application.add_handler(CommandHandler("sourceweb", source_web))

    # Hiển thị thông báo khởi động
    print_message("Bot telegram tải full source web đang chạy...")

    # Chạy bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
