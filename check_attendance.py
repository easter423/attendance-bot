# check_attendance.py ─ cal_list 기반 출석 확인
import re, json, requests
from datetime import date

URL = ("https://champ.hackers.com/"
       "?r=champstudy&c=mypage/my_lec/my_lec_refund"
       "&sub=refund_class_view&odri_id=1493945512")

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/137.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

COOKIE_STRING = """
_ga=GA1.1.168446314.1741787380; _ga_7QMSST0BPJ=GS1.1.1741787380.1.0.1741787384.56.0.0; _wp_uid=1-52ffbee01b67f3f8d52be23b88a25f5b-s1709510058.587801|windows_10|chrome-1u36b1v; _fcOM={"k":"cd5251dd5b3ff15e-dad03af1942c2bb73e3a5e","i":"39.125.69.2.9389608","r":1747570494117}; _ga_NJH9HGX12F=GS2.1.s1747641395$o2$g0$t1747641395$j60$l0$h0$d85a1TcmaFjaO6_ySBjQr5fPmVfDAjxZvxw; _gcl_gs=2.1.k1$i1748215597$u132735452; _gcl_aw=GCL.1748215601.Cj0KCQjwlrvBBhDnARIsAHEQgOTi8h7951XDuJaI0GozPuL4yKEpLJMJsE4raTIzkPnqZ_To14q7KqUaAl5XEALw_wcB; _ga_QSLSW7WENJ=deleted; _ga_QSLSW7WENJ=deleted; _gcl_au=1.1.1168483440.1749636584; hackersID=eyJpdiI6Im93QjRIQlJUNkxuMTBqVDIrNVdPZ1E9PSIsInZhbHVlIjoiT1p4a1BqWVFsVG1yZldkd0ZtYVpiRzlUXC9Wa3FsdVhlb3ljQ1VyXC8xcWp0N0l3eFwva2tndDZXVzV2UEFTM0VCY3FaWU9WenJoanJqa0xZWlFER3QxcHlRVVRWMEtNbFRPVnhPK2ZId2tUWWM9IiwibWFjIjoiMDE3MTEyNmIzYTc0ZWI5OGZlZTIwMzBmYzE4ZWYzYWMyNjU1YzQxNmZjY2M3YjU5NDMzZjBkMTUwZjJiN2M4NyJ9; hackersCCD=1; hackersFLAG=100%2C200%2C300%2C400; hackersNICK=7ZWY6rG07JiB; visited_page[0]=%7B%22lec_id%22%3A%2215069%22%2C%22uri%22%3A%22%5C%2F%3Fr%3Dchampstudy%26m%3Dlecture%26sub%3Ddetail%26lec_id%3D15069%22%2C%22timestamp%22%3A%221750672597_9%22%7D; PHPSESSID=v2uqakejk9vprd67s8j7daeq25; _TRK_CR=https%3A%2F%2Fchamp.hackers.com%2F; _TRK_CQ=%3Fr%3Dchampstudy%26c%3Dmypage%2Fmy_lec%2Fmy_lec_refund%26sub%3Drefund_class_view%26odri_id%3D1493945512; XSRF-TOKEN=eyJpdiI6ImUrNE5reE5QM1o1anZQcVwvVlNJTUVBPT0iLCJ2YWx1ZSI6ImVkNHZUWHRjY1wvVjFPZmxcL0YzT3VJOHhwN1RHNSt0N1dpXC9UUmxpY092NFpGM0c4NzhJaHVPckRPR2Q5NlBrdFhTYlZsUWNtWlE0bTYrZitOZFpDRjN3PT0iLCJtYWMiOiI2OWQ3MmJjNjFmNzcxNjJkZjk0YTFiYmJmNzU0ZGViZTk5ODcyNjFlMmQyNGJhMWVlMTM0MmIwNzFjYzE4YWE5In0%3D; hackers=eyJpdiI6Ik9RRFQxXC9tUHI2MHRjODhVeXJWazV3PT0iLCJ2YWx1ZSI6Ims1blBEcHhDXC9ZVjVQR09BSURrNWdiSVozaWxhRmRHTGtDTUxYd2oxYUpmZVAxK0R3alpwMTJvVnZ5ZFZSMkZYaEtQZ2M5cmgweFdqeVRhZXlsXC9FM2c9PSIsIm1hYyI6ImFiYWI3YmRhODc1YWNhMWZlNjNhMDU3OGE5ZDdhZGFmZTRjZjhmN2Q4ZjRlMWNhZWFiNzdmOWZhMTMyNGZkZGEifQ%3D%3D; _TRK_UID=18bb292ef92a4f10a0ce9e6fdeda9c11:70; _TRK_SID=e50dd7bd4edd09d3a157abf23054470d; _TRK_EX=4; _ga_QSLSW7WENJ=GS2.1.s1751248867$o75$g1$t1751249487$j17$l0$h0; cto_bundle=nrmU2V8lMkJ0ZVZUVnFyR2xyJTJGV2pkTGd2cHBFSmVKUVgyYlJlakM5eDZLaE1mSzg1N2tnNWs0aHE3VmNOREh4N2hBQUNZWXNoalNpa2tLaTZnbEVXOHZabXpySVRqc2d1a05uVk00TGNpS3lwN2UzZG1WanglMkZJT2tjOHRvY2FuU0YwRExjWmFLb3hmS3A0UzNyaFV5QWpiTTY4MkdPRXFZSSUyRmQzbnFNd2FUaFk1UXNUOXBvajE2b0VHZ01MbnZCMEV4SzUyZXFYSXFlaFJySmlFcmUyYkd6bFpiVnBNRnJnNGpDRjE2Rk5JZWxVTWVBV1FWRmE3ZFNWdnlVck5UVCUyQkhvWksyMkZNSDRzM0ZaYnU2RE05a0FDc0RBcWJqVEtySWFNRzI0dSUyQkkyV0REV1UyNEF3ek5KSGVybmFxTTdkTFZWN1Naeg
""".strip()
cookies = {k: v for k, v in 
           (tok.split("=", 1) for tok in COOKIE_STRING.split("; ") if "=" in tok)}

