# -*- coding: utf-8 -*-
"""
Hackers Champ 출석체크 – 자동 로그인‧쿠키 영구화
함수:
    fetch_cal_list()  ▶ dict   : "YYYY-MM-DD": "Y"
    check_attendance() ▶ bool  : 오늘 출석 여부
"""

import os, re, json, pickle, requests
from datetime import date
from pathlib import Path

# ── URL ──────────────────────────────────────────────
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

# ── 세션 & 쿠키 ───────────────────────────────────────
sess = requests.Session()
sess.headers.update(HEADERS)
if COOKIE_FILE.exists():
    try:
        sess.cookies.update(pickle.loads(COOKIE_FILE.read_bytes()))
    except Exception:
        COOKIE_FILE.unlink(missing_ok=True)   # 손상 시 삭제

# ── 로그인 ───────────────────────────────────────────
def _login() -> None:
    """POST 로그인 후 쿠키를 파일로 저장."""
    html = sess.get(LOGIN_PAGE, timeout=10).text
    token = re.search(r'name="_token"\s+value="([^"]+)"', html)
    payload = {
        "_token": token.group(1) if token else "",
        "login_id": ID,
        "password": PW,
        "keep_login": "on",
    }
    r = sess.post(LOGIN_POST, data=payload, allow_redirects=False, timeout=10)
    if r.status_code not in (302, 200):
        raise RuntimeError(f"로그인 실패({r.status_code})")
    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_FILE.write_bytes(pickle.dumps(sess.cookies))
    print("🔑  새 쿠키 저장 완료")

# ── cal_list 추출 ────────────────────────────────────
def fetch_cal_list() -> dict:
    """
    로그인 세션에서 cal_list 전체를 dict 로 반환.
    세션 만료시 자동 재로그인 뒤 재시도.
    """
    for _ in range(2):                       # 최초 + 재로그인 1회 시도
        res = sess.get(ATTEND_URL, allow_redirects=False, timeout=10)
        if res.status_code in (301, 302):
            _login()
            continue
        m = re.search(r"cal_list\s*=\s*(\{[^}]+\})", res.text, re.S)
        if not m:
            _login()
            continue
        return json.loads(m.group(1).replace("'", '"'))
    raise RuntimeError("cal_list 추출 실패")

# ── 오늘 출석 판단 ───────────────────────────────────
def check_attendance() -> bool:
    today = date.today().strftime("%Y-%m-%d")
    return today in fetch_cal_list()

# ── CLI 테스트 ───────────────────────────────────────
if __name__ == "__main__":
    ok = check_attendance()
    print("✅ 출석 완료" if ok else "❌ 아직 미출석")
