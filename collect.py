import requests
import json
import os
import time
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
import threading

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Thay thế bằng token bot của bạn
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

class URLCollector:
    def __init__(self):
        self.collected_urls = set()  # Sử dụng set để tránh trùng lặp
        self.is_collecting = False
    
    def fetch_url_from_api(self, api_url, url_key="url", timeout=10):
        """
        Gọi API và lấy URL từ JSON response
        
        Args:
            api_url: URL của API cần gọi
            url_key: Key chứa URL trong JSON response (mặc định là "url")
            timeout: Timeout cho request (giây)
        
        Returns:
            URL nếu tìm thấy, None nếu không
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(api_url, headers=headers, timeout=timeout)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    url = self.extract_url_from_json(data, url_key)
                    return url
                except json.JSONDecodeError:
                    logger.error("Response không phải JSON hợp lệ")
                    return None
            else:
                logger.warning(f"API trả về status code: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("Request timeout")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi khi gọi API: {e}")
            return None
    
    def extract_url_from_json(self, data, url_key):
        """
        Trích xuất URL từ JSON data (hỗ trợ nested)
        
        Args:
            data: JSON data
            url_key: Key cần tìm
            
        Returns:
            URL nếu tìm thấy, None nếu không
        """
        if isinstance(data, dict):
            if url_key in data:
                return data[url_key]
            
            # Tìm trong nested objects
            for value in data.values():
                if isinstance(value, (dict, list)):
                    result = self.extract_url_from_json(value, url_key)
                    if result:
                        return result
                        
        elif isinstance(data, list):
            for item in data:
                result = self.extract_url_from_json(item, url_key)
                if result:
                    return result
        
        return None
    
    def collect_urls(self, api_url, num_requests, url_key="url", progress_callback=None):
        """
        Thu thập URLs từ API
        
        Args:
            api_url: URL của API
            num_requests: Số lần request
            url_key: Key chứa URL trong JSON
            progress_callback: Callback để cập nhật tiến trình
        """
        self.is_collecting = True
        new_urls_count = 0
        duplicate_count = 0
        error_count = 0
        
        for i in range(num_requests):
            if not self.is_collecting:  # Cho phép dừng giữa chừng
                break
                
            url = self.fetch_url_from_api(api_url, url_key)
            
            if url:
                if url not in self.collected_urls:
                    self.collected_urls.add(url)
                    new_urls_count += 1
                    logger.info(f"Thêm URL mới: {url}")
                else:
                    duplicate_count += 1
                    logger.info(f"URL trùng lặp bỏ qua: {url}")
            else:
                error_count += 1
            
            # Callback để cập nhật tiến trình
            if progress_callback:
                progress_callback(i + 1, num_requests, new_urls_count, duplicate_count, error_count)
            
            # Delay nhỏ để tránh spam API
            time.sleep(0.5)
        
        self.is_collecting = False
        return new_urls_count, duplicate_count, error_count
    
    def save_urls_to_file(self, filename="urls.txt"):
        """Lưu URLs vào file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# URLs được thu thập vào {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Tổng cộng: {len(self.collected_urls)} URLs\n\n")
                
                for url in sorted(self.collected_urls):
                    f.write(f"{url}\n")
            
            return filename
        except Exception as e:
            logger.error(f"Lỗi khi lưu file: {e}")
            return None
    
    def clear_urls(self):
        """Xóa tất cả URLs đã thu thập"""
        self.collected_urls.clear()
    
    def stop_collecting(self):
        """Dừng quá trình thu thập"""
        self.is_collecting = False

# Khởi tạo collector
collector = URLCollector()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /start"""
    welcome_message = """
🤖 *Bot Thu Thập URLs*

Các lệnh có sẵn:
• `/collect <api_url> <số_lần> [url_key]` - Thu thập URLs từ API
• `/status` - Xem trạng thái hiện tại
• `/download` - Tải file urls.txt
• `/clear` - Xóa tất cả URLs đã thu thập
• `/stop` - Dừng quá trình thu thập
• `/help` - Xem hướng dẫn chi tiết

