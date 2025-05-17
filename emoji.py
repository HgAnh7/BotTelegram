import os
import json
import time
import random
import requests

bot_token = os.getenv("TELEGRAM_TOKEN") # Thay token bot vô đây
emoji_list = emoji_list = ['👍', '👎', '❤️', '🔥', '🥰', '👏', '😁', '🤔', '🤯', '😱', '🤬', '😢', '🎉', '🤩', '🤮', '💩', '🙏', '👌', '🕊️', '🤡', '🥱', '🥴', '😍', '🐳', '❤️‍🔥', '🌚', '🌭', '💯', '🤣', '⚡', '🍌', '🏆', '💔', '🤨', '😐', '🍓', '🍾', '💋', '🖕', '😈', '😴', '😭', '🤓', '👻', '👨‍💻', '👀', '🎃', '🙈', '😇', '😨', '🤝', '✍️', '🤗', '🫡', '🎅', '🎄', '☃️', '💅', '🤪', '🗿', '🆒', '💘', '🙉', '🦄', '😘', '💊', '🙊', '😎', '👾', '🤷‍♂️', '🤷', '🤷‍♀️', '😡']
offset = 0  # Theo dõi tin nhắn đã xử lý

def thaCamXuc(chat_id, message_id, emoji):
    url = f"https://api.telegram.org/bot{bot_token}/setMessageReaction"
    data = {
        'chat_id': chat_id,
        'message_id': message_id,
        'reaction': json.dumps([{'type': 'emoji', 'emoji': emoji}])
    }
    response = requests.post(url, data=data)
    return response.json()

while True:
    try:
        # Lấy tin nhắn mới
        updates = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getUpdates",
            params={"offset": offset, "timeout": 30}
        ).json()

        if "result" in updates:
            for update in updates["result"]:
                offset = update["update_id"] + 1  # Cập nhật offset
                
                if "message" in update:
                    msg = update["message"]
                    chat_id = msg["chat"]["id"]
                    message_id = msg["message_id"]
                    
                    # Thả cảm xúc ngẫu nhiên
                    random_emoji = random.choice(emoji_list)
                    result = thaCamXuc(chat_id, message_id, random_emoji)
                    
                    print(f"Đã thả {random_emoji} vào tin nhắn {message_id}")
                    with open("log.txt", "a", encoding="utf-8") as f:
                        f.write(json.dumps(result, ensure_ascii=False) + "\n")

        time.sleep(1)

    except Exception as e:
        print(f"Lỗi: {str(e)}")
        time.sleep(5)
