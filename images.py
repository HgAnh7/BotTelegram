import os
import re
import requests
from telegram import Update
from bs4 import BeautifulSoup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")

async def images(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text('Vui lòng cung cấp URL. Ví dụ: /images https://example.com')
        return

    url = context.args[0]
    if not re.match(r'^https?://', url):
        await update.message.reply_text('URL không hợp lệ. Hãy bắt đầu bằng http:// hoặc https://')
        return

    await update.message.reply_text(f'Đang tải trang: {url} ...')
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        await update.message.reply_text(f'Không thể tải trang: {e}')
        return

    soup = BeautifulSoup(resp.text, 'html.parser')
    images = []

    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src')
        if src:
            full_url = requests.compat.urljoin(resp.url, src)
            images.append(full_url)

    for tag in soup.find_all(style=True):
        style = tag['style']
        for match in re.findall(r'url\(["\']?(.*?)["\']?\)', style):
            full_url = requests.compat.urljoin(resp.url, match)
            images.append(full_url)

    if not images:
        await update.message.reply_text('Không tìm thấy ảnh nào trên trang.')
        return

    # Đánh số và chia nhóm mỗi 30 dòng
    numbered = [f"{i+1}. {img}" for i, img in enumerate(images)]
    batch_size = 30  # mỗi tin nhắn gửi 30 dòng

    for i in range(0, len(numbered), batch_size):
        chunk = '\n'.join(numbered[i:i+batch_size])
        await update.message.reply_text(chunk, disable_web_page_preview=True)

def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass

def main() -> None:
    print("Bot images đang hoạt động...")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler('images', images))
    app.add_error_handler(error_handler)

    app.run_polling()

if __name__ == '__main__':
    main()
