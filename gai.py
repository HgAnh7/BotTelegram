import os, time, requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = "https://api-l8y6.onrender.com/api/random-video"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

offset = 0
while True:
    res = requests.get(f"{BASE_URL}/getUpdates", params={"timeout": 30, "offset": offset}).json()
    for upd in res["result"]:
        offset = upd["update_id"] + 1
        message = upd.get("message")
        if not message:
            continue

        chat_id = message["chat"]["id"]
        msg_id = message["message_id"]
        text = message.get("text")

        if text == "/gai":
            try:
                vid = requests.get(API_URL, timeout=5).json()["video_url"]
                requests.post(
                    f"{BASE_URL}/sendVideo",
                    data={
                        "chat_id": chat_id,
                        "video": vid,
                        "reply_to_message_id": msg_id
                    }
                )
            except:
                requests.post(
                    f"{BASE_URL}/sendMessage",
                    data={
                        "chat_id": chat_id,
                        "text": "Xin lỗi, không lấy được video.",
                        "reply_to_message_id": msg_id
                    }
                )
    time.sleep(1)
