import os
import logging
import re
import requests
from urllib.parse import quote, unquote
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token bot Telegram - thay thế bằng token thực của bạn
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

class SnapVideoDownloader:
    def __init__(self):
        self.base_url = "https://snapvideo.vn/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def is_valid_url(self, url):
        """Kiểm tra URL có hợp lệ không"""
        url_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
            r'(?:https?://)?(?:www\.)?facebook\.com/.+',
            r'(?:https?://)?(?:www\.)?tiktok\.com/.+',
            r'(?:https?://)?(?:vm\.)?tiktok\.com/.+',
            r'(?:https?://)?(?:www\.)?instagram\.com/.+',
            r'(?:https?://)?(?:www\.)?twitter\.com/.+',
            r'(?:https?://)?(?:www\.)?x\.com/.+',
        ]
        
        for pattern in url_patterns:
            if re.match(pattern, url, re.IGNORECASE):
                return True
        return False
    
    def get_download_links(self, video_url):
        """Lấy link tải video và âm thanh từ SnapVideo"""
        try:
            # Tạo URL request đến SnapVideo
            snapvideo_url = f"{self.base_url}#url={video_url}"
            
            # Gửi request để lấy trang
            response = self.session.get(snapvideo_url)
            response.raise_for_status()
            
            # Parse HTML để tìm link tải
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Tìm tất cả các link download
            download_links = soup.find_all('a', class_='btn btn-dark px-4 rounded-pill shadow-tad')
            
            video_link = None
            audio_link = None
            
            for link in download_links:
                href = link.get('href', '')
                if 'y-download.php' in href:  # Link video
                    video_link = href
                elif 'download/?id=' in href and 'itaga=140' in href:  # Link audio
                    audio_link = href
                    
            return {
                'video': video_link,
                'audio': audio_link,
                'title': self.extract_title(soup)
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy link tải: {e}")
            return None
    
    def extract_title(self, soup):
        """Trích xuất tiêu đề video"""
        try:
            # Tìm tiêu đề trong các thẻ có thể có
            title_selectors = [
                'title',
                '.video-title',
                'h1',
                'h2',
                '.title'
            ]
            
            for selector in title_selectors:
                element = soup.select_one(selector)
                if element and element.get_text().strip():
                    return element.get_text().strip()
                    
            return "Video không có tiêu đề"
        except:
            return "Video không có tiêu đề"

# Khởi tạo downloader
downloader = SnapVideoDownloader()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /start"""
    welcome_message = """
🎬 **Chào mừng đến với SnapVideo Bot!**

Bot này giúp bạn tải video và âm thanh từ các nền tảng:
• YouTube
• Facebook  
• TikTok
• Instagram
• Twitter/X

**Cách sử dụng:**
1. Gửi link video bạn muốn tải
2. Chọn định dạng tải về (Video hoặc Audio)
3. Nhận link tải trực tiếp

Chỉ cần gửi link video để bắt đầu! 🚀
    """
    
    await update.message.reply_text(
        welcome_message,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /help"""
    help_text = """
📖 **Hướng dẫn sử dụng:**

**Các nền tảng được hỗ trợ:**
• YouTube (youtube.com, youtu.be)
• Facebook (facebook.com)
• TikTok (tiktok.com, vm.tiktok.com)
• Instagram (instagram.com)
• Twitter/X (twitter.com, x.com)

**Cách sử dụng:**
1. Copy link video từ nền tảng bất kỳ
2. Paste link vào chat
3. Chọn tải Video hoặc Audio
4. Click vào link để tải về

**Lưu ý:**
- Bot chỉ hỗ trợ tải video công khai
- Một số video có thể bị hạn chế do bản quyền
- Link tải có thời hạn, hãy tải ngay sau khi nhận
    """
    
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown'
    )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý URL được gửi"""
    url = update.message.text.strip()
    
    # Kiểm tra URL hợp lệ
    if not downloader.is_valid_url(url):
        await update.message.reply_text(
            "❌ Link không được hỗ trợ!\n\n"
            "Vui lòng gửi link từ:\n"
            "• YouTube\n• Facebook\n• TikTok\n• Instagram\n• Twitter/X"
        )
        return
    
    # Gửi thông báo đang xử lý
    processing_msg = await update.message.reply_text("🔄 Đang xử lý link...")
    
    try:
        # Lấy link tải
        result = downloader.get_download_links(url)
        
        if not result:
            await processing_msg.edit_text("❌ Không thể xử lý link này. Vui lòng thử lại!")
            return
        
        # Tạo keyboard với các tùy chọn tải
        keyboard = []
        
        if result['video']:
            keyboard.append([
                InlineKeyboardButton("📹 Tải Video", url=result['video'])
            ])
        
        if result['audio']:
            keyboard.append([
                InlineKeyboardButton("🎵 Tải Audio", url=result['audio'])
            ])
        
        if not keyboard:
            await processing_msg.edit_text("❌ Không tìm thấy link tải cho video này!")
            return
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Tạo thông báo kết quả
        message_text = f"✅ **Xử lý thành công!**\n\n"
        message_text += f"📝 **Tiêu đề:** {result['title']}\n\n"
        message_text += "👇 **Chọn định dạng tải:**"
        
        await processing_msg.edit_text(
            message_text,
            parse_mode='Markdown',
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Lỗi xử lý URL: {e}")
        await processing_msg.edit_text(
            "❌ Có lỗi xảy ra khi xử lý link.\n"
            "Vui lòng thử lại sau!"
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý tin nhắn text thông thường"""
    text = update.message.text
    
    # Kiểm tra xem có chứa URL không
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    
    if urls:
        # Nếu có URL, xử lý URL đầu tiên
        context.args = [urls[0]]
        await handle_url(update, context)
    else:
        # Nếu không có URL, gửi hướng dẫn
        await update.message.reply_text(
            "👋 Xin chào! Để tải video, hãy gửi link từ:\n\n"
            "• YouTube\n• Facebook\n• TikTok\n• Instagram\n• Twitter/X\n\n"
            "Hoặc gõ /help để xem hướng dẫn chi tiết."
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lỗi"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.message:
        await update.message.reply_text(
            "❌ Có lỗi xảy ra! Vui lòng thử lại sau."
        )

def main():
    """Khởi chạy bot"""
    # Tạo Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Thêm handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Handler cho URL và text
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Chạy bot
    print("🤖 Bot đang chạy...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