sess = requests.Session()
sess.headers.update(HEADERS)
sess.cookies.update(cookies)          # 세션에 쿠키 주입

def check_attendance() -> bool:
    """오늘 날짜가 cal_list 안에 있으면 True(출석), 없으면 False(미출석)"""
    resp = sess.get(URL, timeout=15)
    resp.raise_for_status()                      # 4xx / 5xx 예외 발생 :contentReference[oaicite:3]{index=3}

    # ① cal_list = {...};  부분 정규식 추출
    m = re.search(r"cal_list\s*=\s*(\{[^}]+\})", resp.text)
    if not m:
        raise RuntimeError("cal_list 객체를 찾을 수 없습니다.")
    js_obj = m.group(1)

    # ② JSON 파싱 → dict
    try:
        cal_dict = json.loads(js_obj)           # 이미 "key":"Y" 형태라 그대로 파싱
    except json.JSONDecodeError as e:
        # 따옴표 혼합 등으로 실패 시 대체 로직
        cal_dict = json.loads(js_obj.replace("'", '"'), strict=False)

    # ③ 출석 여부
    today = date.today().strftime("%Y-%m-%d")
    return today in cal_dict                    # 포함돼 있으면 이미 출석한 날
    
def fetch_cal_list() -> dict:
    """cal_list 전체 JSON 반환 (날짜 → 'Y')."""
    resp = sess.get(URL, timeout=15)
    resp.raise_for_status()
    m = re.search(r"cal_list\s*=\s*(\{[^}]+\})", resp.text)
    if not m:
        raise RuntimeError("cal_list 객체를 찾을 수 없습니다.")
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return json.loads(m.group(1).replace("'", '"'), strict=False)

if __name__ == "__main__":
    try:
        attended = check_attendance()
        print("✅ 이미 출석했습니다!" if attended else "❌ 아직 미출석입니다.")
    except Exception as err:
        print("🚨 오류:", err)
