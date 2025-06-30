# check_attendance.py  – service_id · return_url 포함 & 재요청 검증
import os, re, json, pickle, requests, logging, time
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
DBG = Path("/tmp/toeic_debug"); DBG.mkdir(exist_ok=True)

def _dump(text: str, tag: str):
    f = DBG / f"{tag}_{int(time.time())}.html"
    f.write_text(text, encoding="utf-8"); logging.info("💾 %s (%dB)", f, f.stat().st_size)

# ── URL · 경로 ──────────────────────────────────────
BASE_URL   = "https://member.hackers.com"
LOGIN_PAGE = f"{BASE_URL}/login?service_id=3090&return_url=https%3A%2F%2Fchamp.hackers.com%2F"
LOGIN_POST = f"{BASE_URL}/login"
CHAMP_HOME = "https://champ.hackers.com/"
ATTEND_URL = (CHAMP_HOME +
              "?r=champstudy&c=mypage/my_lec/my_lec_refund"
              "&sub=refund_class_view&odri_id=1493945512")
COOKIE_FILE = Path.home() / ".cache/toeic_bot_cookies.pkl"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
    "Content-Type": "application/x-www-form-urlencoded",
}

ID, PW = os.getenv("HACKERS_ID"), os.getenv("HACKERS_PW")
if not (ID and PW):
    raise RuntimeError("HACKERS_ID / HACKERS_PW 환경변수 필요")

# ── 세션 & 쿠키 ───────────────────────────────────────
sess = requests.Session(); sess.headers.update(HEADERS)
if COOKIE_FILE.exists():
    try:
        sess.cookies.update(pickle.loads(COOKIE_FILE.read_bytes()))
        logging.info("✅ 쿠키 로드: %s", COOKIE_FILE)
    except Exception:
        COOKIE_FILE.unlink(True); logging.warning("⚠️ 쿠키 파일 손상 삭제")

# ── 로그인 ───────────────────────────────────────────
def _login():
    html = sess.get(LOGIN_PAGE, timeout=10).text
    token = re.search(r'name="_token"\s+value="([^"]+)"', html)
    payload = {
        "_token": token.group(1) if token else "",
        "login_id": ID,
        "password": PW,
        "keep_login": "on",
        "service_id": "3090",
        "return_url": "https://champ.hackers.com/",
    }
    resp = sess.post(LOGIN_POST, data=payload, timeout=20, allow_redirects=True)
    if resp.status_code not in (200, 302):
        _dump(resp.text, "login_fail"); raise RuntimeError("로그인 실패")
    sess.get(CHAMP_HOME, timeout=10)                 # champ 도메인 쿠키 수령
    # 로그인 정상 여부 1차 검증
    chk = sess.get(ATTEND_URL, timeout=10, allow_redirects=False)
    if "logout" in chk.text or chk.status_code in (301, 302):
        _dump(chk.text, "login_still_logout"); raise RuntimeError("로그인 세션 획득 실패")
    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_FILE.write_bytes(pickle.dumps(sess.cookies))
    logging.info("🔑 새 쿠키 저장: %s", COOKIE_FILE)

# ── cal_list 파싱 ───────────────────────────────────
CAL_RE = re.compile(r"cal_list\s*=\s*({.*?})[;\n]", re.S)

def _get_page():
    return sess.get(ATTEND_URL, timeout=10, allow_redirects=False)

def fetch_cal_list() -> dict:
    """HTML의 cal_list를 추출. 세션 만료 시 재로그인 후 재시도."""
    for step in (1, 2):
        res = _get_page()
        logging.info("GET refund_page → %s", res.status_code)
        if res.status_code in (301, 302) or "logout" in res.text:
            _dump(res.text, f"logout_{step}")
            logging.warning("세션 만료 → 로그인 시도(%d/2)", step)
            _login(); continue      # 로그인 후 루프 재시작
        m = CAL_RE.search(res.text)
        if m:
            logging.info("✅ cal_list 추출 성공")
            return json.loads(m.group(1).replace("'", '"'))
        _dump(res.text, f"no_cal_list_{step}")
        logging.error("cal_list 미발견(%d/2)", step)
        _login()
    raise RuntimeError("cal_list 추출 실패")

def check_attendance() -> bool:
    today = date.today().strftime("%Y-%m-%d")
    return today in fetch_cal_list()

# ── CLI 테스트 ───────────────────────────────────────
if __name__ == "__main__":
    try:
        print("✅" if check_attendance() else "❌", flush=True)
    except Exception as e:
        print("🚨", e, flush=True)
