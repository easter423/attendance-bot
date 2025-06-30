# check_attendance.py
import os, re, json, pickle, requests, logging, time
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
DEBUG_DIR = Path("/tmp/toeic_debug"); DEBUG_DIR.mkdir(exist_ok=True)

def _dump(text: str, tag: str):
    p = DEBUG_DIR / f"{tag}_{int(time.time())}.html"
    p.write_text(text, encoding="utf-8")
    logging.info("💾  %s (%dB)", p, p.stat().st_size)

BASE_URL   = "https://member.hackers.com"
LOGIN_PAGE = f"{BASE_URL}/login?service_id=3090&return_url=https%3A%2F%2Fchamp.hackers.com%2F"
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
    raise RuntimeError("❗ HACKERS_ID / HACKERS_PW 환경변수를 설정하세요")

sess = requests.Session(); sess.headers.update(HEADERS)
if COOKIE_FILE.exists():
    try:
        sess.cookies.update(pickle.loads(COOKIE_FILE.read_bytes()))
        logging.info("✅ 쿠키 로드: %s", COOKIE_FILE)
    except Exception:
        logging.warning("⚠️ 쿠키 파일 손상, 삭제합니다"); COOKIE_FILE.unlink(True)

def _login():
    html = sess.get(LOGIN_PAGE, timeout=10).text
    match = re.search(r'name="_token"\s+value="([^"]+)"', html)
    token = match.group(1) if match else ""
    payload = {"_token": token, "login_id": ID, "password": PW, "keep_login": "on"}
    resp = sess.post(LOGIN_POST, data=payload, timeout=10, allow_redirects=False)
    if resp.status_code not in (200,302):
        _dump(resp.text, "login_fail"); raise RuntimeError("로그인 실패")
    if resp.status_code == 302:
        loc = resp.headers.get("Location", "/")
        logging.info("→ 302 리다이렉션: %s", loc)
        sess.get(loc if loc.startswith("http") else BASE_URL+loc, timeout=10)
    sess.get(CHAMP_HOME, timeout=10)  # champ.hackers.com용 쿠키 확보
    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_FILE.write_bytes(pickle.dumps(sess.cookies))
    logging.info("🔑 새 쿠키 저장: %s", COOKIE_FILE)

CAL_RE = re.compile(r"cal_list\s*=\s*({.*?})[;\n]", re.S)

def fetch_cal_list() -> dict:
    for attempt in (1,2):
        res = sess.get(ATTEND_URL, allow_redirects=False, timeout=10)
        logging.info("GET 페이지 → %s", res.status_code)
        if res.status_code in (301,302):
            _dump(res.text, "redirect")
            logging.warning("세션 만료 추정(%d/2) → 재로그인", attempt)
            _login()
            continue
        m = CAL_RE.search(res.text)
        if m:
            logging.info("✅ cal_list 추출 성공")
            return json.loads(m.group(1).replace("'", '"'))
        logging.error("cal_list 없음(%d/2)", attempt)
        _dump(res.text, "no_cal_list")
        _login()
    raise RuntimeError("cal_list 추출 실패")

def check_attendance() -> bool:
    today = date.today().strftime("%Y-%m-%d")
    return today in fetch_cal_list()

if __name__ == "__main__":
    try:
        print("✅ 출석 완료" if check_attendance() else "❌ 미출석", flush=True)
    except Exception as e:
        print("🚨 오류:", e, flush=True)
