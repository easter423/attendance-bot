# -*- coding: utf-8 -*-
"""
Hackers Champ 출석체크 – 자동 로그인·쿠키 영구화 버전
© 2025.06
"""
import os, re, json, pickle, requests
from datetime import date
from pathlib import Path

# ── 고정 URL ───────────────────────────────────────────
BASE_URL = "https://member.hackers.com"
LOGIN_PAGE = (f"{BASE_URL}/login?service_id=3090"
              "&return_url=https%3A%2F%2Fchamp.hackers.com%2F")
LOGIN_POST = f"{BASE_URL}/login"                     # ← curl 에서 POST 하던 주소
ATTEND_URL = ("https://champ.hackers.com/"
              "?r=champstudy&c=mypage/my_lec/my_lec_refund"
              "&sub=refund_class_view&odri_id=1493945512")

COOKIE_FILE = Path.home() / ".cache/toeic_bot_cookies.pkl"

# ── 공통 헤더 (필요한 핵심만 유지) ───────────────────────
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/137.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": BASE_URL,
    "Referer": LOGIN_PAGE,
}

# ── 자격증명 (환경 변수) ────────────────────────────────
ID = os.getenv("HACKERS_ID")
PW = os.getenv("HACKERS_PW")
if not (ID and PW):
    raise RuntimeError("환경변수 HACKERS_ID / HACKERS_PW 를 설정하세요.")

# ── 세션 & 쿠키 로딩 ────────────────────────────────────
sess = requests.Session()
sess.headers.update(HEADERS)
if COOKIE_FILE.exists():
    try:
        sess.cookies.update(pickle.loads(COOKIE_FILE.read_bytes()))
    except Exception:
        COOKIE_FILE.unlink(missing_ok=True)          # 손상 시 삭제

# ── 로그인 루틴 ─────────────────────────────────────────
def login() -> None:
    """로그인 페이지 → CSRF 토큰 수집 → POST → 새 쿠키 저장"""
    r = sess.get(LOGIN_PAGE, timeout=10)
    r.raise_for_status()                                                # :contentReference[oaicite:1]{index=1}
    m = re.search(r'name="_token"\s+value="([^"]+)"', r.text)           # :contentReference[oaicite:2]{index=2}
    token = m.group(1) if m else ""
    payload = {
        "_token": token,
        "login_id": ID,
        "password": PW,
        "keep_login": "on",
    }
    resp = sess.post(LOGIN_POST, data=payload, allow_redirects=False, timeout=10)
    if resp.status_code not in (302, 200):
        raise RuntimeError(f"로그인 실패: {resp.status_code}")
    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_FILE.write_bytes(pickle.dumps(sess.cookies))                 # :contentReference[oaicite:3]{index=3}
    print("🔑 새 쿠키 저장 완료")

# ── cal_list 추출 ───────────────────────────────────────
def fetch_cal_dict() -> dict:
    """JS cal_list 객체 → dict; 세션 만료 시 RuntimeError"""
    r = sess.get(ATTEND_URL, allow_redirects=False, timeout=10)
    if r.status_code in (301, 302):
        raise RuntimeError("SESSION_EXPIRED")                           # :contentReference[oaicite:4]{index=4}
    m = re.search(r"cal_list\s*=\s*(\{[^}]+\})", r.text, re.S)          # :contentReference[oaicite:5]{index=5}
    if not m:
        raise RuntimeError("SESSION_EXPIRED")
    return json.loads(m.group(1).replace("'", '"'))                     # :contentReference[oaicite:6]{index=6}

# ── 메인 진입점 ─────────────────────────────────────────
def check_attendance():
    """출석 여부(bool)와 cal_list(dict) 반환"""
    try:
        cal = fetch_cal_dict()
    except RuntimeError as e:
        if "SESSION_EXPIRED" in str(e):
            login()
            cal = fetch_cal_dict()
        else:
            raise
    today = date.today().strftime("%Y-%m-%d")
    return today in cal, cal

# ── CLI 테스트 ──────────────────────────────────────────
if __name__ == "__main__":
    try:
        ok, cal = check_attendance()
        print("✅ 출석 완료" if ok else "❌ 미출석하였습니다.")
    except Exception as err:
        print("🚨 오류:", err)
