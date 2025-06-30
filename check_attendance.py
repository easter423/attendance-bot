# check_attendance.py  — champ.hackers.com용 쿠키 고정 + 디버그
import os, re, json, pickle, logging, time, requests
from datetime import date
from pathlib import Path

# ── 로깅 ────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
DBG = Path("/tmp/toeic_debug"); DBG.mkdir(exist_ok=True)

def _dump(txt: str, tag: str):
    f = DBG / f"{tag}_{int(time.time())}.html"
    f.write_text(txt, encoding="utf-8")
    logging.info("💾  %s (%dB)", f, f.stat().st_size)

# ── URL / 파일 경로 ─────────────────────────────────
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
    "Accept": ("text/html,application/xhtml+xml,"
               "application/xml;q=0.9,*/*;q=0.8"),
    "Content-Type": "application/x-www-form-urlencoded",
}

ID = os.getenv("HACKERS_ID")
PW = os.getenv("HACKERS_PW")
if not (ID and PW):
    raise RuntimeError("환경변수 HACKERS_ID / HACKERS_PW 설정 필요")

# ── 세션 & 쿠키 로딩 ─────────────────────────────────
sess = requests.Session(); sess.headers.update(HEADERS)
if COOKIE_FILE.exists():
    try:
        sess.cookies.update(pickle.loads(COOKIE_FILE.read_bytes()))
        logging.info("✅ 쿠키 로드: %s", COOKIE_FILE)
    except Exception:
        COOKIE_FILE.unlink(True); logging.warning("쿠키 손상 → 삭제")

# ── 로그인 ──────────────────────────────────────────
def _login():
    # 1) CSRF 토큰 확보
    html = sess.get(LOGIN_PAGE, timeout=10).text
    tok = re.search(r'name="_token"\s+value="([^"]+)"', html)
    payload = {"_token": tok.group(1) if tok else "",
               "login_id": ID, "password": PW, "keep_login": "on"}
    # 2) 리다이렉트 모두 따라가며 세션 수립
    resp = sess.post(LOGIN_POST, data=payload, timeout=15,
                     allow_redirects=True)
    if resp.status_code not in (200, 302):
        _dump(resp.text, "login_fail"); raise RuntimeError("로그인 실패")

    # 3) champ.hackers.com 홈 GET → champ 도메인 쿠키 확보
    sess.get(CHAMP_HOME, timeout=10)
    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_FILE.write_bytes(pickle.dumps(sess.cookies))
    logging.info("🔑 새 쿠키 저장 (%s)", COOKIE_FILE)

# ── cal_list 파싱 ───────────────────────────────────
CAL_RE = re.compile(r"cal_list\s*=\s*({.*?})[;\n]", re.S)

def fetch_cal_list() -> dict:
    """HTML에서 cal_list={...} 추출; 없으면 재로그인 1회 더 시도"""
    for step in (1, 2):
        res = sess.get(ATTEND_URL, timeout=10, allow_redirects=False)
        logging.info("GET refund_page → %s", res.status_code)

        # 로그인 안 됐으면 서버가 302/logout 스크립트 반환
        if res.status_code in (301, 302) or "logout" in res.text:
            _dump(res.text, f"logout_{step}")
            logging.warning("세션 만료 → 재로그인(%d/2)", step)
            _login(); continue

        m = CAL_RE.search(res.text)
        if m:
            logging.info("✅ cal_list 추출 성공")
            return json.loads(m.group(1).replace("'", '"'))

        _dump(res.text, f"no_cal_list_{step}")
        logging.error("cal_list 미발견(%d/2) → 재로그인", step)
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
