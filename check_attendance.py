# check_attendance.py  –  cal_list 없으면 attend_list.ajax로 폴백
import os, re, json, pickle, requests, logging, time
from datetime import date
from pathlib import Path

# ── 로깅 설정 ─────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
DEBUG_DIR = Path("/tmp/toeic_debug"); DEBUG_DIR.mkdir(exist_ok=True)

def _dump(content: str, tag: str, ext="html"):
    p = DEBUG_DIR / f"{tag}_{int(time.time())}.{ext}"
    p.write_text(content, encoding="utf-8")
    logging.info("💾  %s (%dB)", p, p.stat().st_size)

# ── URL 상수 ──────────────────────────────────────────
BASE_URL   = "https://member.hackers.com"
LOGIN_PAGE = (f"{BASE_URL}/login?service_id=3090"
              "&return_url=https%3A%2F%2Fchamp.hackers.com%2F")
LOGIN_POST = f"{BASE_URL}/login"
CHAMP_HOME = "https://champ.hackers.com/"
ATTEND_URL = (CHAMP_HOME +
              "?r=champstudy&c=mypage/my_lec/my_lec_refund"
              "&sub=refund_class_view&odri_id=1493945512")
ATTEND_API = (CHAMP_HOME +
              "?r=champstudy&m=mypage&a=attend_list.ajax")

COOKIE_FILE = Path.home() / ".cache/toeic_bot_cookies.pkl"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/137.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,"
               "application/xml;q=0.9,*/*;q=0.8"),
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": BASE_URL,
    "Referer": LOGIN_PAGE,
}

ID = os.getenv("HACKERS_ID")
PW = os.getenv("HACKERS_PW")
if not (ID and PW):
    raise RuntimeError("HACKERS_ID / HACKERS_PW 환경변수를 설정하세요")

# ── 세션 & 쿠키 ───────────────────────────────────────
sess = requests.Session(); sess.headers.update(HEADERS)
if COOKIE_FILE.exists():
    try:
        sess.cookies.update(pickle.loads(COOKIE_FILE.read_bytes()))
        logging.info("✅ 쿠키 로드: %s", COOKIE_FILE)
    except Exception:
        logging.warning("⚠️  쿠키 손상 → 삭제"); COOKIE_FILE.unlink(True)

# ── 로그인 ───────────────────────────────────────────
def _login():
    html = sess.get(LOGIN_PAGE, timeout=10).text
    token = re.search(r'name="_token"\s+value="([^"]+)"', html)
    payload = {"_token": token.group(1) if token else "",
               "login_id": ID, "password": PW, "keep_login": "on"}
    resp = sess.post(LOGIN_POST, data=payload,
                     allow_redirects=False, timeout=10)
    if resp.status_code not in (200, 302):
        _dump(resp.text, "login_fail"); raise RuntimeError("로그인 실패")
    # 302 Location 따라가기
    if resp.status_code == 302:
        loc = resp.headers["Location"]
        sess.get(loc if loc.startswith("http") else BASE_URL + loc, timeout=10)
    # champ.hackers.com 홈 열어 서브도메인용 쿠키 확보
    sess.get(CHAMP_HOME, timeout=10)
    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_FILE.write_bytes(pickle.dumps(sess.cookies))
    logging.info("🔑  새 쿠키 저장(%s)", COOKIE_FILE)

# ── cal_list & API 폴백 ──────────────────────────────
CAL_RE = re.compile(r"cal_list\s*=\s*({.*?})[;\n]", re.S)

def _html_cal_list() -> dict|None:
    res = sess.get(ATTEND_URL, allow_redirects=False, timeout=10)
    logging.info("GET refund_class_view → %s", res.status_code)
    if res.status_code in (301, 302):
        _dump(res.text, "redirect")
        raise RuntimeError("SESSION_EXPIRED")
    m = CAL_RE.search(res.text)
    if m:
        return json.loads(m.group(1).replace("'", '"'))
    _dump(res.text, "no_cal_list")
    return None

def _api_cal_list() -> dict:
    today = date.today().strftime("%Y-%m-%d")
    payload = {"now_date": today}
    res = sess.post(ATTEND_API, data=payload, timeout=10)
    logging.info("POST attend_list.ajax → %s", res.status_code)
    if res.status_code != 200:
        _dump(res.text, "api_fail", "txt")
        raise RuntimeError("API 호출 실패")
    data = res.json()
    return {d: "Y" for d in data.get("check_date_list", {})}

def fetch_cal_list() -> dict:
    """cal_list 추출(HTML→실패시 API) + 세션 만료 자동 복구"""
    for step in (1, 2):
        try:
            cal = _html_cal_list()
            if cal is not None:
                return cal
            # HTML에 없으면 AJAX API 사용
            return _api_cal_list()
        except RuntimeError as e:
            if "SESSION_EXPIRED" in str(e) and step == 1:
                logging.warning("세션 만료 → 재로그인")
                _login()
            else:
                raise
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
