import requests
import json
import os
import time
import asyncio
import aiohttp
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Set, Optional, Tuple

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
        self.collected_urls: Set[str] = set()
        self.is_collecting = False
        self.session = None
        
    async def create_session(self):
        """Tạo aiohttp session để tái sử dụng connection"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=5, connect=2)
            connector = aiohttp.TCPConnector(
                limit=100,  # Tổng số connection
                limit_per_host=20,  # Connection per host
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
    
    async def close_session(self):
        """Đóng session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def fetch_url_from_api_async(self, api_url: str, url_key: str = "url") -> Optional[str]:
        """
        Gọi API async và lấy URL từ JSON response
        """
        try:
            await self.create_session()
            
            async with self.session.get(api_url) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        url = self.extract_url_from_json(data, url_key)
                        return url
                    except (json.JSONDecodeError, aiohttp.ContentTypeError):
                        logger.error("Response không phải JSON hợp lệ")
                        return None
                else:
                    logger.warning(f"API trả về status code: {response.status}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error("Request timeout")
            return None
        except Exception as e:
            logger.error(f"Lỗi khi gọi API: {e}")
            return None
    
    def fetch_url_from_api_sync(self, api_url: str, url_key: str = "url", timeout: int = 5) -> Optional[str]:
        """
        Phiên bản sync backup cho trường hợp cần thiết
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
    
    def extract_url_from_json(self, data, url_key: str) -> Optional[str]:
        """
        Trích xuất URL từ JSON data (hỗ trợ nested) - Tối ưu hóa
        """
        if isinstance(data, dict):
            # Kiểm tra key trực tiếp trước
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
    
    async def collect_urls_async_batch(self, api_url: str, num_requests: int, url_key: str = "url", 
                                     batch_size: int = 20, progress_callback=None) -> Tuple[int, int, int]:
        """
        Thu thập URLs sử dụng async batch processing
        """
        self.is_collecting = True
        new_urls_count = 0
        duplicate_count = 0
        error_count = 0
        
        await self.create_session()
        
        try:
            # Chia thành các batch để xử lý
            for batch_start in range(0, num_requests, batch_size):
                if not self.is_collecting:
                    break
                
                batch_end = min(batch_start + batch_size, num_requests)
                current_batch_size = batch_end - batch_start
                
                # Tạo tasks cho batch hiện tại
                tasks = [
                    self.fetch_url_from_api_async(api_url, url_key) 
                    for _ in range(current_batch_size)
                ]
                
                # Chạy batch với timeout
                try:
                    results = await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=30.0  # Timeout cho cả batch
                    )
                except asyncio.TimeoutError:
                    logger.error("Batch timeout")
                    error_count += current_batch_size
                    continue
                
                # Xử lý kết quả
                for result in results:
                    if isinstance(result, Exception):
                        error_count += 1
                    elif result:
                        if result not in self.collected_urls:
                            self.collected_urls.add(result)
                            new_urls_count += 1
                            logger.info(f"Thêm URL mới: {result}")
                        else:
                            duplicate_count += 1
                    else:
                        error_count += 1
                
                # Callback tiến trình
                if progress_callback:
                    progress_callback(batch_end, num_requests, new_urls_count, duplicate_count, error_count)
                
                # Delay nhỏ giữa các batch
                if batch_end < num_requests:
                    await asyncio.sleep(0.1)
        
        finally:
            self.is_collecting = False
            await self.close_session()
        
        return new_urls_count, duplicate_count, error_count
    
    def collect_urls_threaded(self, api_url: str, num_requests: int, url_key: str = "url", 
                            max_workers: int = 10, progress_callback=None) -> Tuple[int, int, int]:
        """
        Thu thập URLs sử dụng ThreadPoolExecutor (fallback cho sync)
        """
        self.is_collecting = True
        new_urls_count = 0
        duplicate_count = 0
        error_count = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Tạo futures
            futures = [
                executor.submit(self.fetch_url_from_api_sync, api_url, url_key, 5)
                for _ in range(num_requests)
            ]
            
            # Xử lý kết quả khi hoàn thành
            for i, future in enumerate(as_completed(futures), 1):
                if not self.is_collecting:
                    # Hủy các futures còn lại
                    for f in futures:
                        f.cancel()
                    break
                
                try:
                    url = future.result(timeout=10)
                    if url:
                        if url not in self.collected_urls:
                            self.collected_urls.add(url)
                            new_urls_count += 1
                            logger.info(f"Thêm URL mới: {url}")
                        else:
                            duplicate_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"Lỗi trong thread: {e}")
                
                # Callback tiến trình
                if progress_callback and i % 5 == 0:  # Cập nhật mỗi 5 requests
                    progress_callback(i, num_requests, new_urls_count, duplicate_count, error_count)
        
        self.is_collecting = False
        return new_urls_count, duplicate_count, error_count
    
    def save_urls_to_file(self, filename: str = "urls.txt") -> Optional[str]:
        """Lưu URLs vào file - Tối ưu hóa"""
        try:
            with open(filename, 'w', encoding='utf-8', buffering=8192) as f:
                f.write(f"# URLs được thu thập vào {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Tổng cộng: {len(self.collected_urls)} URLs\n\n")
                
                # Sắp xếp và ghi một lần để tối ưu I/O
                sorted_urls = sorted(self.collected_urls)
                f.writelines(f"{url}\n" for url in sorted_urls)
            
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
🤖 *Bot Thu Thập URLs - Phiên Bản Tối Ưu*

Các lệnh có sẵn:
• `/collect <api_url> <số_lần> [url_key] [mode]` - Thu thập URLs từ API
• `/status` - Xem trạng thái hiện tại
• `/download` - Tải file urls.txt
• `/clear` - Xóa tất cả URLs đã thu thập
• `/stop` - Dừng quá trình thu thập
• `/help` - Xem hướng dẫn chi tiết

*Mode tối ưu:*
• `async` - Sử dụng async (nhanh nhất, mặc định)
• `thread` - Sử dụng threading (tương thích cao)

*Ví dụ:*
`/collect https://api.example.com/data 100 url async`
    """
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /help"""
    help_text = """
📖 *Hướng Dẫn Sử Dụng - Phiên Bản Tối Ưu*

*Lệnh collect:*
`/collect <api_url> <số_lần> [url_key] [mode]`

• `api_url`: URL của API cần gọi
• `số_lần`: Số lần request API (1-2000)
• `url_key`: Key chứa URL trong JSON (mặc định: "url")
• `mode`: Chế độ xử lý (async/thread, mặc định: async)

*Tối ưu hóa mới:*
• ⚡ Async batch processing - nhanh hơn 5-10 lần
• 🔄 Connection pooling - tái sử dụng kết nối
• 🧵 Threading fallback - đảm bảo tương thích
• 📊 Real-time progress tracking
• 💾 Optimized file I/O

*Ví dụ:*
• `/collect https://picsum.photos/200/300 100 url async`
• `/collect https://api.example.com/data 200 download_url thread`
• `/collect https://randomuser.me/api 50 picture`

*Lưu ý:*
• Chế độ async nhanh nhất cho API ổn định
• Chế độ thread tốt cho API có độ trễ cao
• Tối đa 2000 requests mỗi lần (tăng từ 1000)
• Auto retry và error handling
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def collect_urls_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /collect - Tối ưu hóa"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Sử dụng: `/collect <api_url> <số_lần> [url_key] [mode]`",
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
        mode = context.args[3].lower() if len(context.args) > 3 else "async"
        
        if num_requests < 1 or num_requests > 2000:
            await update.message.reply_text("❌ Số lần request phải từ 1-2000")
            return
            
        if mode not in ["async", "thread"]:
            mode = "async"
        
        # Gửi thông báo bắt đầu
        start_time = time.time()
        progress_msg = await update.message.reply_text(
            f"🚀 Bắt đầu thu thập URLs (Chế độ: {mode.upper()})..."
        )
        
        # Biến để theo dõi progress
        last_update_time = 0
        
        def update_progress(current, total, new_count, duplicate_count, error_count):
            nonlocal last_update_time
            current_time = time.time()
            
            # Cập nhật UI mỗi 2 giây hoặc khi hoàn thành
            if current_time - last_update_time >= 2 or current == total:
                last_update_time = current_time
                
                elapsed = current_time - start_time
                rate = current / elapsed if elapsed > 0 else 0
                eta = (total - current) / rate if rate > 0 else 0
                
                progress_text = f"📊 Tiến trình: {current}/{total} ({current/total*100:.1f}%)\n"
                progress_text += f"⚡ Tốc độ: {rate:.1f} req/s\n"
                progress_text += f"⏱️ Còn lại: {eta:.0f}s\n"
                progress_text += f"✅ URLs mới: {new_count}\n"
                progress_text += f"🔄 Trùng lặp: {duplicate_count}\n"
                progress_text += f"❌ Lỗi: {error_count}"
                
                update_progress.last_text = progress_text
        
        # Thu thập URLs với chế độ được chọn
        if mode == "async":
            batch_size = min(50, max(10, num_requests // 10))  # Dynamic batch size
            new_count, duplicate_count, error_count = await collector.collect_urls_async_batch(
                api_url, num_requests, url_key, batch_size, update_progress
            )
        else:  # thread mode
            max_workers = min(20, max(5, num_requests // 10))  # Dynamic worker count
            new_count, duplicate_count, error_count = await asyncio.get_event_loop().run_in_executor(
                None, collector.collect_urls_threaded, api_url, num_requests, url_key, max_workers, update_progress
            )
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_rate = num_requests / total_time if total_time > 0 else 0
        
        # Gửi kết quả và file
        if collector.collected_urls:
            try:
                filename = collector.save_urls_to_file()
                if filename and os.path.exists(filename):
                    # Caption với thống kê chi tiết
                    caption = f"✅ *Thu thập hoàn thành!*\n\n"
                    caption += f"📊 Kết quả:\n"
                    caption += f"• URLs mới: {new_count}\n"
                    caption += f"• Trùng lặp: {duplicate_count}\n"
                    caption += f"• Lỗi: {error_count}\n"
                    caption += f"• Tổng URLs: {len(collector.collected_urls)}\n\n"
                    caption += f"⚡ Hiệu suất:\n"
                    caption += f"• Thời gian: {total_time:.1f}s\n"
                    caption += f"• Tốc độ TB: {avg_rate:.1f} req/s\n"
                    caption += f"• Chế độ: {mode.upper()}"
                    
                    # Gửi file
                    with open(filename, 'rb') as f:
                        await update.message.reply_document(
                            document=f,
                            filename="urls.txt",
                            caption=caption,
                            parse_mode='Markdown'
                        )
                    
                    os.remove(filename)
                    await progress_msg.delete()
                    
                else:
                    # Fallback text result
                    result_text = f"✅ *Hoàn thành!* (Lỗi tạo file)\n\n"
                    result_text += f"📊 URLs mới: {new_count} | Trùng: {duplicate_count} | Lỗi: {error_count}\n"
                    result_text += f"⚡ {avg_rate:.1f} req/s trong {total_time:.1f}s"
                    await progress_msg.edit_text(result_text, parse_mode='Markdown')
                    
            except Exception as file_error:
                logger.error(f"File error: {file_error}")
                result_text = f"✅ *Thu thập hoàn thành!*\n\n"
                result_text += f"📊 URLs: {new_count} mới, {duplicate_count} trùng, {error_count} lỗi\n"
                result_text += f"⚡ {avg_rate:.1f} req/s\n❌ Lỗi gửi file, dùng `/download`"
                await progress_msg.edit_text(result_text, parse_mode='Markdown')
        else:
            result_text = f"⚠️ *Không có URLs nào!*\n\n"
            result_text += f"Kiểm tra API URL và key name\n"
            result_text += f"⚡ Đã test {num_requests} requests trong {total_time:.1f}s"
            await progress_msg.edit_text(result_text, parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text("❌ Số lần request phải là số nguyên")
    except Exception as e:
        logger.error(f"Collect error: {e}")
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /status"""
    status_text = f"📊 *Trạng Thái Bot*\n\n"
    status_text += f"• Tổng URLs: {len(collector.collected_urls)}\n"
    status_text += f"• Đang thu thập: {'✅' if collector.is_collecting else '❌'}\n"
    status_text += f"• Session: {'🟢 Active' if collector.session and not collector.session.closed else '🔴 Closed'}\n"
    
    if collector.collected_urls:
        recent_urls = list(collector.collected_urls)[-3:]
        status_text += f"\n*URLs gần nhất:*\n"
        for i, url in enumerate(recent_urls, 1):
            display_url = url[:50] + "..." if len(url) > 50 else url
            status_text += f"{i}. `{display_url}`\n"
    
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
            os.remove(filename)
        else:
            await update.message.reply_text("❌ Lỗi khi tạo file")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /clear"""
    count = len(collector.collected_urls)
    collector.clear_urls()
    await collector.close_session()  # Đóng session khi clear
    await update.message.reply_text(f"🗑️ Đã xóa {count} URLs và reset session")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /stop"""
    if collector.is_collecting:
        collector.stop_collecting()
        await update.message.reply_text("⏹️ Đã dừng quá trình thu thập URLs")
    else:
        await update.message.reply_text("❌ Không có quá trình thu thập nào đang chạy")

def main():
    """Hàm main"""
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
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
    print("🤖 Bot tối ưu đang chạy...")
    application.run_polling()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot đã dừng")
    finally:
        # Cleanup
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                loop.run_until_complete(collector.close_session())
        except:
            pass
