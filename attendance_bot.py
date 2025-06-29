# -*- coding: utf-8 -*-
"""
Hackers Champ – ‘환급 출석체크’ 오늘 출석 여부 확인 스크립트
1) DevTools → Copy as cURL 로 복사한 쿠키‧헤더 문자열 붙여넣기
2) 실행 : python check_attendance.py
"""

import requests, urllib.parse
from bs4 import BeautifulSoup            # HTML 파싱용 :contentReference[oaicite:0]{index=0}
from datetime import date, timedelta
from pprint import pprint                # 디버그용 (선택)

# ────────────────────────────────────────────────────────────────
# 1. 세션‧헤더‧쿠키 세팅
# ────────────────────────────────────────────────────────────────
URL = "https://champ.hackers.com/"
ODRI_ID = "1493945512"   # 수강권 고유번호 (필요 시 변경)

# (A) 크롬 ‘Request Headers’ 그대로 복사 → 필요 없는 SEC- 계열은 지워도 무방
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://champ.hackers.com",
    "Referer": ("https://champ.hackers.com/?r=champstudy&c=mypage/my_lec/"
                "my_lec_refund&sub=refund_class_view&odri_id={ODRI_ID}"),
}

# (B) ‘Cookie’ 헤더 전체 문자열을 그대로 붙여넣어도 되지만,
#     requests 는 쿠키를 dict 로 주는 편이 안전하다 :contentReference[oaicite:1]{index=1}
COOKIE_STRING = """
_ga=GA1.1.168446314.1741787380; _ga_7QMSST0BPJ=GS1.1.1741787380.1.0.1741787384.56.0.0; _wp_uid=1-52ffbee01b67f3f8d52be23b88a25f5b-s1709510058.587801|windows_10|chrome-1u36b1v; _fcOM={"k":"cd5251dd5b3ff15e-dad03af1942c2bb73e3a5e","i":"39.125.69.2.9389608","r":1747570494117}; _ga_NJH9HGX12F=GS2.1.s1747641395$o2$g0$t1747641395$j60$l0$h0$d85a1TcmaFjaO6_ySBjQr5fPmVfDAjxZvxw; _gcl_gs=2.1.k1$i1748215597$u132735452; _gcl_aw=GCL.1748215601.Cj0KCQjwlrvBBhDnARIsAHEQgOTi8h7951XDuJaI0GozPuL4yKEpLJMJsE4raTIzkPnqZ_To14q7KqUaAl5XEALw_wcB; _ga_QSLSW7WENJ=deleted; _ga_QSLSW7WENJ=deleted; _gcl_au=1.1.1168483440.1749636584; hackersID=eyJpdiI6Im93QjRIQlJUNkxuMTBqVDIrNVdPZ1E9PSIsInZhbHVlIjoiT1p4a1BqWVFsVG1yZldkd0ZtYVpiRzlUXC9Wa3FsdVhlb3ljQ1VyXC8xcWp0N0l3eFwva2tndDZXVzV2UEFTM0VCY3FaWU9WenJoanJqa0xZWlFER3QxcHlRVVRWMEtNbFRPVnhPK2ZId2tUWWM9IiwibWFjIjoiMDE3MTEyNmIzYTc0ZWI5OGZlZTIwMzBmYzE4ZWYzYWMyNjU1YzQxNmZjY2M3YjU5NDMzZjBkMTUwZjJiN2M4NyJ9; hackersCCD=1; hackersFLAG=100%2C200%2C300%2C400; hackersNICK=7ZWY6rG07JiB; visited_page[0]=%7B%22lec_id%22%3A%2215069%22%2C%22uri%22%3A%22%5C%2F%3Fr%3Dchampstudy%26m%3Dlecture%26sub%3Ddetail%26lec_id%3D15069%22%2C%22timestamp%22%3A%221750672597_9%22%7D; PHPSESSID=v2uqakejk9vprd67s8j7daeq25; _TRK_CR=https%3A%2F%2Fchamp.hackers.com%2F; XSRF-TOKEN=eyJpdiI6IkcrVlQxTGNxNkJTS3pmbHFMTG4raFE9PSIsInZhbHVlIjoiUnNKTENNbnVVS3ZObDdldVEreFhxZHhrKzRpWXBrUE9RdkxrUkl2ZlwvQlVuTzBtdFo0ZjJJS01sR1o1NlwvOSthNTN4bnFlcHVWQXg1SEgzdjBNYlh5UT09IiwibWFjIjoiYzgyMTYzNGZkMjcyYjA3ZGJhMDY5NDcwYzhlZWRkYjE5NTNhZDJhMDBmODFlNjJjYzI4MDRiNGExNDk4N2U2MCJ9; hackers=eyJpdiI6IkNRd0wyRUhsMHNkeVpSVEFkcUN2Q3c9PSIsInZhbHVlIjoiYm1IS1wvaHB2VlwveVFaRVEzcFNLajZvY1ZPMGZiZGg3bWpCdldpbzNZRDh6WXl4T0RTTHpyelJXMTR6TDJGS3piU3laTHVIMVY5VU03bVVaQXZPMnR1QT09IiwibWFjIjoiZjE3YTkzNjJkM2VkYmQxYTkxZmE5YmI0NTc5MzI5NjBkZTZiMmJhNGVkZDc2OGVjNWExYmIyZTc1OWRkZmNkMiJ9; _TRK_UID=18bb292ef92a4f10a0ce9e6fdeda9c11:68; _TRK_SID=c1796ae37c06160ab40b8074e23b9d0c; _TRK_CQ=%3Fr%3Dchampstudy%26c%3Dmypage%2Fmy_lec%2Fmy_lec_refund%26sub%3Drefund_class_view%26odri_id%3D1493945512; _TRK_EX=11; cto_bundle=cTHd-V8lMkJ0ZVZUVnFyR2xyJTJGV2pkTGd2cHBFQzgxNEJxaFVJUVNVcFR2aWdmMEg3bWtHN0ZkejlNVnF4ZEF0eGZmc21jVzZ1eHJhQ1hPWmh4Y3VaY3FJOVM5U25odVJpWXJIZUNjeXhqYmMwc3I0UEpUcWR3UTUxWkpOZmNJYld4MGlEN280RjNDUFhENDlJTWxmZnpYeExieWFCeUFwVW5MSjZCTTclMkZHcjg4dTBwJTJCZzBaZkN4ZDI1OEdPdzJReEpGYUJJaW1GSjd6Y1FRaGZtNXRGM25uQU1ySTQzcnVqVyUyRkJ6SElvUTdObW5GNTRIZndwMENBNkxWSVdxZEpyU2Y5N3UlMkJ1MFR1MEs1VWFYWSUyQjhwTmZYRFJxcHUlMkJUbDM2R0FoekI1OU14d0ttc2dyMmpLN3hpV2VoZ1lrT2poYlJaSWpocnU; _ga_QSLSW7WENJ=GS2.1.s1751206186$o73$g1$t1751209290$j60$l0$h0
"""
cookies = {
    k.strip(): v for k, v in (
        token.split("=", 1) for token in COOKIE_STRING.strip().split("; ") if "=" in token
    )
}

