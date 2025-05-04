import requests, sys, re, threading, json
from time import sleep

session = requests.Session()

def get_token():
    try:
        response = session.get(
            'https://tikfollowers.com/',
            headers={
                'accept': '*/*',
                'accept-language': 'vi-VN,vi;q=0.9',
                'content-type': 'text/plain;charset=UTF-8',
                'origin': 'https://tikfollowers.com',
                'referer': 'https://tikfollowers.com/free-tiktok-followers',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
            },
            timeout=10
        )
        if "csrf_token = '" in response.text:
            return response.text.split("csrf_token = '")[1].split("'")[0]
        else:
            print("Không tìm thấy token trong response.")
            return None
    except Exception as e:
        print(f'Lỗi khi lấy token: {e}')
        return None

def send_follow_and_like():
    user = '@hganh'
    link = 'https://www.tiktok.com/@hganh_7/video/7452648664998104338'

    def thread_follow():
        while True:
            token = get_token()
            if not token:
                print("Không thể lấy token. Thử lại sau 10 giây.")
                sleep(10)
                continue

            try:
                response = session.post(
                    'https://tikfollowers.com/api/free',
                    headers={
                        'accept': '*/*',
                        'content-type': 'text/plain;charset=UTF-8',
                        'origin': 'https://tikfollowers.com',
                        'referer': 'https://tikfollowers.com/free-tiktok-followers',
                        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                    },
                    data=json.dumps({"type": "follow", "q": user, "token": token}),
                    timeout=10
                )
                data = response.json().get("data", "")
            except Exception as e:
                print(f"Yêu cầu Follow thất bại: {e}")
                sleep(3)
                continue

            try:
                send_data = {
                    "token": token,
                    "google_token": "abc",
                    "type": "follow",
                    "data": data
                }
                response = session.post(
                    'https://tikfollowers.com/api/free/send',
                    headers={
                        'accept': '*/*',
                        'content-type': 'text/plain;charset=UTF-8',
                        'origin': 'https://tikfollowers.com',
                        'referer': 'https://tikfollowers.com/free-tiktok-followers',
                        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                    },
                    data=json.dumps(send_data),
                    timeout=10
                )
                result = response.json()
                if result["type"] == "success":
                    print("✅ Follow thành công. Đợi 15 phút...")
                    sleep(900)
                elif result["type"] == "info":
                    mins = int(re.search(r'(\d+)', result["message"]).group(1))
                    print(f"⏳ Chờ {mins} phút để Follow tiếp.")
                    sleep(mins * 60)
                else:
                    print("❌ Lỗi server khi tăng Follow:", result)
                    sleep(3)
            except Exception as e:
                print(f"Lỗi khi gửi Follow: {e}")
                sleep(3)

    def thread_like():
        while True:
            token = get_token()
            if not token:
                print("Không thể lấy token. Thử lại sau 10 giây.")
                sleep(10)
                continue

            try:
                response = session.post(
                    'https://tikfollowers.com/api/free',
                    headers={
                        'accept': '*/*',
                        'content-type': 'text/plain;charset=UTF-8',
                        'origin': 'https://tikfollowers.com',
                        'referer': 'https://tikfollowers.com/free-tiktok-likes',
                        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                    },
                    data=json.dumps({"type": "like", "q": link, "token": token}),
                    timeout=10
                )
                data = response.json().get("data", "")
            except Exception as e:
                print(f"Yêu cầu Like thất bại: {e}")
                sleep(3)
                continue

            try:
                send_data = {
                    "token": token,
                    "google_token": "abc",
                    "type": "like",
                    "data": data
                }
                response = session.post(
                    'https://tikfollowers.com/api/free/send',
                    headers={
                        'accept': '*/*',
                        'content-type': 'text/plain;charset=UTF-8',
                        'origin': 'https://tikfollowers.com',
                        'referer': 'https://tikfollowers.com/free-tiktok-likes',
                        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                    },
                    data=json.dumps(send_data),
                    timeout=10
                )
                result = response.json()
                if result["type"] == "success":
                    print("❤️ Like thành công. Đợi 15 phút...")
                    sleep(900)
                elif result["type"] == "info":
                    mins = int(re.search(r'(\d+)', result["message"]).group(1))
                    print(f"⏳ Chờ {mins} phút để Like tiếp.")
                    sleep(mins * 60)
                else:
                    print("❌ Lỗi server khi tăng Like:", result)
                    sleep(3)
            except Exception as e:
                print(f"Lỗi khi gửi Like: {e}")
                sleep(3)

    threading.Thread(target=thread_follow, daemon=True).start()
    threading.Thread(target=thread_like, daemon=True).start()

    while True:
        sleep(1)  # Giữ chương trình chạy

if __name__ == "__main__":
    send_follow_and_like()
