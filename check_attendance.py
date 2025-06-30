# check_attendance.py  – 302 자동 추적 + Referer 동적 설정
import os, re, json, pickle, requests, logging, time
from datetime import date
from pathlib import Path

# ── 기본 로깅 ─────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
DBG = Path("/tmp/toeic_debug"); DBG.mkdir(exist_ok=True)

def _dump(txt, tag):
    p = DBG / f"{tag}_{int(time.time())}.html"
    p.write_text(txt, encoding="utf-8")
    logging.info("💾 %s (%dB)", p, p.stat().st_size)

# ── URL 구성 ────────────────────────────────────────
BASE         = "https://member.hackers.com"
CHAMP_HOME   = "https://champ.hackers.com/"
ATTEND_URL   = (CHAMP_HOME +
                "?r=champstudy&c=mypage/my_lec/my_lec_refund"
                "&sub=refund_class_view&odri_id=1493945512")
LOGIN_PAGE   = f"{BASE}/login?service_id=3090&return_url={ATTEND_URL}"
LOGIN_POST   = f"{BASE}/login"
COOKIE_FILE  = Path.home() / ".cache/toeic_bot_cookies.pkl"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/137.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,"
               "application/xml;q=0.9,*/*;q=0.8"),
    "Content-Type": "application/x-www-form-urlencoded",
}

ID, PW = os.getenv("HACKERS_ID"), os.getenv("HACKERS_PW")
if not (ID and PW):
    raise RuntimeError("HACKERS_ID / HACKERS_PW 환경변수를 설정하세요")

# ── 세션 + 쿠키 ──────────────────────────────────────
sess = requests.Session()
sess.headers.update(HEADERS)

if COOKIE_FILE.exists():
    try:
        #sess.cookies.update(pickle.loads(COOKIE_FILE.read_bytes()))
        sess.cookies.update('''_ga=GA1.1.168446314.1741787380; _ga_7QMSST0BPJ=GS1.1.1741787380.1.0.1741787384.56.0.0; _wp_uid=1-52ffbee01b67f3f8d52be23b88a25f5b-s1709510058.587801|windows_10|chrome-1u36b1v; _fcOM={"k":"cd5251dd5b3ff15e-dad03af1942c2bb73e3a5e","i":"39.125.69.2.9389608","r":1747574823604}; _ga_NJH9HGX12F=GS2.1.s1747641395$o2$g0$t1747641395$j60$l0$h0$d85a1TcmaFjaO6_ySBjQr5fPmVfDAjxZvxw; _gcl_gs=2.1.k1$i1748215597$u132735452; _gcl_aw=GCL.1748215601.Cj0KCQjwlrvBBhDnARIsAHEQgOTi8h7951XDuJaI0GozPuL4yKEpLJMJsE4raTIzkPnqZ_To14q7KqUaAl5XEALw_wcB; _gcl_au=1.1.1168483440.1749636584; PHPSESSID=v2uqakejk9vprd67s8j7daeq25; _TRK_CR=https%3A%2F%2Fchamp.hackers.com%2F; _TRK_UID=b95aab3563189a7fad5ba0691d09f5ac:7; _TRK_SID=146d6a062e4f69667930cd7df241afd7; _TRK_CQ=%3Fservice_id%3D3090%26return_url%3Dhttps%253A%252F%252Fchamp.hackers.com%252F%253Fr%253Dchampstudy%2526c%253Dmypage%252Fmy_lec%252Fmy_lec_refund%2526sub%253Drefund_class_view%2526odri_id%253D1493945512; XSRF-TOKEN=eyJpdiI6IlJsM1dZZlBZVWFcL0ZCWkZTYmpBYkVRPT0iLCJ2YWx1ZSI6ImFBdE4rSUtkWkZJeFJVY3h4OW1xbXRwa3I4WHozTzdHaWRhMUdieGswalI0XC9JUmxYcTZCcnRtZWpNaEJuUWY3YTJhTitCbnBFeUZtS3hwWnh2RUlPQT09IiwibWFjIjoiNzIwZGJkZDNjMTEzZDNjZDllY2EzYjQzYjI2MWUzOWQzNjhlOGE4NmI5NDVmZWU4M2VkOGFhYmJjMWViNjAwMiJ9; hackers=eyJpdiI6InBHWml1d0o2Y3Jpc1F1XC9ub2I0bHRBPT0iLCJ2YWx1ZSI6IitlM1lRRmVOSkozcUZLNG9SbVpCcTUyak9ZNXd6VlJwMVwvcGJpdmxsVE5TMThiRWVEV2hwNG5UVUF2R2MrYTgzUE9HSGVPOEdCVkRSR2U5bFZEUW56dz09IiwibWFjIjoiM2NlZmY3YmQ2NmY4NjVkM2Y5NmIzYTE1ZDMyOTViMWNkNGUwMzE5MDJkNTI2NmQwMjdmYjJiOWI0OTJmY2Q4MiJ9; _ga_QSLSW7WENJ=GS2.1.s1751278061$o76$g1$t1751284170$j53$l0$h0; cto_bundle=5KTAWF8lMkJ0ZVZUVnFyR2xyJTJGV2pkTGd2cHBFQ3ExekRVc1NCcUVFS0NaR3NyMkVJSkcwZU1qanA4eWVCc1prOXAySDkzcGtRTFJkRHpaTHp0M04wM2Y4TDNrN3l0Y29PTkhWYVlFclhHN3RJaVhnWWxpJTJGalVrQ0U3cDlrdEYwc0Fnam15TzVFb2t5WVNBYTdrdUxHejRJakNzY1F1S2JHVlBheFl4Y1VxbEdCJTJCUW95NXoyS1dOV3RaR3hGSXRDbFdRUkU5JTJGaEJJJTJGaWpDV2hxRGt5ekEyVGZkMGZ1NUFudWVWY1YzdTlJJTJCUzNTNGpHa0ZoWEVyYXRVaXMxdnZLbGI0MXBwOWpnJTJGNUJHd0RFM2dYOU02ZVlOZW1QZWpIbjVPTVlvSHBIMkh0NUNpdnlXcUlkQWgxeiUyQjgyNjBjUXdJcTlTaVlPUQ; _TRK_EX=3''')
        logging.info("✅ 쿠키 로드 완료")
    except Exception:
        COOKIE_FILE.unlink(True)

