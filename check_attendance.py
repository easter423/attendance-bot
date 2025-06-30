# check_attendance.py  ─ Hackers Champ 자동 로그인 + 출석 확인
import os, re, json, pickle, requests, logging, time
from datetime import date
from pathlib import Path

# ────────────────────── 기본 설정 ──────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
DBG = Path("/tmp/toeic_debug"); DBG.mkdir(exist_ok=True)

def _dump(text: str, tag: str, ext="html"):
    p = DBG / f"{tag}_{int(time.time())}.{ext}"
    p.write_text(text, encoding="utf-8")
    logging.info("💾  %s (%dB)", p, p.stat().st_size)

# (1) URL
BASE       = "https://member.hackers.com"
CHAMP_HOME = "https://champ.hackers.com/"
ATTEND_URL = (CHAMP_HOME +
              "?r=champstudy&c=mypage/my_lec/my_lec_refund"
              "&sub=refund_class_view&odri_id=1493945512")
LOGIN_PAGE = f"{BASE}/login?service_id=3090&return_url={ATTEND_URL}"
LOGIN_POST = f"{BASE}/login"

# (2) 고정 파일
COOKIE_FILE = Path.home() / ".cache/toeic_bot_cookies.pkl"

# (3) 헤더
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/137.0.0.0 Safari/537.36",
    "Accept": ("text/html,application/xhtml+xml,"
               "application/xml;q=0.9,*/*;q=0.8"),
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": BASE,
    "Referer": LOGIN_PAGE,
}

# (4) 자격증명
ID, PW = os.getenv("HACKERS_ID"), os.getenv("HACKERS_PW")
if not (ID and PW):
    raise RuntimeError("❗ HACKERS_ID / HACKERS_PW 환경변수를 먼저 설정하세요")

# ────────────────────── 세션 구성 ──────────────────────
sess = requests.Session(); sess.headers.update(HEADERS)

if COOKIE_FILE.exists():
    try:
        sess.cookies.update(pickle.loads(COOKIE_FILE.read_bytes()))
        logging.info("✅ 쿠키 로드: %s", COOKIE_FILE)
    except Exception:
        COOKIE_FILE.unlink(True); logging.warning("⚠️ 쿠키 손상 → 삭제")

# ────────────────────── 로그인 루틴 ────────────────────
def _login() -> None:
    """member.hackers.com → POST 로그인 → 302 따라가 champ.hackers.com 세션 쿠키 확보"""
    html = sess.get(LOGIN_PAGE, timeout=10).text
    mtk  = re.search(r'name="_token"\s+value="([^"]+)"', html)
    payload = {
        "_token":      mtk.group(1) if mtk else "",
        "login_id":    ID,
        "password":    PW,
        "keep_login":  "on",
        "service_id":  "3090",
        "return_url":  ATTEND_URL,
    }
    resp = sess.post(LOGIN_POST, data=payload,
                     timeout=20, allow_redirects=True)  # 302 자동 추적
    if resp.status_code not in (200, 302):
        _dump(resp.text, "login_fail"); raise RuntimeError("로그인 실패")

    # champ.hackers.com 홈 방문(쿠키 확정)
    sess.get(CHAMP_HOME, timeout=10)

    # 최종 확인: 여전히 logout 스크립트면 실패 처리
    verify = sess.get(ATTEND_URL, timeout=10, allow_redirects=False)
    if "logout" in verify.text or verify.status_code in (301, 302):
        _dump(verify.text, "login_still_logout")
        raise RuntimeError("로그인 세션 미확보")

    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_FILE.write_bytes(pickle.dumps(sess.cookies))
    logging.info("🔑 새 쿠키 저장: %s", COOKIE_FILE)

# ────────────────────── cal_list 추출 ──────────────────
CAL_RE = re.compile(r"cal_list\s*=\s*({.*?})[;\n]", re.S)

def _get_page():
    return sess.get(ATTEND_URL, timeout=10, allow_redirects=False)

def fetch_cal_list() -> dict:
    """HTML 안 cal_list = {...} JS 객체를 dict 로 반환."""
    for attempt in (1, 2):
        res = _get_page()
        logging.info("GET refund_page → %s", res.status_code)

        if res.status_code in (301, 302) or "logout" in res.text:
            _dump(res.text, f"logout_{attempt}")
            logging.warning("세션 만료 → 재로그인(%d/2)", attempt)
            _login(); continue

        m = CAL_RE.search(res.text)
        if m:
            logging.info("✅ cal_list 추출 성공")
            return json.loads(m.group(1).replace("'", '"'))

        _dump(res.text, f"no_cal_list_{attempt}")
        logging.error("cal_list 미발견(%d/2)", attempt)
        _login()
    raise RuntimeError("cal_list 추출 실패")

# ────────────────────── 오늘 출석 여부 ─────────────────
def check_attendance() -> bool:
    today = date.today().strftime("%Y-%m-%d")
    return today in fetch_cal_list()

# ────────────────────── CLI 테스트용 ───────────────────
if __name__ == "__main__":
    try:
        print("✅ 출석 완료" if check_attendance() else "❌ 아직 미출석", flush=True)
    except Exception as e:
        print("🚨 오류:", e, flush=True)
