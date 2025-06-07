import asyncio
import aiohttp
import os
import time
from datetime import datetime
from telebot.async_telebot import AsyncTeleBot
import logging
from typing import Set, Optional, Tuple, Dict

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cấu hình
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
MAX_URLS = 10_000

class URLCollector:
    def __init__(self):
        self.urls: Set[str] = set()
        self.tasks: Dict[int, asyncio.Task] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_api: Optional[str] = None

    async def get_session(self) -> aiohttp.ClientSession:
        """Lấy hoặc tạo session HTTP mới"""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10, connect=5),
                connector=aiohttp.TCPConnector(limit=100, limit_per_host=20),
                headers={'User-Agent': 'URLBot/2.0'}
            )
        return self.session

    async def close_session(self):
        """Đóng session HTTP"""
        if self.session and not self.session.closed:
            await self.session.close()

    def reset_if_api_changed(self, api_url: str):
        """Reset URLs nếu API thay đổi"""
        if self.last_api and self.last_api != api_url:
            count = len(self.urls)
            self.urls.clear()
            logger.info(f"API changed: cleared {count} URLs")
        self.last_api = api_url

    def extract_url(self, data, key: str) -> Optional[str]:
        """Trích xuất URL từ JSON response"""
        if isinstance(data, dict):
            if key in data:
                return data[key]
            for value in data.values():
                if isinstance(value, (dict, list)):
                    result = self.extract_url(value, key)
                    if result:
                        return result
        elif isinstance(data, list):
            for item in data:
                result = self.extract_url(item, key)
                if result:
                    return result
        return None

    async def fetch_url(self, api_url: str, url_key: str) -> Optional[str]:
        """Lấy một URL từ API"""
        try:
            session = await self.get_session()
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return self.extract_url(data, url_key)
        except Exception as e:
            logger.debug(f"Fetch error: {e}")
        return None

    async def collect_batch(self, api_url: str, batch_size: int, url_key: str) -> Tuple[int, int, int]:
        """Thu thập một batch URLs"""
        tasks = [self.fetch_url(api_url, url_key) for _ in range(batch_size)]
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), 
                timeout=30.0
            )
            
            new_count = dup_count = err_count = 0
            
            for result in results:
                if isinstance(result, Exception) or not result:
                    err_count += 1
                elif result in self.urls:
                    dup_count += 1
                elif len(self.urls) < MAX_URLS:
                    self.urls.add(result)
                    new_count += 1
                else:
                    break
                    
            return new_count, dup_count, err_count
            
        except asyncio.TimeoutError:
            return 0, 0, batch_size

    async def collect_urls(self, chat_id: int, api_url: str, count: int, url_key: str, callback) -> Tuple[int, int, int]:
        """Thu thập URLs với callback tiến độ"""
        total_new = total_dup = total_err = 0
        batch_size = min(50, max(10, count // 20))
        processed = 0

        for start in range(0, count, batch_size):
            if chat_id not in self.tasks or len(self.urls) >= MAX_URLS:
                break

            current_batch = min(batch_size, count - start)
            new, dup, err = await self.collect_batch(api_url, current_batch, url_key)
            
            total_new += new
            total_dup += dup
            total_err += err
            processed += current_batch

            if callback:
                await callback(processed, count, total_new, total_dup, total_err)
            
            await asyncio.sleep(0.02)  # Rate limiting

        return total_new, total_dup, total_err

    def save_urls(self, chat_id: int) -> Optional[str]:
        """Lưu URLs vào file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"urls_{chat_id}_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# URLs collected at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Total: {len(self.urls)} URLs\n\n")
                for url in sorted(self.urls):
                    f.write(f"{url}\n")
            return filename
        except Exception as e:
            logger.error(f"Save error: {e}")
            return None

    async def run_collection(self, bot, chat_id: int, msg_id: int, api_url: str, count: int, url_key: str):
        """Chạy thu thập URLs trong background"""
        start_time = time.time()

        async def update_progress(current, total, new, dup, err):
            """Cập nhật tiến độ"""
            elapsed = time.time() - start_time
            speed = current / elapsed if elapsed > 0 else 0
            text = (
                f"⏳ Đã xử lý: {current}/{total} ({current/total*100:.1f}%)\n"
                f"⚡ Tốc độ: {speed:.1f} yêu cầu/giây\n"
                f"✅ Mới: {new} | 🔁 Trùng: {dup} | ❌ Lỗi: {err}\n"
                f"📦 Tổng: {len(self.urls)} URLs"
            )
            try:
                await bot.edit_message_text(text, chat_id, msg_id)
            except:
                pass

        # Thu thập URLs
        new, dup, err = await self.collect_urls(chat_id, api_url, count, url_key, update_progress)
        
        # Gửi kết quả
        if self.urls:
            filename = self.save_urls(chat_id)
            if filename:
                elapsed = time.time() - start_time
                caption = (
                    f"✅ *Thu thập hoàn tất!*\n\n"
                    f"• Mới: {new}\n• Trùng: {dup}\n• Lỗi: {err}\n"
                    f"• Tổng: {len(self.urls)} URLs\n• Thời gian: {elapsed:.1f}s"
                )
                
                try:
                    with open(filename, 'rb') as f:
                        await bot.send_document(
                            chat_id, f, caption=caption, parse_mode='Markdown',
                            visible_file_name=os.path.basename(filename)
                        )
                    await bot.delete_message(chat_id, msg_id)
                except Exception as e:
                    await bot.send_message(chat_id, f"❌ Lỗi gửi file: {e}")
                finally:
                    os.remove(filename)
            else:
                await bot.send_message(chat_id, "✅ Hoàn tất! (Lỗi lưu file)")
        else:
            try:
                await bot.edit_message_text(
                    "⚠️ Không thu thập được URL nào. Kiểm tra API hoặc tên trường.", chat_id, msg_id
                )
            except:
                pass

        # Cleanup
        self.tasks.pop(chat_id, None)

# Khởi tạo
collector = URLCollector()
bot = AsyncTeleBot(BOT_TOKEN)

@bot.message_handler(commands=['collect'])
async def collect_handler(message):
    """Handler cho lệnh /collect"""
    args = message.text.split()[1:]
    
    if len(args) < 2:
        await bot.reply_to(
            message,
            "❌ Cú pháp: `/collect <api_url> <số_lượng> [tên_trường_url]`\n\n"
            "*Ví dụ:* `/collect https://picsum.photos/200/300 100`",
            parse_mode='Markdown'
        )
        return

    chat_id = message.chat.id
    
    # Kiểm tra task đang chạy
    if chat_id in collector.tasks:
        await bot.reply_to(message, "⚠️ Đang thu thập. Vui lòng đợi.")
        return

    try:
        api_url, count_str = args[0], args[1]
        count = int(count_str)
        url_key = args[2] if len(args) > 2 else "url"

        if not (1 <= count <= 10_000):
            await bot.reply_to(message, "❌ Số lượng phải từ 1-10.000")
            return

        # Reset nếu API thay đổi
        collector.reset_if_api_changed(api_url)

        # Gửi message khởi tạo
        status_msg = await bot.reply_to(message, "🚀 Bắt đầu thu thập...")

        # Tạo background task
        task = asyncio.create_task(
            collector.run_collection(bot, chat_id, status_msg.message_id, api_url, count, url_key)
        )
        collector.tasks[chat_id] = task

    except ValueError:
        await bot.reply_to(message, "❌ Số lượng không hợp lệ")
    except Exception as e:
        await bot.reply_to(message, f"❌ Lỗi: {e}")

async def main():
    """Hàm main"""
    if not BOT_TOKEN:
        print("❌ TELEGRAM_TOKEN chưa được thiết lập")
        return

    print("🤖 Bot Thu Thập URL đang chạy...")
    
    try:
        await bot.polling(non_stop=True)
    except Exception as e:
        logger.error(f"Lỗi bot: {e}")
    finally:
        await collector.close_session()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot đã dừng")
        asyncio.run(collector.close_session())