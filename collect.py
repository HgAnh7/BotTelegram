import asyncio, aiohttp, os, time, logging
from datetime import datetime
from typing import Set, Optional, Tuple, Dict
from telebot.async_telebot import AsyncTeleBot

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
MAX_URLS = 10_000

class URLCollector:
    def __init__(self):
        self.urls: Set[str] = set()
        self.tasks: Dict[int, asyncio.Task] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_api: Optional[str] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if not isinstance(self.session, aiohttp.ClientSession) or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                connector=aiohttp.TCPConnector(limit=100, limit_per_host=20),
                headers={'User-Agent': 'URLBot/2.0'}
            )
        return self.session

    async def close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()

    def reset_if_api_changed(self, api_url: str):
        if self.last_api and self.last_api != api_url:
            logger.info(f"API changed: cleared {len(self.urls)} URLs")
            self.urls.clear()
        self.last_api = api_url

    def extract_url(self, data, key: str) -> Optional[str]:
        if isinstance(data, dict):
            if key in data: return data[key]
            for v in data.values():
                if isinstance(v, (dict, list)):
                    r = self.extract_url(v, key)
                    if r: return r
        elif isinstance(data, list):
            for item in data:
                r = self.extract_url(item, key)
                if r: return r
        return None

    async def fetch_url(self, api_url: str, url_key: str) -> Optional[str]:
        try:
            async with (await self.get_session()).get(api_url) as r:
                return self.extract_url(await r.json(), url_key) if r.status == 200 else None
        except Exception as e:
            logger.debug(f"Fetch error: {e}")
            return None

    async def collect_batch(self, api_url: str, batch_size: int, url_key: str) -> Tuple[int, int, int]:
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*(self.fetch_url(api_url, url_key) for _ in range(batch_size)), return_exceptions=True),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            return 0, 0, batch_size

        new = dup = err = 0
        for r in results:
            if isinstance(r, Exception) or not r: err += 1
            elif r in self.urls: dup += 1
            elif len(self.urls) < MAX_URLS:
                self.urls.add(r)
                new += 1
        return new, dup, err

    async def collect_urls(self, chat_id: int, api_url: str, count: int, url_key: str, callback) -> Tuple[int, int, int]:
        total_new = total_dup = total_err = processed = 0
        batch_size = min(50, max(10, count // 20))

        for start in range(0, count, batch_size):
            if chat_id not in self.tasks or len(self.urls) >= MAX_URLS: break
            size = min(batch_size, count - start)
            new, dup, err = await self.collect_batch(api_url, size, url_key)
            total_new += new; total_dup += dup; total_err += err; processed += size
            if callback: await callback(processed, count, total_new, total_dup, total_err)
            await asyncio.sleep(0.02)
        return total_new, total_dup, total_err

    def save_urls(self, chat_id: int) -> Optional[str]:
        name = f"urls_{chat_id}_{datetime.now():%Y%m%d_%H%M%S}.txt"
        try:
            with open(name, 'w', encoding='utf-8') as f:
                f.write(f"# URLs collected at {datetime.now():%Y-%m-%d %H:%M:%S}\n")
                f.write(f"# Total: {len(self.urls)} URLs\n\n")
                f.writelines(f"{url}\n" for url in sorted(self.urls))
            return name
        except Exception as e:
            logger.error(f"Save error: {e}")
            return None

    async def run_collection(self, bot, chat_id: int, msg_id: int, api_url: str, count: int, url_key: str):
        start = time.time()

        async def update(current, total, new, dup, err):
            text = (
                f"⏳ {current}/{total} ({current/total*100:.1f}%)\n"
                f"⚡ {current/(time.time()-start):.1f} req/s\n"
                f"✅ Mới: {new} | 🔁 Trùng: {dup} | ❌ Lỗi: {err}\n"
                f"📦 Tổng: {len(self.urls)} URLs"
            )
            try: await bot.edit_message_text(text, chat_id, msg_id)
            except: pass

        new, dup, err = await self.collect_urls(chat_id, api_url, count, url_key, update)
        if not self.urls:
            try: await bot.edit_message_text("⚠️ Không thu thập được URL nào. Kiểm tra API hoặc tên trường.", chat_id, msg_id)
            except: pass
            self.tasks.pop(chat_id, None)
            return

        file = self.save_urls(chat_id)
        if file:
            caption = (
                f"✅ *Thu thập hoàn tất!*\n\n• Mới: {new}\n• Trùng: {dup}\n• Lỗi: {err}"
                f"\n• Tổng: {len(self.urls)} URLs\n• Thời gian: {time.time() - start:.1f}s"
            )
            try:
                with open(file, 'rb') as f:
                    await bot.send_document(chat_id, f, caption=caption, parse_mode='Markdown')
                await bot.delete_message(chat_id, msg_id)
            except Exception as e:
                await bot.send_message(chat_id, f"❌ Lỗi gửi file: {e}")
            finally:
                try: os.remove(file)
                except: pass
        self.tasks.pop(chat_id, None)

collector = URLCollector()
bot = AsyncTeleBot(BOT_TOKEN)

@bot.message_handler(commands=['collect'])
async def handle_collect(msg):
    args = msg.text.split()[1:]
    chat_id = msg.chat.id

    if len(args) < 2:
        await bot.reply_to(msg, (
            "❌ Cú pháp: `/collect <api_url> <số_lượng> [tên_trường_url]`\n"
            "*Ví dụ:* `/collect https://example.com/api 100`"), parse_mode='Markdown')
        return

    if chat_id in collector.tasks:
        await bot.reply_to(msg, "⚠️ Đang thu thập. Vui lòng đợi.")
        return

    try:
        api_url, count = args[0], int(args[1])
        if not 1 <= count <= MAX_URLS:
            await bot.reply_to(msg, "❌ Số lượng phải từ 1-10.000"); return
        url_key = args[2] if len(args) > 2 else "url"
        collector.reset_if_api_changed(api_url)
        status = await bot.reply_to(msg, "🚀 Bắt đầu thu thập...")
        task = asyncio.create_task(collector.run_collection(bot, chat_id, status.message_id, api_url, count, url_key))
        collector.tasks[chat_id] = task
    except ValueError:
        await bot.reply_to(msg, "❌ Số lượng không hợp lệ")
    except Exception as e:
        await bot.reply_to(msg, f"❌ Lỗi: {e}")

async def main():
    if not BOT_TOKEN:
        print("❌ TELEGRAM_TOKEN chưa được thiết lập"); return
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