sess = requests.Session()
sess.headers.update(HEADERS)
sess.cookies.update(cookies)                # 세션에 쿠키 주입 :contentReference[oaicite:2]{index=2}

# ────────────────────────────────────────────────────────────────
# 2. POST 파라미터(폼 데이터) 구성
#    - 최근 35일 간 mission_list[YYYY-MM-DD]=Y
# ────────────────────────────────────────────────────────────────
TODAY = date.today().strftime("%Y-%m-%d")     # 예: '2025-06-30'
# TODAY 하루 전
YESTERDAY = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
#exit()
#TODAY= YESTERDAY  # 테스트용으로 어제 날짜로 설정
# ── 3) POST 폼 데이터 구성 ──
payload = [
    ("r", "champstudy"),
    ("m", "mypage"),
    ("a", "attend_list.ajax"),
    ("now_date", TODAY),
]
encoded = urllib.parse.urlencode(payload, safe="[]")

# ── 4) 요청 & JSON 파싱 ──
try:
    resp = sess.post(URL, data=encoded, timeout=15)
    resp.raise_for_status()            # HTTP 오류 검증
    data = resp.json()                 # {"list": "...", "check_date_list": {...}}
except Exception as e:
    print("🔴 요청 실패 또는 JSON 파싱 오류:", e)
    exit(1)

# ── 5) 오늘 출석 여부 판별 ──
attended = TODAY in data.get("check_date_list", {})
if attended:
    print(f"✅ {TODAY} 출석 완료!")
else:
    print(f"❌ {TODAY} 아직 미출석입니다.")

# ── 6) (선택) 주간 HTML 리스트 저장 ──
with open(f"week_{TODAY}.html", "w", encoding="utf-8") as f:
    f.write(data.get("list", ""))
