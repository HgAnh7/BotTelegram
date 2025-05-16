import logging
import random
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Thay thế 'YOUR_BOT_TOKEN' bằng token thực của bot bạn nhận được từ BotFather
BOT_TOKEN = 'YOUR_BOT_TOKEN'

# Danh sách ID của các chat mà bot được phép hoạt động
# Thay thế các số này bằng ID chat thực của bạn
ALLOWED_CHAT_IDS = [
    -1002472439486,  # ID của nhóm 1
    -1009876543210,  # ID của nhóm 2 #
    6379209139,       # ID chat cá nhân (nếu cần)
]

# Danh sách emoji cảm xúc có thể dùng để thả reaction
EMOJI_LIST = [
    '👍', '👎', '❤️', '🔥', '🥰', '👏', '😁', '🤔', '🤯', '😱', 
    '🤬', '😢', '🎉', '🤩', '🤮', '💯', '😴', '🤤', '🤨', '🤝'
]

async def react_to_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Thả cảm xúc ngẫu nhiên cho mỗi tin nhắn khi chat được cho phép."""
    try:
        # Lấy ID của chat hiện tại
        chat_id = update.effective_chat.id
        
        # Kiểm tra xem chat có được phép sử dụng bot không
        if chat_id not in ALLOWED_CHAT_IDS:
            logger.info(f"Chat {chat_id} không được phép sử dụng bot")
            return
        
        # Bỏ qua tin nhắn từ bot hoặc các lệnh
        if update.effective_user.is_bot or (update.message.text and update.message.text.startswith('/')):
            return
        
        # Chọn ngẫu nhiên một emoji
        emoji = random.choice(EMOJI_LIST)
        
        # Thả cảm xúc cho tin nhắn
        message_id = update.message.message_id
        
        await context.bot.set_message_reaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=[{"type": "emoji", "emoji": emoji}]
        )
        
        logger.info(f"Đã thả cảm xúc {emoji} cho tin nhắn {message_id} trong chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Lỗi khi thả cảm xúc: {e}")

def main() -> None:
    """Khởi động bot."""
    # Tạo application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Xử lý tất cả tin nhắn
    application.add_handler(MessageHandler(filters.ALL, react_to_message))

    # Chạy bot cho đến khi người dùng nhấn Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()