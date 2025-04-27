import os
from io import BytesIO
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image
import asyncio

# Cấu hình token bot của bạn
token = '7201356785:AAE93_9W2SfEB_9lDwmtd_wưcQsZ1EEng6s'
# Lệnh /thumb: người dùng reply tin nhắn chứa file audio với /thumb để bắt đầu xử lý
async def handle_thumb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    # kiểm tra có reply
    if not msg.reply_to_message:
        await msg.reply_text('Vui lòng reply tin nhắn chứa file nhạc và dùng /thumb.')
        return
    orig = msg.reply_to_message
    doc = orig.document or orig.audio
    if not (doc and doc.mime_type and doc.mime_type.startswith('audio/')):
        await msg.reply_text('Tin nhắn bạn reply không chứa file nhạc.')
        return
    # lưu file_id và tên gốc để chờ ảnh
    context.user_data['pending'] = {
        'file_id': doc.file_id, 
        'filename': doc.file_name or f'{doc.file_unique_id}.mp3',
        'reply_message_id': orig.message_id  # Lưu lại message_id của tin nhắn gốc
    }
    await msg.reply_text('Vui lòng reply tin nhắn này bằng ảnh (JPG/PNG) để tạo thumbnail.')

# Xử lý khi user gửi ảnh (reply tin nhắn /thumb)
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    pending = context.user_data.get('pending')
    # chỉ xử lý khi có pending và ảnh reply tin nhắn /thumb
    if not pending or not msg.reply_to_message:
        return
    
    # Lấy tên file âm thanh gốc
    filename = pending['filename']
    
    # Thông báo đang thêm thumbnail ngay sau khi nhận được ảnh
    await msg.reply_text(f'Đang thêm thumbnail cho "{filename}"...')

    # Xác nhận reply chuỗi
    if msg.photo:
        file = await msg.photo[-1].get_file()
    elif msg.document and msg.document.mime_type.startswith('image/'):
        file = await msg.document.get_file()
    else:
        await msg.reply_text('Vui lòng gửi ảnh hợp lệ (JPG/PNG).')
        return
    img_data = await file.download_as_bytearray()
    img_buf = BytesIO(img_data)
    img_buf.seek(0)
    
    # Nếu ảnh là JPEG, không cần chuyển đổi
    ext = os.path.splitext(file.file_path)[1] if hasattr(file, 'file_path') else '.jpg'
    thumb_buf = img_buf
    if ext.lower() != '.jpg':
        # Chuyển đổi PNG -> JPG nếu cần
        img = Image.open(img_buf).convert('RGB')
        new = BytesIO()
        img.save(new, format='JPEG')
        new.name = 'thumb.jpg'
        new.seek(0)
        thumb_buf = new

    # Tải file âm thanh và gửi kèm thumbnail song song
    async def send_audio_with_thumb():
        # tải file âm thanh
        audio_file = await context.bot.get_file(pending['file_id'])
        audio_data = await audio_file.download_as_bytearray()
        audio_buf = BytesIO(audio_data)
        audio_buf.name = filename  # Đảm bảo tên file âm thanh vẫn giữ nguyên
        audio_buf.seek(0)

        # gửi lại audio kèm thumb và giữ tên file gốc dưới dạng trả lời tin nhắn gốc
        await context.bot.send_audio(
            chat_id=msg.chat.id,
            audio=InputFile(audio_buf, filename=filename),  # Giữ tên file gốc khi gửi
            thumb=InputFile(thumb_buf),  # Gửi thumbnail đã được xử lý
            title=filename,  # Tên file âm thanh sẽ được hiển thị
            performer='',  # Để trống performer để không bị thêm "Unknown"
            reply_to_message_id=pending['reply_message_id']  # Trả lời chính xác tin nhắn gốc
        )

    # Chạy việc tải âm thanh và gửi thumbnail song song
    await asyncio.gather(send_audio_with_thumb(), return_exceptions=True)

    # xóa pending sau khi hoàn thành
    context.user_data.pop('pending', None)

if __name__ == '__main__':
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler('thumb', handle_thumb))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.Category('image/'), handle_image))
    print('Bot đang chạy...')
    app.run_polling()