*Ví dụ:*
`/collect https://api.example.com/data 10 url`
    """
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /help"""
    help_text = """
📖 *Hướng Dẫn Sử Dụng*

*Lệnh collect:*
`/collect <api_url> <số_lần> [url_key]`

• `api_url`: URL của API cần gọi
• `số_lần`: Số lần request API (1-1000)
• `url_key`: Key chứa URL trong JSON (mặc định: "url")

*Ví dụ:*
• `/collect https://picsum.photos/200/300 20`
• `/collect https://api.example.com/data 50 download_url`
• `/collect https://randomuser.me/api 10 picture`

*Các API test có thể dùng:*
• `https://jsonplaceholder.typicode.com/posts/1` - key: url
• `https://httpbin.org/json` - key: url
• `https://api.github.com/repos/microsoft/vscode` - key: clone_url

*Lưu ý:*
• Bot sẽ tự động loại bỏ URLs trùng lặp
• File sẽ được lưu với tên `urls.txt`
• Tối đa 1000 requests mỗi lần
• Sử dụng `/stop` để dừng giữa chừng
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def collect_urls_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /collect"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Sử dụng: `/collect <api_url> <số_lần> [url_key]`",
            parse_mode='Markdown'
        )
        return
    
    if collector.is_collecting:
        await update.message.reply_text("⚠️ Bot đang thu thập URLs. Dùng `/stop` để dừng trước.")
        return
    
    try:
        api_url = context.args[0]
        num_requests = int(context.args[1])
        url_key = context.args[2] if len(context.args) > 2 else "url"
        
        if num_requests < 1 or num_requests > 1000:
            await update.message.reply_text("❌ Số lần request phải từ 1-1000")
            return
        
        # Gửi thông báo bắt đầu
        progress_msg = await update.message.reply_text("🚀 Bắt đầu thu thập URLs...")
        
        # Hàm cập nhật tiến trình đơn giản hơn
        def update_progress(current, total, new_count, duplicate_count, error_count):
            if current % 5 == 0 or current == total:  # Cập nhật mỗi 5 lần
                progress_text = f"📊 Tiến trình: {current}/{total}\n"
                progress_text += f"✅ URLs mới: {new_count}\n"
                progress_text += f"🔄 Trùng lặp: {duplicate_count}\n"
                progress_text += f"❌ Lỗi: {error_count}"
                
                # Lưu để cập nhật sau (tránh async trong sync function)
                update_progress.last_text = progress_text
        
        update_progress.last_text = "🚀 Bắt đầu thu thập URLs..."
        
        # Thu thập URLs trực tiếp (không dùng thread để tránh lỗi event loop)
        new_count, duplicate_count, error_count = collector.collect_urls(api_url, num_requests, url_key, update_progress)
        
        # Tạo và gửi file ngay lập tức
        if collector.collected_urls:
            try:
                filename = collector.save_urls_to_file()
                if filename and os.path.exists(filename):
                    # Tạo caption với thống kê
                    caption = f"✅ *Thu thập hoàn thành!*\n\n"
                    caption += f"📊 Kết quả:\n"
                    caption += f"• URLs mới: {new_count}\n"
                    caption += f"• Trùng lặp: {duplicate_count}\n"
                    caption += f"• Lỗi: {error_count}\n"
                    caption += f"• Tổng URLs: {len(collector.collected_urls)}"
                    
                    # Gửi file với caption
                    with open(filename, 'rb') as f:
                        await update.message.reply_document(
                            document=f,
                            filename="urls.txt",
                            caption=caption,
                            parse_mode='Markdown'
                        )
                    
                    # Xóa file tạm
                    os.remove(filename)
                    
                    # Xóa message tiến trình
                    await progress_msg.delete()
                    
                else:
                    # Nếu không tạo được file, hiển thị kết quả text
                    result_text = f"✅ *Hoàn thành!*\n\n"
                    result_text += f"📊 Kết quả:\n"
                    result_text += f"• URLs mới: {new_count}\n"
                    result_text += f"• Trùng lặp: {duplicate_count}\n"
                    result_text += f"• Lỗi: {error_count}\n"
                    result_text += f"• Tổng URLs: {len(collector.collected_urls)}\n\n"
                    result_text += f"❌ Lỗi tạo file, dùng `/download` để thử lại"
                    
                    await progress_msg.edit_text(result_text, parse_mode='Markdown')
                    
            except Exception as file_error:
                # Nếu có lỗi khi gửi file
                result_text = f"✅ *Thu thập hoàn thành!*\n\n"
                result_text += f"📊 Kết quả:\n"
                result_text += f"• URLs mới: {new_count}\n"
                result_text += f"• Trùng lặp: {duplicate_count}\n"
                result_text += f"• Lỗi: {error_count}\n"
                result_text += f"• Tổng URLs: {len(collector.collected_urls)}\n\n"
                result_text += f"❌ Lỗi gửi file: {str(file_error)}\n"
                result_text += f"Dùng `/download` để tải file"
                
                await progress_msg.edit_text(result_text, parse_mode='Markdown')
        else:
            # Nếu không có URLs nào
            result_text = f"⚠️ *Hoàn thành nhưng không có URLs!*\n\n"
            result_text += f"📊 Kết quả:\n"
            result_text += f"• URLs mới: {new_count}\n"
            result_text += f"• Trùng lặp: {duplicate_count}\n"
            result_text += f"• Lỗi: {error_count}\n\n"
            result_text += f"Kiểm tra lại API URL và key name"
            
            await progress_msg.edit_text(result_text, parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text("❌ Số lần request phải là số nguyên")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /status"""
    status_text = f"📊 *Trạng Thái*\n\n"
    status_text += f"• Tổng URLs: {len(collector.collected_urls)}\n"
    status_text += f"• Đang thu thập: {'✅' if collector.is_collecting else '❌'}\n"
    
    if collector.collected_urls:
        recent_urls = list(collector.collected_urls)[-3:]  # 3 URLs gần nhất
        status_text += f"\n*URLs gần nhất:*\n"
        for i, url in enumerate(recent_urls, 1):
            status_text += f"{i}. `{url[:50]}...`\n"
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /download"""
    if not collector.collected_urls:
        await update.message.reply_text("❌ Chưa có URLs nào được thu thập")
        return
    
    try:
        filename = collector.save_urls_to_file()
        if filename and os.path.exists(filename):
            with open(filename, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=filename,
                    caption=f"📁 File chứa {len(collector.collected_urls)} URLs"
                )
            
            # Xóa file tạm sau khi gửi
            os.remove(filename)
        else:
            await update.message.reply_text("❌ Lỗi khi tạo file")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /clear"""
    count = len(collector.collected_urls)
    collector.clear_urls()
    await update.message.reply_text(f"🗑️ Đã xóa {count} URLs")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /stop"""
    if collector.is_collecting:
        collector.stop_collecting()
        await update.message.reply_text("⏹️ Đã dừng quá trình thu thập URLs")
    else:
        await update.message.reply_text("❌ Không có quá trình thu thập nào đang chạy")

def main():
    """Hàm main"""
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Vui lòng thay thế BOT_TOKEN bằng token thực từ @BotFather")
        return
    
    # Tạo application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Thêm handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("collect", collect_urls_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("download", download_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("stop", stop_command))
    
    # Chạy bot
    print("🤖 Bot đang chạy...")
    application.run_polling()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot đã dừng")
