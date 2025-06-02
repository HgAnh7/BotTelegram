import asyncio
import aiohttp
import os
import time
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
from typing import Set, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
MAX_URLS = 10_000  # Giới hạn nội bộ, không hiển thị cho người dùng

class URLCollector:
    def __init__(self):
        self.collected_urls: Set[str] = set()
        self.collection_tasks = {}
        self.session = None

    async def get_session(self):
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=10, connect=5)
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=20)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; URLBot/1.0)'}
            )
        return self.session

    async def close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()

    def extract_url_from_json(self, data, url_key: str) -> Optional[str]:
        if isinstance(data, dict):
            if url_key in data:
                return data[url_key]
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

    async def fetch_single_url(self, api_url: str, url_key: str) -> Optional[str]:
        try:
            session = await self.get_session()
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return self.extract_url_from_json(data, url_key)
        except Exception as e:
            logger.debug(f"Lỗi khi lấy URL: {e}")
        return None

    async def collect_urls(self, chat_id: int, api_url: str, request_count: int,
                           url_key: str, progress_callback) -> Tuple[int, int, int]:
        new_count = dup_count = err_count = 0
        batch_size = min(100, max(10, request_count // 10))

        for start in range(0, request_count, batch_size):
            if chat_id not in self.collection_tasks:
                break

            if len(self.collected_urls) >= MAX_URLS:
                break

            end = min(start + batch_size, request_count)
            tasks = [self.fetch_single_url(api_url, url_key) for _ in range(end - start)]

            try:
                results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=30.0)
                for result in results:
                    if isinstance(result, Exception):
                        err_count += 1
                    elif result:
                        if result not in self.collected_urls:
                            if len(self.collected_urls) < MAX_URLS:
                                self.collected_urls.add(result)
                                new_count += 1
                            else:
                                break
                        else:
                            dup_count += 1
                    else:
                        err_count += 1

                if progress_callback:
                    await progress_callback(end, request_count, new_count, dup_count, err_count)

                await asyncio.sleep(0.05)

            except asyncio.TimeoutError:
                err_count += end - start

        return new_count, dup_count, err_count

    def generate_filename(self, chat_id: int = None, prefix: str = "urls", ext: str = "txt") -> str:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{prefix}_{chat_id}_{timestamp}.{ext}" if chat_id else f"{prefix}_{timestamp}.{ext}"

    def save_urls_to_file(self, filename: str = None, chat_id: int = None) -> Optional[str]:
        if not filename:
            filename = self.generate_filename(chat_id)
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# Danh sách URL thu thập được tại {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Tổng cộng: {len(self.collected_urls)} URL\n\n")
                for url in sorted(self.collected_urls):
                    f.write(f"{url}\n")
            return filename
        except Exception as e:
            logger.error(f"Lỗi lưu tệp: {e}")
            return None

collector = URLCollector()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Bot Thu Thập URL*\n\n"
        "Lệnh có thể sử dụng:\n"
        "• /collect <api_url> <số_lượng> [tên_trường_url] - Bắt đầu thu thập URL\n"
        "• /status - Xem trạng thái bot\n"
        "• /download - Tải danh sách URL đã thu thập\n"
        "• /stop - Dừng quá trình thu thập\n"
        "• /clear - Xoá toàn bộ URL đã lưu\n\n"
        "*Ví dụ:* `/collect https://picsum.photos/200/300 100`",
        parse_mode='Markdown'
    )

