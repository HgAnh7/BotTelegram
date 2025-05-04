import requests,sys,re,threading,json
from time import sleep

session = requests.Session() 
def get_token():
    try:
        response = session.get('https://tikfollowers.com/', headers={'accept': '*/*','accept-language': 'vi-VN,vi;q=0.9','content-type': 'text/plain;charset=UTF-8','origin': 'https://tikfollowers.com','priority': 'u=1, i','referer': 'https://tikfollowers.com/free-tiktok-followers','sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"','sec-ch-ua-mobile': '?0','sec-ch-ua-platform': '"Windows"','sec-fetch-dest': 'empty','sec-fetch-mode': 'cors','sec-fetch-site': 'same-origin','user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'})
        return response.text.split("csrf_token = '")[1].split("'")[0]
    except:
        print('Kiểm tra lại Internet'); sys.exit()

def main():
    
    while True:
        luachon = int(input('1. Follow✅\n2. Like❤️\n3.Follow✅ + Like❤️\nNhập lựa chọn: '))
        if luachon == 1 :
            link = str(input("Nhập Username : "))
            if link[0]!='@' :
                link = '@'+link
            kieu = 'follow'
        elif luachon == 2:
            while True:
                link = str(input("Nhập Link Video : "))
                if re.search(r'/video/\d+', link):
                    break
                elif re.search(r'/photo/\d+', link):
                    print("Không hỗ trợ link ảnh")
                    continue
                else :
                    print("Link không hợp lệ")
                continue
            kieu = 'like'
        elif luachon == 3:
            user = str(input("Nhập Username : "))
            if user[0]!='@' :
                user = '@'+user
            while True:
                link = str(input("Nhập Link Video : "))
                if re.search(r'/video/\d+', link):
                    break
                elif re.search(r'/photo/\d+', link):
                    print("Không hỗ trợ link ảnh")
                    continue
                else :
                    print("Link không hợp lệ")
                continue
            
            def thread1():
                while True:
                    token = get_token()
                    try:
                        response = session.post('https://tikfollowers.com/api/free', headers={'accept': '*/*','accept-language': 'vi-VN,vi;q=0.9','content-type': 'text/plain;charset=UTF-8','origin': 'https://tikfollowers.com','priority': 'u=1, i','referer': 'https://tikfollowers.com/free-tiktok-followers','sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"','sec-ch-ua-mobile': '?0','sec-ch-ua-platform': '"Windows"','sec-fetch-dest': 'empty','sec-fetch-mode': 'cors','sec-fetch-site': 'same-origin','user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}, data=f'{{"type":"follow","q":"{user}","google_token":"{'03AFcWeA6JMsHnFA92hVyaQGJepvRgKvByZ42vh8GhzCKAZNkn34uyhA8HDhiOseNFPlOCCy2L2IB7RZ4dw1vcHtqoY7gBqsvTJAhFRUryRWAjwcllWZ4Ghp10FBhLsrnB8gHVUywzurcmjEBEJJKW7HnFWnmn-KzxVQ-ZUse0A42fsKDH1uXKqeSGjMWQZRC4rxkhAeZ4t_CySMzRTq67Bdataa0K4LQNGH2C3K2uWuHE8YFlKRoHnvCW3fV4cxmuXdataQCs_CBYaTK-TDlDxNeKnKpQTKr66UB-GK952BZJ4qkA4kZMsTNSD3ADgF_r6xHXE8ZQFqVB37-7ubCDmJ1uljrQ9YyxgdL4dZw08wlUzY690d2vCJLk-824obisjBhGJJ0SIGzN7GPTyuEDMINoO63pXnR0vuc_L_7aLMLRjDidVycGdEH5GcBReqHV5fRO0G_VOjFuhy42feeShWafAFg1Sr4ePStylHfa00KDRVW_qrpQvQ7Rmx3kM-TOoK1CTSWKcOkkoAcwLlr5qm0qa_UKsNYjj6fJPyS1BSB-rrT4CaS7rWwyuBjRvpLiO43eUMIIC7xrmy1AGHb3-6hHoezlUxSPTEVMgL4HiNLFqXx_xJQFfOrca4AdWiAokITYHRtrILg2YuyaSkpYZ9FGKNYifF2NiK-VshkGEUr-PyIzm8tylMIfkHY8vSHU64aLcs2BxSvOANOejmKWbpDJVP69H_P7rQTuGv2bbSLTS4bRDQEfF3QEAtEtUBYd0RiZX-ks55U3RnOUyCrYh_ex87z7g4Y5MPdrQosKVzzRpfTthqwmvIRhmObYX2g5gt-6kXuxQav1r6HH9KZYLeoD0zyo47ejbmXAclE1KGkrEyb_Qn7LGTRlJOL2QOy91SlSfengQFgWQuB1Nx7pJmq4uhfSwUkpWQmlf6e4yYQq2dCFP9l3WdSN-aFgHPbzWbcXyLyphBt6IlS6ic7siDO4NGDi8gIl3gAAiLNbY-vBeOd1HJbLLYpEQjIYofLCGonGA0sRX6eoYIPRYKla2ZXxFE44lw1xAul4AygLa2mn8mWkhWf14vUQStwN3UlFbyi1OELnqsKua93r1N3m7D-94O280jtN7IuiFHYAF8TwHLkfH_6sB7pjep7oNVSGY0PD2rJ80VkM6t2PuJtxmQqovzlsOg2wwnAmt9fudJZkGuJGWwyjRzwJskkDxkeTjO3bwesWRM4dIbF6xUjrl5H-UPSBwFBqDps_BUIIVxivEeNnTi6je2KU9pepBeg2uBUXiqpts8j7U73Ax7ncs2rhVBTMvw02xzDfOnIlTKnOjvs4B0vuav3PbuthoXCiXKOmQEEg3kREAyhDCct_XNRrFAcmFaaJWKkmBLC6qqdyJdPnHzaMyK7mpDQiMiNEillv0i2T2iE6Geb8UXXkANupmW6jdVA-s9HeEhUXfy1yQQoL1AjQnp6g71SG1Hixs8tyu7kQxWr9AvucCCFUYlvVTUiUvAwLm1lP6cy31fkmkOC-U8wlUMz8qWdPVNVRRvNoSr5oI_u2Uqlf4i9FAEPs-eoQ9oEZEltzA-pfX7hBx77jxPbLhT2IPFC8OC0U-xNZTWKW2JUyh77_y3Yq2Ht7JkhHmdov1Rl1FYFZJs-KDrfc0mgCSuaiOO8FbE26IHYNXPNpbmN6khcH2m2oH6q8YfakCnknidz68-_Th0ey-67qxUoXifD1BAxfoKpPhYfU7P_YpskaQa_uGYw__c8H5TO7T1fF7dKEwST4TlIUZSzb5rPqhq-fISrYE1w-gNPlxVpBS5wx6sUw2fHsBtO_SC58e9qmWhtcf460f-SVAgH6fUUCSrqv2vxva_BfIdxjVpFip3XeKr3HQ5IPutvVhyQMEQ911HL32xP6lsLOIglyizH0RKJF7tSrr__p6BnbMrv0xaFGB2houn2HtuxdkvVvbDOP9sTpTPDdBt6e2OawwW1ZtDMHg64SZ_-dQvwAlrMwIhjw5RdsptxSNwxrH11M_1rG7l4H9A'}","token":"{token}"}}')
                        result = json.loads(response.text)
                        if response.status_code == 200:
                            print("Đang gửi yêu cầu")
                        data = result['data']
                    except:
                        print('Yêu cầu thất bại, thử lại sau 3 giây')
                        sleep(3); 
                        continue
                    send_data = f'{{"google_token":"{'03AFcWeA6JMsHnFA92hVyaQGJepvRgKvByZ42vh8GhzCKAZNkn34uyhA8HDhiOseNFPlOCCy2L2IB7RZ4dw1vcHtqoY7gBqsvTJAhFRUryRWAjwcllWZ4Ghp10FBhLsrnB8gHVUywzurcmjEBEJJKW7HnFWnmn-KzxVQ-ZUse0A42fsKDH1uXKqeSGjMWQZRC4rxkhAeZ4t_CySMzRTq67Bdataa0K4LQNGH2C3K2uWuHE8YFlKRoHnvCW3fV4cxmuXdataQCs_CBYaTK-TDlDxNeKnKpQTKr66UB-GK952BZJ4qkA4kZMsTNSD3ADgF_r6xHXE8ZQFqVB37-7ubCDmJ1uljrQ9YyxgdL4dZw08wlUzY690d2vCJLk-824obisjBhGJJ0SIGzN7GPTyuEDMINoO63pXnR0vuc_L_7aLMLRjDidVycGdEH5GcBReqHV5fRO0G_VOjFuhy42feeShWafAFg1Sr4ePStylHfa00KDRVW_qrpQvQ7Rmx3kM-TOoK1CTSWKcOkkoAcwLlr5qm0qa_UKsNYjj6fJPyS1BSB-rrT4CaS7rWwyuBjRvpLiO43eUMIIC7xrmy1AGHb3-6hHoezlUxSPTEVMgL4HiNLFqXx_xJQFfOrca4AdWiAokITYHRtrILg2YuyaSkpYZ9FGKNYifF2NiK-VshkGEUr-PyIzm8tylMIfkHY8vSHU64aLcs2BxSvOANOejmKWbpDJVP69H_P7rQTuGv2bbSLTS4bRDQEfF3QEAtEtUBYd0RiZX-ks55U3RnOUyCrYh_ex87z7g4Y5MPdrQosKVzzRpfTthqwmvIRhmObYX2g5gt-6kXuxQav1r6HH9KZYLeoD0zyo47ejbmXAclE1KGkrEyb_Qn7LGTRlJOL2QOy91SlSfengQFgWQuB1Nx7pJmq4uhfSwUkpWQmlf6e4yYQq2dCFP9l3WdSN-aFgHPbzWbcXyLyphBt6IlS6ic7siDO4NGDi8gIl3gAAiLNbY-vBeOd1HJbLLYpEQjIYofLCGonGA0sRX6eoYIPRYKla2ZXxFE44lw1xAul4AygLa2mn8mWkhWf14vUQStwN3UlFbyi1OELnqsKua93r1N3m7D-94O280jtN7IuiFHYAF8TwHLkfH_6sB7pjep7oNVSGY0PD2rJ80VkM6t2PuJtxmQqovzlsOg2wwnAmt9fudJZkGuJGWwyjRzwJskkDxkeTjO3bwesWRM4dIbF6xUjrl5H-UPSBwFBqDps_BUIIVxivEeNnTi6je2KU9pepBeg2uBUXiqpts8j7U73Ax7ncs2rhVBTMvw02xzDfOnIlTKnOjvs4B0vuav3PbuthoXCiXKOmQEEg3kREAyhDCct_XNRrFAcmFaaJWKkmBLC6qqdyJdPnHzaMyK7mpDQiMiNEillv0i2T2iE6Geb8UXXkANupmW6jdVA-s9HeEhUXfy1yQQoL1AjQnp6g71SG1Hixs8tyu7kQxWr9AvucCCFUYlvVTUiUvAwLm1lP6cy31fkmkOC-U8wlUMz8qWdPVNVRRvNoSr5oI_u2Uqlf4i9FAEPs-eoQ9oEZEltzA-pfX7hBx77jxPbLhT2IPFC8OC0U-xNZTWKW2JUyh77_y3Yq2Ht7JkhHmdov1Rl1FYFZJs-KDrfc0mgCSuaiOO8FbE26IHYNXPNpbmN6khcH2m2oH6q8YfakCnknidz68-_Th0ey-67qxUoXifD1BAxfoKpPhYfU7P_YpskaQa_uGYw__c8H5TO7T1fF7dKEwST4TlIUZSzb5rPqhq-fISrYE1w-gNPlxVpBS5wx6sUw2fHsBtO_SC58e9qmWhtcf460f-SVAgH6fUUCSrqv2vxva_BfIdxjVpFip3XeKr3HQ5IPutvVhyQMEQ911HL32xP6lsLOIglyizH0RKJF7tSrr__p6BnbMrv0xaFGB2houn2HtuxdkvVvbDOP9sTpTPDdBt6e2OawwW1ZtDMHg64SZ_-dQvwAlrMwIhjw5RdsptxSNwxrH11M_1rG7l4H9A'}","token":"{token}","data":"{data}","type":"follow"}}'
                    try:
                        response = session.post('https://tikfollowers.com/api/free/send', headers={'accept': '*/*','accept-language': 'vi-VN,vi;q=0.9','content-type': 'text/plain;charset=UTF-8','origin': 'https://tikfollowers.com','priority': 'u=1, i','referer': 'https://tikfollowers.com/free-tiktok-followers','sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"','sec-ch-ua-mobile': '?0','sec-ch-ua-platform': '"Windows"','sec-fetch-dest': 'empty','sec-fetch-mode': 'cors','sec-fetch-site': 'same-origin','user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}, data=send_data)
                        result = json.loads(response.text)
                        if result["type"] == "success" :
                            print(f'Follow thành công vui lòng đợi 15 phút để Follow tiếp')
                            sleep(900)
                        elif result["type"] == "info" :
                            time = re.search(r'(\d+)\s*Minutes', result["message"])
                            print("Vui lòng chờ:", int(time.group(1)), "phút Follow tiếp")
                            sleep(int(time.group(1))*60)
                        else:
                            print(f'Lỗi server khi tăng Follow')
                            sleep(3);
                            continue
                    except:
                        print(f'Lỗi mạng khi tăng Follow')
                        sleep(3); 
                        continue
            def thread2():
                while True:
                    token = get_token()
                    try:
                        response = session.post('https://tikfollowers.com/api/free', headers={'accept': '*/*','accept-language': 'vi-VN,vi;q=0.9','content-type': 'text/plain;charset=UTF-8','origin': 'https://tikfollowers.com','priority': 'u=1, i','referer': 'https://tikfollowers.com/free-tiktok-followers','sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"','sec-ch-ua-mobile': '?0','sec-ch-ua-platform': '"Windows"','sec-fetch-dest': 'empty','sec-fetch-mode': 'cors','sec-fetch-site': 'same-origin','user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}, data=f'{{"type":"like","q":"{link}","google_token":"{'03AFcWeA6JMsHnFA92hVyaQGJepvRgKvByZ42vh8GhzCKAZNkn34uyhA8HDhiOseNFPlOCCy2L2IB7RZ4dw1vcHtqoY7gBqsvTJAhFRUryRWAjwcllWZ4Ghp10FBhLsrnB8gHVUywzurcmjEBEJJKW7HnFWnmn-KzxVQ-ZUse0A42fsKDH1uXKqeSGjMWQZRC4rxkhAeZ4t_CySMzRTq67Bdataa0K4LQNGH2C3K2uWuHE8YFlKRoHnvCW3fV4cxmuXdataQCs_CBYaTK-TDlDxNeKnKpQTKr66UB-GK952BZJ4qkA4kZMsTNSD3ADgF_r6xHXE8ZQFqVB37-7ubCDmJ1uljrQ9YyxgdL4dZw08wlUzY690d2vCJLk-824obisjBhGJJ0SIGzN7GPTyuEDMINoO63pXnR0vuc_L_7aLMLRjDidVycGdEH5GcBReqHV5fRO0G_VOjFuhy42feeShWafAFg1Sr4ePStylHfa00KDRVW_qrpQvQ7Rmx3kM-TOoK1CTSWKcOkkoAcwLlr5qm0qa_UKsNYjj6fJPyS1BSB-rrT4CaS7rWwyuBjRvpLiO43eUMIIC7xrmy1AGHb3-6hHoezlUxSPTEVMgL4HiNLFqXx_xJQFfOrca4AdWiAokITYHRtrILg2YuyaSkpYZ9FGKNYifF2NiK-VshkGEUr-PyIzm8tylMIfkHY8vSHU64aLcs2BxSvOANOejmKWbpDJVP69H_P7rQTuGv2bbSLTS4bRDQEfF3QEAtEtUBYd0RiZX-ks55U3RnOUyCrYh_ex87z7g4Y5MPdrQosKVzzRpfTthqwmvIRhmObYX2g5gt-6kXuxQav1r6HH9KZYLeoD0zyo47ejbmXAclE1KGkrEyb_Qn7LGTRlJOL2QOy91SlSfengQFgWQuB1Nx7pJmq4uhfSwUkpWQmlf6e4yYQq2dCFP9l3WdSN-aFgHPbzWbcXyLyphBt6IlS6ic7siDO4NGDi8gIl3gAAiLNbY-vBeOd1HJbLLYpEQjIYofLCGonGA0sRX6eoYIPRYKla2ZXxFE44lw1xAul4AygLa2mn8mWkhWf14vUQStwN3UlFbyi1OELnqsKua93r1N3m7D-94O280jtN7IuiFHYAF8TwHLkfH_6sB7pjep7oNVSGY0PD2rJ80VkM6t2PuJtxmQqovzlsOg2wwnAmt9fudJZkGuJGWwyjRzwJskkDxkeTjO3bwesWRM4dIbF6xUjrl5H-UPSBwFBqDps_BUIIVxivEeNnTi6je2KU9pepBeg2uBUXiqpts8j7U73Ax7ncs2rhVBTMvw02xzDfOnIlTKnOjvs4B0vuav3PbuthoXCiXKOmQEEg3kREAyhDCct_XNRrFAcmFaaJWKkmBLC6qqdyJdPnHzaMyK7mpDQiMiNEillv0i2T2iE6Geb8UXXkANupmW6jdVA-s9HeEhUXfy1yQQoL1AjQnp6g71SG1Hixs8tyu7kQxWr9AvucCCFUYlvVTUiUvAwLm1lP6cy31fkmkOC-U8wlUMz8qWdPVNVRRvNoSr5oI_u2Uqlf4i9FAEPs-eoQ9oEZEltzA-pfX7hBx77jxPbLhT2IPFC8OC0U-xNZTWKW2JUyh77_y3Yq2Ht7JkhHmdov1Rl1FYFZJs-KDrfc0mgCSuaiOO8FbE26IHYNXPNpbmN6khcH2m2oH6q8YfakCnknidz68-_Th0ey-67qxUoXifD1BAxfoKpPhYfU7P_YpskaQa_uGYw__c8H5TO7T1fF7dKEwST4TlIUZSzb5rPqhq-fISrYE1w-gNPlxVpBS5wx6sUw2fHsBtO_SC58e9qmWhtcf460f-SVAgH6fUUCSrqv2vxva_BfIdxjVpFip3XeKr3HQ5IPutvVhyQMEQ911HL32xP6lsLOIglyizH0RKJF7tSrr__p6BnbMrv0xaFGB2houn2HtuxdkvVvbDOP9sTpTPDdBt6e2OawwW1ZtDMHg64SZ_-dQvwAlrMwIhjw5RdsptxSNwxrH11M_1rG7l4H9A'}","token":"{token}"}}')
                        result = json.loads(response.text)
                        if response.status_code == 200:
                            print("Đang gửi yêu cầu")
                        data = result['data']
                    except:
                        print('Yêu cầu thất bại, thử lại sau 3 giây')
                        sleep(3); 
                        continue
                    send_data = f'{{"google_token":"{'03AFcWeA6JMsHnFA92hVyaQGJepvRgKvByZ42vh8GhzCKAZNkn34uyhA8HDhiOseNFPlOCCy2L2IB7RZ4dw1vcHtqoY7gBqsvTJAhFRUryRWAjwcllWZ4Ghp10FBhLsrnB8gHVUywzurcmjEBEJJKW7HnFWnmn-KzxVQ-ZUse0A42fsKDH1uXKqeSGjMWQZRC4rxkhAeZ4t_CySMzRTq67Bdataa0K4LQNGH2C3K2uWuHE8YFlKRoHnvCW3fV4cxmuXdataQCs_CBYaTK-TDlDxNeKnKpQTKr66UB-GK952BZJ4qkA4kZMsTNSD3ADgF_r6xHXE8ZQFqVB37-7ubCDmJ1uljrQ9YyxgdL4dZw08wlUzY690d2vCJLk-824obisjBhGJJ0SIGzN7GPTyuEDMINoO63pXnR0vuc_L_7aLMLRjDidVycGdEH5GcBReqHV5fRO0G_VOjFuhy42feeShWafAFg1Sr4ePStylHfa00KDRVW_qrpQvQ7Rmx3kM-TOoK1CTSWKcOkkoAcwLlr5qm0qa_UKsNYjj6fJPyS1BSB-rrT4CaS7rWwyuBjRvpLiO43eUMIIC7xrmy1AGHb3-6hHoezlUxSPTEVMgL4HiNLFqXx_xJQFfOrca4AdWiAokITYHRtrILg2YuyaSkpYZ9FGKNYifF2NiK-VshkGEUr-PyIzm8tylMIfkHY8vSHU64aLcs2BxSvOANOejmKWbpDJVP69H_P7rQTuGv2bbSLTS4bRDQEfF3QEAtEtUBYd0RiZX-ks55U3RnOUyCrYh_ex87z7g4Y5MPdrQosKVzzRpfTthqwmvIRhmObYX2g5gt-6kXuxQav1r6HH9KZYLeoD0zyo47ejbmXAclE1KGkrEyb_Qn7LGTRlJOL2QOy91SlSfengQFgWQuB1Nx7pJmq4uhfSwUkpWQmlf6e4yYQq2dCFP9l3WdSN-aFgHPbzWbcXyLyphBt6IlS6ic7siDO4NGDi8gIl3gAAiLNbY-vBeOd1HJbLLYpEQjIYofLCGonGA0sRX6eoYIPRYKla2ZXxFE44lw1xAul4AygLa2mn8mWkhWf14vUQStwN3UlFbyi1OELnqsKua93r1N3m7D-94O280jtN7IuiFHYAF8TwHLkfH_6sB7pjep7oNVSGY0PD2rJ80VkM6t2PuJtxmQqovzlsOg2wwnAmt9fudJZkGuJGWwyjRzwJskkDxkeTjO3bwesWRM4dIbF6xUjrl5H-UPSBwFBqDps_BUIIVxivEeNnTi6je2KU9pepBeg2uBUXiqpts8j7U73Ax7ncs2rhVBTMvw02xzDfOnIlTKnOjvs4B0vuav3PbuthoXCiXKOmQEEg3kREAyhDCct_XNRrFAcmFaaJWKkmBLC6qqdyJdPnHzaMyK7mpDQiMiNEillv0i2T2iE6Geb8UXXkANupmW6jdVA-s9HeEhUXfy1yQQoL1AjQnp6g71SG1Hixs8tyu7kQxWr9AvucCCFUYlvVTUiUvAwLm1lP6cy31fkmkOC-U8wlUMz8qWdPVNVRRvNoSr5oI_u2Uqlf4i9FAEPs-eoQ9oEZEltzA-pfX7hBx77jxPbLhT2IPFC8OC0U-xNZTWKW2JUyh77_y3Yq2Ht7JkhHmdov1Rl1FYFZJs-KDrfc0mgCSuaiOO8FbE26IHYNXPNpbmN6khcH2m2oH6q8YfakCnknidz68-_Th0ey-67qxUoXifD1BAxfoKpPhYfU7P_YpskaQa_uGYw__c8H5TO7T1fF7dKEwST4TlIUZSzb5rPqhq-fISrYE1w-gNPlxVpBS5wx6sUw2fHsBtO_SC58e9qmWhtcf460f-SVAgH6fUUCSrqv2vxva_BfIdxjVpFip3XeKr3HQ5IPutvVhyQMEQ911HL32xP6lsLOIglyizH0RKJF7tSrr__p6BnbMrv0xaFGB2houn2HtuxdkvVvbDOP9sTpTPDdBt6e2OawwW1ZtDMHg64SZ_-dQvwAlrMwIhjw5RdsptxSNwxrH11M_1rG7l4H9A'}","token":"{token}","data":"{data}","type":"like"}}'
                    try:
                        response = session.post('https://tikfollowers.com/api/free/send', headers={'accept': '*/*','accept-language': 'vi-VN,vi;q=0.9','content-type': 'text/plain;charset=UTF-8','origin': 'https://tikfollowers.com','priority': 'u=1, i','referer': 'https://tikfollowers.com/free-tiktok-followers','sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"','sec-ch-ua-mobile': '?0','sec-ch-ua-platform': '"Windows"','sec-fetch-dest': 'empty','sec-fetch-mode': 'cors','sec-fetch-site': 'same-origin','user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}, data=send_data)
                        result = json.loads(response.text)
                        if result["type"] == "success" :
                            print(f'Like thành công vui lòng đợi 15 phút để Like tiếp')
                            sleep(900)
                        elif result["type"] == "info" :
                            time = re.search(r'(\d+)\s*Minutes', result["message"])
                            print("Vui lòng chờ:", int(time.group(1)), "phút để Like tiếp")
                            sleep(int(time.group(1))*60)
                        else:
                            print(f'Lỗi server khi tăng Like')
                            sleep(3);
                            continue
                    except:
                        print(f'Lỗi mạng khi tăng Like')
                        sleep(3); 
                        continue

            threading.Thread(target=thread1).start()
            threading.Thread(target=thread2).start()

        else:
            print("Sai Lựa Chọn\n")
            continue
        break

    if luachon !=3 :
        while True:
            token = get_token()
            try:
                response = session.post('https://tikfollowers.com/api/free', headers={'accept': '*/*','accept-language': 'vi-VN,vi;q=0.9','content-type': 'text/plain;charset=UTF-8','origin': 'https://tikfollowers.com','priority': 'u=1, i','referer': 'https://tikfollowers.com/free-tiktok-followers','sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"','sec-ch-ua-mobile': '?0','sec-ch-ua-platform': '"Windows"','sec-fetch-dest': 'empty','sec-fetch-mode': 'cors','sec-fetch-site': 'same-origin','user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}, data=f'{{"type":"{kieu}","q":"{link}","google_token":"{'03AFcWeA6JMsHnFA92hVyaQGJepvRgKvByZ42vh8GhzCKAZNkn34uyhA8HDhiOseNFPlOCCy2L2IB7RZ4dw1vcHtqoY7gBqsvTJAhFRUryRWAjwcllWZ4Ghp10FBhLsrnB8gHVUywzurcmjEBEJJKW7HnFWnmn-KzxVQ-ZUse0A42fsKDH1uXKqeSGjMWQZRC4rxkhAeZ4t_CySMzRTq67Bdataa0K4LQNGH2C3K2uWuHE8YFlKRoHnvCW3fV4cxmuXdataQCs_CBYaTK-TDlDxNeKnKpQTKr66UB-GK952BZJ4qkA4kZMsTNSD3ADgF_r6xHXE8ZQFqVB37-7ubCDmJ1uljrQ9YyxgdL4dZw08wlUzY690d2vCJLk-824obisjBhGJJ0SIGzN7GPTyuEDMINoO63pXnR0vuc_L_7aLMLRjDidVycGdEH5GcBReqHV5fRO0G_VOjFuhy42feeShWafAFg1Sr4ePStylHfa00KDRVW_qrpQvQ7Rmx3kM-TOoK1CTSWKcOkkoAcwLlr5qm0qa_UKsNYjj6fJPyS1BSB-rrT4CaS7rWwyuBjRvpLiO43eUMIIC7xrmy1AGHb3-6hHoezlUxSPTEVMgL4HiNLFqXx_xJQFfOrca4AdWiAokITYHRtrILg2YuyaSkpYZ9FGKNYifF2NiK-VshkGEUr-PyIzm8tylMIfkHY8vSHU64aLcs2BxSvOANOejmKWbpDJVP69H_P7rQTuGv2bbSLTS4bRDQEfF3QEAtEtUBYd0RiZX-ks55U3RnOUyCrYh_ex87z7g4Y5MPdrQosKVzzRpfTthqwmvIRhmObYX2g5gt-6kXuxQav1r6HH9KZYLeoD0zyo47ejbmXAclE1KGkrEyb_Qn7LGTRlJOL2QOy91SlSfengQFgWQuB1Nx7pJmq4uhfSwUkpWQmlf6e4yYQq2dCFP9l3WdSN-aFgHPbzWbcXyLyphBt6IlS6ic7siDO4NGDi8gIl3gAAiLNbY-vBeOd1HJbLLYpEQjIYofLCGonGA0sRX6eoYIPRYKla2ZXxFE44lw1xAul4AygLa2mn8mWkhWf14vUQStwN3UlFbyi1OELnqsKua93r1N3m7D-94O280jtN7IuiFHYAF8TwHLkfH_6sB7pjep7oNVSGY0PD2rJ80VkM6t2PuJtxmQqovzlsOg2wwnAmt9fudJZkGuJGWwyjRzwJskkDxkeTjO3bwesWRM4dIbF6xUjrl5H-UPSBwFBqDps_BUIIVxivEeNnTi6je2KU9pepBeg2uBUXiqpts8j7U73Ax7ncs2rhVBTMvw02xzDfOnIlTKnOjvs4B0vuav3PbuthoXCiXKOmQEEg3kREAyhDCct_XNRrFAcmFaaJWKkmBLC6qqdyJdPnHzaMyK7mpDQiMiNEillv0i2T2iE6Geb8UXXkANupmW6jdVA-s9HeEhUXfy1yQQoL1AjQnp6g71SG1Hixs8tyu7kQxWr9AvucCCFUYlvVTUiUvAwLm1lP6cy31fkmkOC-U8wlUMz8qWdPVNVRRvNoSr5oI_u2Uqlf4i9FAEPs-eoQ9oEZEltzA-pfX7hBx77jxPbLhT2IPFC8OC0U-xNZTWKW2JUyh77_y3Yq2Ht7JkhHmdov1Rl1FYFZJs-KDrfc0mgCSuaiOO8FbE26IHYNXPNpbmN6khcH2m2oH6q8YfakCnknidz68-_Th0ey-67qxUoXifD1BAxfoKpPhYfU7P_YpskaQa_uGYw__c8H5TO7T1fF7dKEwST4TlIUZSzb5rPqhq-fISrYE1w-gNPlxVpBS5wx6sUw2fHsBtO_SC58e9qmWhtcf460f-SVAgH6fUUCSrqv2vxva_BfIdxjVpFip3XeKr3HQ5IPutvVhyQMEQ911HL32xP6lsLOIglyizH0RKJF7tSrr__p6BnbMrv0xaFGB2houn2HtuxdkvVvbDOP9sTpTPDdBt6e2OawwW1ZtDMHg64SZ_-dQvwAlrMwIhjw5RdsptxSNwxrH11M_1rG7l4H9A'}","token":"{token}"}}')
                result = json.loads(response.text)
                if response.status_code == 200:
                    print("Đang gửi yêu cầu")
                data = result['data']
            except:
                print('Yêu cầu thất bại, thử lại sau 3 giây')
                sleep(3); 
                continue
            send_data = f'{{"google_token":"{'03AFcWeA6JMsHnFA92hVyaQGJepvRgKvByZ42vh8GhzCKAZNkn34uyhA8HDhiOseNFPlOCCy2L2IB7RZ4dw1vcHtqoY7gBqsvTJAhFRUryRWAjwcllWZ4Ghp10FBhLsrnB8gHVUywzurcmjEBEJJKW7HnFWnmn-KzxVQ-ZUse0A42fsKDH1uXKqeSGjMWQZRC4rxkhAeZ4t_CySMzRTq67Bdataa0K4LQNGH2C3K2uWuHE8YFlKRoHnvCW3fV4cxmuXdataQCs_CBYaTK-TDlDxNeKnKpQTKr66UB-GK952BZJ4qkA4kZMsTNSD3ADgF_r6xHXE8ZQFqVB37-7ubCDmJ1uljrQ9YyxgdL4dZw08wlUzY690d2vCJLk-824obisjBhGJJ0SIGzN7GPTyuEDMINoO63pXnR0vuc_L_7aLMLRjDidVycGdEH5GcBReqHV5fRO0G_VOjFuhy42feeShWafAFg1Sr4ePStylHfa00KDRVW_qrpQvQ7Rmx3kM-TOoK1CTSWKcOkkoAcwLlr5qm0qa_UKsNYjj6fJPyS1BSB-rrT4CaS7rWwyuBjRvpLiO43eUMIIC7xrmy1AGHb3-6hHoezlUxSPTEVMgL4HiNLFqXx_xJQFfOrca4AdWiAokITYHRtrILg2YuyaSkpYZ9FGKNYifF2NiK-VshkGEUr-PyIzm8tylMIfkHY8vSHU64aLcs2BxSvOANOejmKWbpDJVP69H_P7rQTuGv2bbSLTS4bRDQEfF3QEAtEtUBYd0RiZX-ks55U3RnOUyCrYh_ex87z7g4Y5MPdrQosKVzzRpfTthqwmvIRhmObYX2g5gt-6kXuxQav1r6HH9KZYLeoD0zyo47ejbmXAclE1KGkrEyb_Qn7LGTRlJOL2QOy91SlSfengQFgWQuB1Nx7pJmq4uhfSwUkpWQmlf6e4yYQq2dCFP9l3WdSN-aFgHPbzWbcXyLyphBt6IlS6ic7siDO4NGDi8gIl3gAAiLNbY-vBeOd1HJbLLYpEQjIYofLCGonGA0sRX6eoYIPRYKla2ZXxFE44lw1xAul4AygLa2mn8mWkhWf14vUQStwN3UlFbyi1OELnqsKua93r1N3m7D-94O280jtN7IuiFHYAF8TwHLkfH_6sB7pjep7oNVSGY0PD2rJ80VkM6t2PuJtxmQqovzlsOg2wwnAmt9fudJZkGuJGWwyjRzwJskkDxkeTjO3bwesWRM4dIbF6xUjrl5H-UPSBwFBqDps_BUIIVxivEeNnTi6je2KU9pepBeg2uBUXiqpts8j7U73Ax7ncs2rhVBTMvw02xzDfOnIlTKnOjvs4B0vuav3PbuthoXCiXKOmQEEg3kREAyhDCct_XNRrFAcmFaaJWKkmBLC6qqdyJdPnHzaMyK7mpDQiMiNEillv0i2T2iE6Geb8UXXkANupmW6jdVA-s9HeEhUXfy1yQQoL1AjQnp6g71SG1Hixs8tyu7kQxWr9AvucCCFUYlvVTUiUvAwLm1lP6cy31fkmkOC-U8wlUMz8qWdPVNVRRvNoSr5oI_u2Uqlf4i9FAEPs-eoQ9oEZEltzA-pfX7hBx77jxPbLhT2IPFC8OC0U-xNZTWKW2JUyh77_y3Yq2Ht7JkhHmdov1Rl1FYFZJs-KDrfc0mgCSuaiOO8FbE26IHYNXPNpbmN6khcH2m2oH6q8YfakCnknidz68-_Th0ey-67qxUoXifD1BAxfoKpPhYfU7P_YpskaQa_uGYw__c8H5TO7T1fF7dKEwST4TlIUZSzb5rPqhq-fISrYE1w-gNPlxVpBS5wx6sUw2fHsBtO_SC58e9qmWhtcf460f-SVAgH6fUUCSrqv2vxva_BfIdxjVpFip3XeKr3HQ5IPutvVhyQMEQ911HL32xP6lsLOIglyizH0RKJF7tSrr__p6BnbMrv0xaFGB2houn2HtuxdkvVvbDOP9sTpTPDdBt6e2OawwW1ZtDMHg64SZ_-dQvwAlrMwIhjw5RdsptxSNwxrH11M_1rG7l4H9A'}","token":"{token}","data":"{data}","type":"{kieu}"}}'
            try:
                response = session.post('https://tikfollowers.com/api/free/send', headers={'accept': '*/*','accept-language': 'vi-VN,vi;q=0.9','content-type': 'text/plain;charset=UTF-8','origin': 'https://tikfollowers.com','priority': 'u=1, i','referer': 'https://tikfollowers.com/free-tiktok-followers','sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"','sec-ch-ua-mobile': '?0','sec-ch-ua-platform': '"Windows"','sec-fetch-dest': 'empty','sec-fetch-mode': 'cors','sec-fetch-site': 'same-origin','user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}, data=send_data)
                result = json.loads(response.text)
                if result["type"] == "success" :
                    print(f'{kieu} thành công vui lòng đợi 15 phút để {kieu} tiếp')
                    sleep(900)
                elif result["type"] == "info" :
                    time = re.search(r'(\d+)\s*Minutes', result["message"])
                    print("Vui lòng chờ:", int(time.group(1)), "phút để", kieu, "tiếp")
                    sleep(int(time.group(1))*60)
                else:
                    print(f'Lỗi server khi tăng {kieu}')
                    sleep(3);
                    continue
            except:
                print(f'Lỗi mạng khi tăng {kieu}')
                sleep(3); 
                continue

if __name__ == '__main__':
    try:
        main()
    except:
        pass
