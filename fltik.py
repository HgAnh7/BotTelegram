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
            }
        )
        return response.text.split("csrf_token = '")[1].split("'")[0]
    except:
        print('Kiểm tra lại Internet')
        sys.exit()

def send_follow_and_like():
    user = '@hganh'
    link = 'https://www.tiktok.com/@hganh_7/video/7452648664998104338'

    def thread_follow():
        while True:
            token = get_token()
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
                    data=json.dumps({"type": "follow", "q": user, "token": token})
                )
                data = json.loads(response.text).get("data", "")
            except:
                print("Yêu cầu Follow thất bại. Thử lại sau 3 giây.")
                sleep(3)
                continue

            try:
                send_data = {
                    "token": token,
                    "google_token": "abc",  # Giữ nguyên chuỗi giả nếu không dùng token Google thật
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
                    data=json.dumps(send_data)
                )
                result = json.loads(response.text)
                if result["type"] == "success":
                    print("Follow thành công. Đợi 15 phút để gửi tiếp.")
                    sleep(900)
                elif result["type"] == "info":
                    mins = int(re.search(r'(\d+)', result["message"]).group(1))
                    print(f"Vui lòng chờ {mins} phút để Follow tiếp.")
                    sleep(mins * 60)
                else:
                    print("Lỗi server khi tăng Follow")
                    sleep(3)
            except:
                print("Lỗi mạng khi gửi Follow.")
                sleep(3)

    def thread_like():
        while True:
            token = get_token()
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
                    data=json.dumps({"type": "like", "q": link, "token": token})
                )
                data = json.loads(response.text).get("data", "")
            except:
                print("Yêu cầu Like thất bại. Thử lại sau 3 giây.")
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
                    data=json.dumps(send_data)
                )
                result = json.loads(response.text)
                if result["type"] == "success":
                    print("Like thành công. Đợi 15 phút để Like tiếp.")
                    sleep(900)
                elif result["type"] == "info":
                    mins = int(re.search(r'(\d+)', result["message"]).group(1))
                    print(f"Vui lòng chờ {mins} phút để Like tiếp.")
                    sleep(mins * 60)
                else:
                    print("Lỗi server khi tăng Like")
                    sleep(3)
            except:
                print("Lỗi mạng khi gửi Like.")
                sleep(3)

    threading.Thread(target=thread_follow).start()
    threading.Thread(target=thread_like).start()

if __name__ == "__main__":
    send_follow_and_like()