async def collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❌ Cú pháp: `/collect <api_url> <số_lượng> [tên_trường_url]`", parse_mode='Markdown')
        return

    chat_id = update.effective_chat.id
    if chat_id in collector.collection_tasks:
        await update.message.reply_text("⚠️ Đang thu thập. Dùng lệnh `/stop` để dừng.")
        return

    try:
        api_url = context.args[0]
        request_count = int(context.args[1])
        url_key = context.args[2] if len(context.args) > 2 else "url"

        if not (1 <= request_count <= 10_000):
            await update.message.reply_text("❌ Số lượng URL phải nằm trong khoảng 1–10.000")
            return

        start_time = time.time()
        status_msg = await update.message.reply_text("🚀 Bắt đầu thu thập...")

        async def update_progress(current, total, new, dup, err):
            elapsed = time.time() - start_time
            speed = current / elapsed if elapsed else 0
            text = (
                f"⏳ Đã xử lý: {current}/{total} ({current / total * 100:.1f}%)\n"
                f"⚡ Tốc độ: {speed:.1f} yêu cầu/giây\n"
                f"✅ Mới: {new} | 🔁 Trùng: {dup} | ❌ Lỗi: {err}\n"
                f"📦 Tổng URL đã lưu: {len(collector.collected_urls)}"
            )
            try:
                await status_msg.edit_text(text)
            except:
                pass

        task = asyncio.create_task(
            collector.collect_urls(chat_id, api_url, request_count, url_key, update_progress)
        )
        collector.collection_tasks[chat_id] = task

        new, dup, err = await task

        if collector.collected_urls:
            filename = collector.save_urls_to_file(chat_id=chat_id)
            if filename:
                total_time = time.time() - start_time
                caption = (
                    f"✅ *Thu thập hoàn tất!*\n\n"
                    f"• Mới: {new}\n"
                    f"• Trùng: {dup}\n"
                    f"• Lỗi: {err}\n"
                    f"• Tổng: {len(collector.collected_urls)} URL\n"
                    f"• Thời gian: {total_time:.1f} giây"
                )
                with open(filename, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename=os.path.basename(filename),
                        caption=caption,
                        parse_mode='Markdown'
                    )
                os.remove(filename)
                await status_msg.delete()
            else:
                await status_msg.edit_text("✅ Hoàn tất! (Lỗi khi lưu tệp)")
        else:
            await status_msg.edit_text("⚠️ Không thu thập được URL nào. Hãy kiểm tra API hoặc tên trường URL.")

    except asyncio.CancelledError:
        await update.message.reply_text("⏹️ Đã dừng thu thập")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
    finally:
        collector.collection_tasks.pop(chat_id, None)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    is_collecting = chat_id in collector.collection_tasks

    text = (
        f"📊 *Trạng thái bot*\n\n"
        f"• URL đã lưu: {len(collector.collected_urls)}\n"
        f"• Đang thu thập: {'🟢 Có' if is_collecting else '🔴 Không'}\n"
        f"• Số tiến trình đang chạy: {len(collector.collection_tasks)}"
    )

    if collector.collected_urls:
        recent = list(collector.collected_urls)[-3:]
        text += "\n\n*URL gần nhất:*\n"
        for i, url in enumerate(recent, 1):
            display = url[:40] + "..." if len(url) > 40 else url
            text += f"{i}. `{display}`\n"

    await update.message.reply_text(text, parse_mode='Markdown')

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not collector.collected_urls:
        await update.message.reply_text("❌ Chưa có URL nào được thu thập")
        return

    chat_id = update.effective_chat.id
    filename = collector.save_urls_to_file(chat_id=chat_id)

    if filename:
        try:
            with open(filename, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=os.path.basename(filename),
                    caption=f"📁 Tổng cộng: {len(collector.collected_urls)} URL"
                )
            os.remove(filename)
        except Exception as e:
            await update.message.reply_text(f"❌ Gửi tệp lỗi: {str(e)}")
    else:
        await update.message.reply_text("❌ Không thể tạo tệp")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in collector.collection_tasks:
        collector.collection_tasks[chat_id].cancel()
        await update.message.reply_text("⏹️ Đã dừng thu thập")
        collector.collection_tasks.pop(chat_id, None)
    else:
        await update.message.reply_text("❌ Không có tiến trình nào đang chạy")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = len(collector.collected_urls)
    collector.collected_urls.clear()
    await collector.close_session()
    await update.message.reply_text(f"🗑️ Đã xoá {count} URL")

def main():
    if not BOT_TOKEN:
        print("❌ TELEGRAM_TOKEN chưa được thiết lập")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("collect", collect))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("download", download))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("clear", clear))

    print("🤖 Bot Thu Thập URL đang chạy...")
    app.run_polling()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot đã dừng")
    finally:
        asyncio.run(collector.close_session())
