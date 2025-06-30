# check_attendance.py  –  자동 로그인 + 쿠키 영구화 + 디버그 로깅
import os, re, json, pickle, requests, logging, time
from datetime import date
from pathlib import Path

# ── 로그 설정 ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

DEBUG_DIR = Path("/tmp/toeic_debug")
DEBUG_DIR.mkdir(exist_ok=True)

def _dump(resp, tag):
    """문제 응답을 /tmp/toeic_debug/ 이하에 저장"""
    fname = DEBUG_DIR / f"{tag}_{int(time.time())}.html"
    try:
        fname.write_text(resp.text, encoding="utf-8")
        logging.info("💾  %s 저장 (%d바이트)", fname, fname.stat().st_size)
    except Exception as e:
        logging.error("파일 저장 실패: %s", e)

# ── 상수 — URL & 쿠키 파일 위치 ──────────────────────
BASE_URL   = "https://member.hackers.com"
LOGIN_PAGE = (f"{BASE_URL}/login?service_id=3090"
              "&return_url=https%3A%2F%2Fchamp.hackers.com%2F")
LOGIN_POST = f"{BASE_URL}/login"
ATTEND_URL = ("https://champ.hackers.com/"
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
    raise RuntimeError("❗  HACKERS_ID / HACKERS_PW 환경변수를 설정하세요")

# ── 세션 & 쿠키 로딩 ───────────────────────────────────
sess = requests.Session()
sess.headers.update(HEADERS)
if COOKIE_FILE.exists():
    try:
        sess.cookies.update(pickle.loads(COOKIE_FILE.read_bytes()))
        logging.info("✅ 쿠키 파일 로드: %s", COOKIE_FILE)
    except Exception:
        logging.warning("⚠️  쿠키 파일 손상, 삭제 후 재로그인")
        COOKIE_FILE.unlink(missing_ok=True)

# ── 로그인 함수 ───────────────────────────────────────
def _login():
    html = sess.get(LOGIN_PAGE, timeout=10).text
    token_m = re.search(r'name="_token"\s+value="([^"]+)"', html)
    payload = {
        "_token": token_m.group(1) if token_m else "",
        "login_id": ID,
        "password": PW,
        "keep_login": "on",
    }
    r = sess.post(LOGIN_POST, data=payload, allow_redirects=False, timeout=10)
    if r.status_code not in (200, 302):
        _dump(r, "login_fail")
        raise RuntimeError(f"로그인 실패: {r.status_code}")
    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_FILE.write_bytes(pickle.dumps(sess.cookies))
    logging.info("🔑  새 쿠키 저장 완료 (%s)", COOKIE_FILE)

# ── cal_list 추출 ────────────────────────────────────
CAL_RE = re.compile(r"cal_list\s*=\s*({.*?})[;\n]", re.S)

def fetch_cal_list() -> dict:
    """
    cal_list 전체 딕셔너리 반환.
    세션 만료 시 자동 재로그인 후 1회 재시도.
    """
    for attempt in (1, 2):              # 최대 두 번 시도
        res = sess.get(ATTEND_URL, allow_redirects=False, timeout=10)
        logging.info("GET %s → %s", ATTEND_URL, res.status_code)

        if res.status_code in (301, 302):
            logging.warning("302 리다이렉트 → 세션 만료, 재로그인 시도(%d/2)", attempt)
            _dump(res, "redirect")
            _login()
            continue

        m = CAL_RE.search(res.text)
        if m:
            logging.info("✅ cal_list 추출 성공")
            return json.loads(m.group(1).replace("'", '"'))

        logging.error("cal_list 미발견(%d/2), HTML 저장", attempt)
        _dump(res, "no_cal_list")
        _login()
    raise RuntimeError("cal_list 추출 실패")

# ── 오늘 출석 여부 ───────────────────────────────────
def check_attendance() -> bool:
    today = date.today().strftime("%Y-%m-%d")
    return today in fetch_cal_list()

# ── CLI 진입점 ───────────────────────────────────────
if __name__ == "__main__":
    try:
        ok = check_attendance()
        print("✅ 출석 완료" if ok else "❌ 아직 미출석", flush=True)
    except Exception as e:
        print("🚨 오류:", e, flush=True)
