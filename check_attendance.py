# check_attendance.py — Referer 헤더 자동 갱신 + 안정적 로그인 & cal_list 추출
import os, re, json, pickle, requests, logging, time
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
DBG = Path("/tmp/toeic_debug"); DBG.mkdir(exist_ok=True)

def _dump(text: str, tag: str, ext="html"):
    p = DBG / f"{tag}_{int(time.time())}.{ext}"
    p.write_text(text, encoding="utf-8")
    logging.info("💾  %s (%dB)", p, p.stat().st_size)

# ────────────────────── URL 및 설정 ──────────────────────
BASE        = "https://member.hackers.com"
CHAMP_HOME  = "https://champ.hackers.com/"
ATTEND_URL  = (CHAMP_HOME +
               "?r=champstudy&c=mypage/my_lec/my_lec_refund"
               "&sub=refund_class_view&odri_id=1493945512")
LOGIN_PAGE  = f"{BASE}/login?service_id=3090&return_url={ATTEND_URL}"
LOGIN_POST  = f"{BASE}/login"

COOKIE_FILE = Path.home() / ".cache/toeic_bot_cookies.pkl"

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
    raise RuntimeError("❗ HACKERS_ID / HACKERS_PW 환경변수 필요")

# ────────────────────── 세션 생성 & 쿠키 로드 ──────────────────────
sess = requests.Session()
sess.headers.update(HEADERS)

if COOKIE_FILE.exists():
    try:
        sess.cookies.update(pickle.loads(COOKIE_FILE.read_bytes()))
        logging.info("✅ 쿠키 불러옴: %s", COOKIE_FILE)
    except Exception:
        COOKIE_FILE.unlink(True)
        logging.warning("⚠️ 쿠키 파싱 실패 — 삭제됨")

# ────────────────────── 로그인 흐름 ──────────────────────
def _login():
    # 로그인 페이지 GET (Referer 자동 설정)
    sess.headers["Referer"] = LOGIN_PAGE
    html = sess.get(LOGIN_PAGE, timeout=10).text
    mtk = re.search(r'name="_token"\s+value="([^"]+)"', html)
    payload = {
        "_token": token.group(1) if (token := mtk) else "",
        "login_id": ID,
        "password":  PW,
        "keep_login": "on",
    }

    # 로그인 POST + 302 자동 추적
    sess.headers["Referer"] = LOGIN_PAGE
    resp = sess.post(LOGIN_POST, data=payload, timeout=20, allow_redirects=True)
    if resp.status_code not in (200, 302):
        _dump(resp.text, "login_fail"); raise RuntimeError("로그인 실패")

    # 챔프 도메인 쿠키 받아오기
    sess.headers["Referer"] = resp.url
    sess.get(CHAMP_HOME, timeout=10)

    # 로그인 성공 여부 마지막 확인
    sess.headers["Referer"] = CHAMP_HOME
    verify = sess.get(ATTEND_URL, timeout=10, allow_redirects=False)
    if verify.status_code in (301, 302) or "logout" in verify.text:
        _dump(verify.text, "login_still_logout")
        raise RuntimeError("세션 유지 실패 — logout 감지됨")

    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_FILE.write_bytes(pickle.dumps(sess.cookies))
    logging.info("🔑 새 쿠키 저장됨: %s", COOKIE_FILE)

# ────────────────────── cal_list 추출 ──────────────────────
CAL_RE = re.compile(r"cal_list\s*=\s*({.*?})[;\n]", re.S)

def _get_page():
    sess.headers["Referer"] = CHAMP_HOME
    return sess.get(ATTEND_URL, timeout=10, allow_redirects=False)

def fetch_cal_list() -> dict:
    for i in (1, 2):
        res = _get_page()
        logging.info("GET 출석페이지 → %s", res.status_code)

        if res.status_code in (301, 302) or "logout" in res.text:
            _dump(res.text, f"logout_{i}")
            logging.warning("세션 만료 감지 — 재로그인 (%d/2)", i)
            _login(); continue

        m = CAL_RE.search(res.text)
        if m:
            logging.info("✅ cal_list 추출 성공")
            return json.loads(m.group(1).replace("'", '"'))

        _dump(res.text, f"no_cal_list_{i}")
        logging.error("cal_list을 찾지 못함 (%d/2)", i)
        _login()
    raise RuntimeError("❌ cal_list 추출 실패")

# ────────────────────── 출석 여부 확인 ──────────────────────
def check_attendance() -> bool:
    today = date.today().strftime("%Y-%m-%d")
    return today in fetch_cal_list()

# ────────────────────── 디버깅용 메인 ──────────────────────
if __name__ == "__main__":
    try:
        print("✅ 출석 완료" if check_attendance() else "❌ 오늘 미출석", flush=True)
    except Exception as e:
        print("🚨 오류:", e, flush=True)
