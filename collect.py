import asyncio
import aiohttp
import json
import os
import tempfile
from datetime import datetime
from typing import Optional, Set, Tuple
from urllib.parse import urlparse

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Config
BOT_TOKEN = "7757320016:AAEyc-YORyiR2aPz4UTrz7LHNHveSq9NgZw"
MAX_REQUESTS = 50
TIMEOUT = 10
DELAY = 0.5

class URLCollector:
    def __init__(self):
        self.urls: Set[str] = set()
        self.collecting = False
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def get_session(self):
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                headers={'User-Agent': 'Mozilla/5.0 (compatible; URLBot/1.0)'}
            )
        return self.session
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    def is_valid_url(self, url: str) -> bool:
        try:
            result = urlparse(url)
            return bool(result.scheme and result.netloc)
        except:
            return False
    
    def extract_url(self, data, key: str) -> Optional[str]:
        if isinstance(data, dict):
            if key in data and isinstance(data[key], str):
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
    
    async def fetch_url(self, api_url: str, key: str) -> Optional[str]:
        try:
            session = await self.get_session()
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    url = self.extract_url(data, key)
                    return url if url and self.is_valid_url(url) else None
        except:
            pass
        return None
    
    async def collect(self, api_url: str, count: int, key: str, callback=None) -> Tuple[int, int]:
        if not self.is_valid_url(api_url) or not (1 <= count <= MAX_REQUESTS):
            raise ValueError("Invalid API URL or count")
        
        self.collecting = True
        new_count = duplicate_count = 0
        
        try:
            for i in range(count):
                if not self.collecting:
                    break
                
                url = await self.fetch_url(api_url, key)
                if url:
                    if url not in self.urls:
                        self.urls.add(url)
                        new_count += 1
                    else:
                        duplicate_count += 1
                
                if callback and (i + 1) % 5 == 0:
                    callback(i + 1, count, new_count, duplicate_count)
                
                await asyncio.sleep(DELAY)
        finally:
            self.collecting = False
        
        return new_count, duplicate_count
    
    async def save_file(self) -> Optional[str]:
        if not self.urls:
            return None
        
        fd, filename = tempfile.mkstemp(suffix='.txt', prefix='urls_')
        os.close(fd)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# URLs collected: {len(self.urls)}\n")
                f.write(f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for i, url in enumerate(sorted(self.urls), 1):
                    f.write(f"{i}. {url}\n")
            return filename
        except:
            if os.path.exists(filename):
                os.remove(filename)
            return None
    
    def stop(self):
        self.collecting = False
    
    def clear(self) -> int:
        count = len(self.urls)
        self.urls.clear()
        return count

# Global collector
collector = URLCollector()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *URL Collector Bot*\n\n"
        "Commands:\n"
        "• `/collect <api_url> <count> [key]` - Collect URLs\n"
        "• `/status` - Show statistics\n"
        "• `/download` - Get file\n"
        "• `/clear` - Clear URLs\n"
        "• `/stop` - Stop collection\n\n"
        f"Max requests: {MAX_REQUESTS}",
        parse_mode='Markdown'
    )

async def collect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: `/collect <api_url> <count> [key]`", parse_mode='Markdown')
        return
    
    if collector.collecting:
        await update.message.reply_text("⚠️ Already collecting. Use `/stop` first.")
        return
    
    try:
        api_url = context.args[0]
        count = int(context.args[1])
        key = context.args[2] if len(context.args) > 2 else "url"
        
        progress_msg = await update.message.reply_text("🚀 Starting collection...")
        
        async def update_progress(current, total, new, duplicates):
            percent = (current / total) * 100
            text = f"📊 Progress: {current}/{total} ({percent:.0f}%)\n"
            text += f"✅ New: {new} | 🔄 Duplicates: {duplicates}"
            try:
                await progress_msg.edit_text(text)
            except:
                pass
        
        new_count, duplicate_count = await collector.collect(api_url, count, key, update_progress)
        
        if collector.urls:
            filename = await collector.save_file()
            if filename:
                caption = f"✅ Collection complete!\n\n"
                caption += f"📊 New URLs: {new_count}\n"
                caption += f"🔄 Duplicates: {duplicate_count}\n"
                caption += f"📈 Total: {len(collector.urls)}"
                
                with open(filename, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename=f"urls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        caption=caption
                    )
                
                os.remove(filename)
                await progress_msg.delete()
            else:
                await progress_msg.edit_text("✅ Complete but failed to create file. Use `/download`")
        else:
            await progress_msg.edit_text("⚠️ No URLs found. Check API and key name.")
    
    except ValueError:
        await update.message.reply_text("❌ Invalid count or API URL")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"📊 *Status*\n\n"
    text += f"• Total URLs: {len(collector.urls)}\n"
    text += f"• Collecting: {'Yes' if collector.collecting else 'No'}\n"
    
    if collector.urls:
        recent = list(collector.urls)[-3:]
        text += f"\n*Recent URLs:*\n"
        for i, url in enumerate(recent, 1):
            text += f"{i}. `{url[:50]}...`\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def download_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not collector.urls:
        await update.message.reply_text("❌ No URLs collected")
        return
    
    filename = await collector.save_file()
    if filename:
        with open(filename, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=f"urls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                caption=f"📁 {len(collector.urls)} URLs"
            )
        os.remove(filename)
    else:
        await update.message.reply_text("❌ Failed to create file")

async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = collector.clear()
    await update.message.reply_text(f"🗑️ Cleared {count} URLs")

async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if collector.collecting:
        collector.stop()
        await update.message.reply_text("⏹️ Collection stopped")
    else:
        await update.message.reply_text("❌ Not collecting")

def main():
    if not BOT_TOKEN or BOT_TOKEN.startswith("YOUR_BOT"):
        print("❌ Set BOT_TOKEN environment variable")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("collect", collect_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("download", download_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))
    
    print("🤖 Bot starting...")
    
    try:
        # Use run_polling with close_loop=False to avoid event loop conflicts
        app.run_polling(drop_pending_updates=True, close_loop=False)
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")
    finally:
        # Properly close the collector session
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(collector.close())
        else:
            asyncio.run(collector.close())

if __name__ == '__main__':
    # Check if we're in an environment with an existing event loop
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
        print("⚠️ Detected existing event loop. Using alternative approach...")
        
        # If we're here, there's already a running loop
        # We need to run the bot differently
        import nest_asyncio
        nest_asyncio.apply()
        
        async def run_bot():
            if not BOT_TOKEN or BOT_TOKEN.startswith("YOUR_BOT"):
                print("❌ Set BOT_TOKEN environment variable")
                return
            
            app = Application.builder().token(BOT_TOKEN).build()
            
            # Add handlers
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("collect", collect_cmd))
            app.add_handler(CommandHandler("status", status_cmd))
            app.add_handler(CommandHandler("download", download_cmd))
            app.add_handler(CommandHandler("clear", clear_cmd))
            app.add_handler(CommandHandler("stop", stop_cmd))
            
            print("🤖 Bot starting...")
            
            try:
                await app.run_polling(drop_pending_updates=True)
            finally:
                await collector.close()
        
        # Run the bot using the existing event loop
        asyncio.create_task(run_bot())
        
    except RuntimeError:
        # No existing event loop, we can use the normal approach
        main()
    except ImportError:
        print("❌ nest_asyncio not found. Install it with: pip install nest-asyncio")
        print("Or run the bot in a fresh Python session without existing event loops")
        # Fall back to normal approach
        main()