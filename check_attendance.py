# check_attendance.py
import os, re, json, pickle, requests, logging, time
from datetime import date
from pathlib import Path

# ── 로깅 ───────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
DEBUG_DIR = Path("/tmp/toeic_debug"); DEBUG_DIR.mkdir(exist_ok=True)

def _dump(resp, tag):
    p = DEBUG_DIR / f"{tag}_{int(time.time())}.html"
    p.write_text(resp.text, encoding="utf-8")
    logging.info("💾  %s (%dB)", p, p.stat().st_size)

# ── URL & 파일 경로 ───────────────────────────────
BASE_URL   = "https://member.hackers.com"
LOGIN_PAGE = (f"{BASE_URL}/login?service_id=3090"
              "&return_url=https%3A%2F%2Fchamp.hackers.com%2F")
LOGIN_POST = f"{BASE_URL}/login"
CHAMP_HOME = "https://champ.hackers.com/"
ATTEND_URL = (CHAMP_HOME +
              "?r=champstudy&c=mypage/my_lec/my_lec_refund"
              "&sub=refund_class_view&odri_id=1493945512")
COOKIE_FILE = Path.home() / ".cache/toeic_bot_cookies.pkl"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/137.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": BASE_URL,
    "Referer": LOGIN_PAGE,
}

ID = os.getenv("HACKERS_ID")
PW = os.getenv("HACKERS_PW")
if not (ID and PW):
    raise RuntimeError("HACKERS_ID / HACKERS_PW 환경변수를 먼저 설정하세요")

# ── 세션 & 쿠키 로드 ───────────────────────────────
sess = requests.Session(); sess.headers.update(HEADERS)
if COOKIE_FILE.exists():
    try:
        sess.cookies.update(pickle.loads(COOKIE_FILE.read_bytes()))
        logging.info("✅ 쿠키 로드: %s", COOKIE_FILE)
    except Exception:
        logging.warning("⚠️  쿠키 파일 손상, 삭제")
        COOKIE_FILE.unlink(missing_ok=True)

# ── 로그인 ─────────────────────────────────────────
def _login():
    html = sess.get(LOGIN_PAGE, timeout=10).text
    token = re.search(r'name="_token"\s+value="([^"]+)"', html)
    payload = {"_token": token.group(1) if token else "",
               "login_id": ID, "password": PW, "keep_login": "on"}
    resp = sess.post(LOGIN_POST, data=payload, timeout=10,
                     allow_redirects=False)
    if resp.status_code not in (200, 302):
        _dump(resp, "login_fail"); raise RuntimeError("로그인 실패")
    # 302가 나오면 Location 따라가 사이트용 세션 쿠키 받기
    if resp.status_code == 302:
        loc = resp.headers.get("Location", "/")
        logging.info("→ 302 Location: %s", loc)
        sess.get(loc if loc.startswith("http") else BASE_URL + loc, timeout=10)
    # Champ 홈을 한 번 열어 champ.hackers.com 전용 쿠키 확보
    sess.get(CHAMP_HOME, timeout=10)
    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_FILE.write_bytes(pickle.dumps(sess.cookies))
    logging.info("🔑  새 쿠키 저장 완료 (%s)", COOKIE_FILE)

# ── cal_list 추출 ──────────────────────────────────
CAL_RE = re.compile(r"cal_list\s*=\s*({.*?})[;\n]", re.S)

def fetch_cal_list() -> dict:
    """세션 만료 감지 → 재로그인 후 cal_list 딕셔너리 반환"""
    for at in (1, 2):
        res = sess.get(ATTEND_URL, allow_redirects=False, timeout=10)
        logging.info("GET /refund_class_view → %s", res.status_code)
        if res.status_code in (301, 302):
            logging.warning("302 → 재로그인 (%d/2)", at)
            _dump(res, "redirect"); _login(); continue
        m = CAL_RE.search(res.text)
        if m:
            logging.info("✅ cal_list 추출 성공")
            return json.loads(m.group(1).replace("'", '"'))
        logging.error("cal_list 미발견 (%d/2)", at)
        _dump(res, "no_cal_list"); _login()
    raise RuntimeError("cal_list 추출 실패")

def check_attendance() -> bool:
    today = date.today().strftime("%Y-%m-%d")
    return today in fetch_cal_list()

# ── CLI 테스트 ─────────────────────────────────────
if __name__ == "__main__":
    try:
        print("✅" if check_attendance() else "❌", flush=True)
    except Exception as e:
        print("🚨", e, flush=True)
