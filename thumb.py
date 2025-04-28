import os
from io import BytesIO
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio

# Hỏi token khi chạy
## TOKEN = input("Nhập token bot Telegram của bạn: ").strip()
TOKEN = "7201356785:AAE93_9W2SfEB_9lDwmtd_wcQsZ1EEEng6s" 
if not TOKEN:
    raise ValueError("Bạn phải nhập token.")

# Lệnh /thumb: Người dùng reply tin nhắn chứa file audio với /thumb để bắt đầu xử lý
async def handle_thumb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.reply_to_message:
        await msg.reply_text('Vui lòng reply tin nhắn chứa file nhạc và dùng /thumb.')
        return

    orig = msg.reply_to_message
    doc = orig.document or orig.audio
    if not (doc and doc.mime_type and doc.mime_type.startswith('audio/')):
        await msg.reply_text('Tin nhắn bạn reply không chứa file nhạc.')
        return

    context.user_data['pending'] = {
        'file_id': doc.file_id,
        'filename': doc.file_name or f'{doc.file_unique_id}.mp3',
        'reply_message_id': orig.message_id
    }
    await msg.reply_text('Vui lòng reply tin nhắn này bằng ảnh (JPG/PNG) để tạo thumbnail.')

# Xử lý khi user gửi ảnh (reply tin nhắn /thumb)
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    pending = context.user_data.get('pending')
    if not pending or not msg.reply_to_message:
        return

    filename = pending['filename']
    await msg.reply_text(f'Đang thêm thumbnail cho \"{filename}\"...')

    if msg.photo:
        file = await msg.photo[-1].get_file()
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith('image/'):
        file = await msg.document.get_file()
    else:
        await msg.reply_text('Vui lòng gửi ảnh hợp lệ (JPG/PNG).')
        return

    img_data = await file.download_as_bytearray()
    thumb_buf = BytesIO(img_data)
    thumb_buf.name = 'thumb.jpg'
    thumb_buf.seek(0)

    async def send_audio_with_thumb():
        audio_file = await context.bot.get_file(pending['file_id'])
        audio_data = await audio_file.download_as_bytearray()
        audio_buf = BytesIO(audio_data)
        audio_buf.name = filename
        audio_buf.seek(0)

        await context.bot.send_audio(
            chat_id
