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
        sess.cookies.update(pickle.loads(COOKIE_FILE.read_bytes()))
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
    logging.info("응답 헤더: %s", resp.headers)
    logging.info("응답 쿠키: %s", resp.cookies)
    logging.info("응답 본문: %s", resp.text[:500])  # 처음 500자만 출력
    logging.info("요청 URL: %s", resp.url)
    logging.info("요청 헤더: %s", resp.request.headers)
    logging.info("요청 본문: %s", resp.request.body)
    logging.info("요청 쿠키: %s", resp.request.headers.get("Cookie"))
    logging.info("요청 메소드: %s", resp.request.method)
    logging.info("요청 쿼리: %s", resp.request.url.split('?')[1] if '?' in resp.request.url else None)
    logging.info("요청 시간: %s", resp.elapsed)
    logging.info("요청 프로토콜: %s", resp.request.url.split(':')[0])


    sess.headers["Referer"] = BASE
    resp = sess.get(ATTEND_URL, timeout=10, allow_redirects=False)
    if resp.status_code != 200:
        _dump(resp.text, "login_redirect")
        raise RuntimeError("로그인 후 리다이렉트 실패")

    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_FILE.write_bytes(pickle.dumps(sess.cookies))
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
