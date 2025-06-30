r"""
Hackers Champ 출석 여부 자동 확인 스크립트
------------------------------------------------
• _login()          : 세션이 비로그인 상태일 때 로그인 수행
• fetch_cal_list()  : cal_list JSON → dict 반환 (자동 재로그인 & 재시도 3회)
• check_attendance(): 오늘 날짜 출석 여부 True/False 반환

Python 3.9+ (zoneinfo)
의존성: requests, beautifulsoup4
       $ pip install requests beautifulsoup4
"""

from __future__ import annotations

import json
import logging
import re
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Optional

import requests
from bs4 import BeautifulSoup

__all__ = [
    "_login",
    "fetch_cal_list",
    "check_attendance",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  Global HTTP session & constants
# ---------------------------------------------------------------------------
SESS = requests.Session()

_COMMON_HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.6,en;q=0.5",
    "Cache-Control": "max-age=0",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0.0.0 Safari/537.36"
    ),
}
SESS.headers.update(_COMMON_HEADERS)

_LOGIN_PAGE = (
    "https://member.hackers.com/login"
    "?service_id=3090&return_url="
    "https%3A%2F%2Fchamp.hackers.com%2F"
    "%3Fr%3Dchampstudy%26c%3Dmypage"
    "%2Fmy_lec%2Fmy_lec_refund%26sub%3Drefund_class_view"
    "%26odri_id%3D1493945512"
)
_LOGIN_POST = "https://member.hackers.com/login"
_TARGET_URL = (
    "https://champ.hackers.com/"
    "?r=champstudy&c=mypage/my_lec/my_lec_refund"
    "&sub=refund_class_view&odri_id=1493945512"
)

# 로그인 정보 (실 서비스에서는 안전한 저장/주입 필요)
_LOGIN_ID, _PASSWORD = os.getenv("HACKERS_ID"), os.getenv("HACKERS_PW")
if not (_LOGIN_ID and _PASSWORD):
    raise RuntimeError("HACKERS_ID / HACKERS_PW 환경변수를 설정하세요")

# ---------------------------------------------------------------------------
#  Private helpers
# ---------------------------------------------------------------------------

def _extract_csrf_token(html: str) -> str:
    """페이지 HTML에서 hidden _token 값을 추출한다."""
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("input", attrs={"name": "_token"})
    if not tag or not tag.get("value"):
        raise RuntimeError("CSRF token을 찾을 수 없습니다.")
    return tag["value"]


def _parse_cal_list(html: str) -> Optional[Dict[str, str]]:
    """var cal_list = {...}; 를 dict 로 변환 (없으면 None)."""
    m = re.search(r"var\s+cal_list\s*=\s*(\{[\s\S]*?\});", html)
    if not m:
        return None
    js_obj = m.group(1)
    # JS 객체 → JSON 호환(따옴표는 이미 \"…\")
    try:
        return json.loads(js_obj)
    except json.JSONDecodeError as e:
        logger.error("cal_list JSON 변환 실패: %s", e)
        raise


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def _login() -> None:
    """세션이 비로그인 상태라면 로그인 과정을 수행한다."""
    try:
        logger.info("로그인 페이지 접근(_token 추출)")
        r0 = SESS.get(_LOGIN_PAGE, timeout=10)
        r0.raise_for_status()
        csrf_token = _extract_csrf_token(r0.text)

        payload = {
            "_token": csrf_token,
            "login_id": _LOGIN_ID,
            "password": _PASSWORD,
            "keep_login": "on",
        }

        logger.info("로그인 POST 시도")
        r1 = SESS.post(
            _LOGIN_POST,
            data=payload,
            allow_redirects=False,
            headers={
                **_COMMON_HEADERS,
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://member.hackers.com",
                "Referer": _LOGIN_PAGE,
            },
            timeout=10,
        )
        if r1.status_code != 302:
            raise RuntimeError(f"로그인 실패(status {r1.status_code})")

        redirect_url = r1.headers["Location"]
        logger.info("리다이렉트 GET → %s", redirect_url)
        # 첫 GET (refresh 메타 대응)
        SESS.get(
            redirect_url,
            allow_redirects=False,
            headers={**_COMMON_HEADERS, "Referer": "https://member.hackers.com/"},
            timeout=10,
        )
        logger.info("세션 로그인 완료")
    except requests.RequestException as e:
        logger.exception("네트워크 오류: %s", e)
        raise


def fetch_cal_list(max_retry: int = 3) -> Dict[str, str]:
    """목표 페이지에서 cal_list dict 를 반환.

    1. 페이지 GET → cal_list 추출
    2. 실패 시 _login() 후 재시도(최대 max_retry)
    """
    attempt = 0
    while attempt < max_retry:
        attempt += 1
        try:
            logger.info("TARGET GET (attempt %d) …", attempt)
            r = SESS.get(
                _TARGET_URL,
                headers={**_COMMON_HEADERS, "Referer": _TARGET_URL},
                timeout=10,
            )
            r.raise_for_status()
            cal_dict = _parse_cal_list(r.text)
            if cal_dict is not None:
                logger.info("cal_list 파싱 성공 (%d 항목)", len(cal_dict))
                return cal_dict
            logger.warning("cal_list 미발견 – 재로그인 시도")
        except requests.RequestException as e:
            logger.error("네트워크 오류: %s", e)
        except Exception as e:
            logger.error("오류 발생: %s", e)

        # 재로그인 후 재시도
        try:
            _login()
        except Exception as e:
            logger.error("로그인 재시도 실패: %s", e)
            break  # 로그인 자체가 안 되면 추가 시도 무의미

    raise RuntimeError("cal_list를 찾을 수 없습니다 (재시도 초과)")


def check_attendance() -> bool:
    """오늘 날짜 출석 여부(True/False) 반환."""
    today = datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()  # YYYY-MM-DD
    logger.info("오늘 날짜: %s", today)
    cal_dict = fetch_cal_list()
    result = cal_dict.get(today) == "Y"
    logger.info("출석 결과: %s", result)
    return result


# ---------------------------------------------------------------------------
#  CLI 실행 예시
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        present = check_attendance()
        logger.info("✅ 출석 여부: %s", "YES" if present else "NO")
    except Exception as err:
        logger.error("프로그램 실패: %s", err)
        sys.exit(1)