# ── 로그인 함수 ──────────────────────────────────────
def _login():
    # 1) CSRF 토큰
    sess.headers["Referer"] = LOGIN_PAGE
    html = sess.get(LOGIN_PAGE, timeout=10).text
    token = re.search(r'name="_token"\s+value="([^"]+)"', html)
    payload = {
        "_token": token.group(1) if token else "",
        "login_id": ID,
        "password": PW,
        "return_url": ATTEND_URL,
    }

    # 2) POST 로그인 (+302 자동 추적) → 쿠키 저장
    resp = sess.post(LOGIN_POST, data=payload,
                     timeout=20, allow_redirects=True)
    if resp.status_code not in (200, 302):
        _dump(resp.text, "login_fail")
        raise RuntimeError("로그인 실패")
    
    # resp 요청 및 응답 데이터 전체 출력(헤더 등)
    logging.info("로그인 성공: %s", resp.status_code)
    logging.info("resp: %s", resp.text)


    sess.headers["Referer"] = BASE
    resp = sess.get(ATTEND_URL, timeout=10, allow_redirects=False)
    if resp.status_code != 200:
        _dump(resp.text, "login_redirect")
        raise RuntimeError("로그인 후 리다이렉트 실패")

    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    #COOKIE_FILE.write_bytes(pickle.dumps(sess.cookies))
    logging.info("🔑 쿠키 저장 성공")

# ── cal_list 추출 ────────────────────────────────────
CAL_RE = re.compile(r"cal_list\s*=\s*({.*?})[;\n]", re.S)

def _attend_page():
    sess.headers["Referer"] = ATTEND_URL
    return sess.get(ATTEND_URL, timeout=10, allow_redirects=False)

def fetch_cal_list() -> dict:
    for step in (1, 2):
        res = _attend_page()
        logging.info("GET 출석페이지 → %s", res.status_code)

        if res.status_code in (301, 302) or "logout" in res.text:
            _dump(res.text, f"logout_{step}")
            _login(); continue

        m = CAL_RE.search(res.text)
        if m:
            logging.info("✅ cal_list 추출 성공")
            return json.loads(m.group(1).replace("'", '"'))

        _dump(res.text, f"no_cal_list_{step}")
        _login()
    raise RuntimeError("cal_list 추출 실패")

def check_attendance() -> bool:
    today = date.today().strftime("%Y-%m-%d")
    return today in fetch_cal_list()

# ── CLI 테스트 ──────────────────────────────────────
if __name__ == "__main__":
    try:
        print("✅" if check_attendance() else "❌", flush=True)
    except Exception as e:
        print("🚨", e, flush=True)
