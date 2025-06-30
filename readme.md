# D90 Sentinel

**Version v0.1.0**\
[GitHub Repository](https://github.com/easter423/d90-sentinel)

---

## 개요

"D90 Sentinel"은 **90일(Day 90)을 지키는 파수꾼(sentinel)** 으로서, 해O스인강 환급반 수강생이 **오늘 출석(출석체크) 여부를 자동으로 확인**하고, 미출석 시 **1시간 간격으로 디스코드 알림을 전송**하여 놓치지 않도록 돕는 디스코드 봇입니다. 개인 PC‑환경은 물론, 클라우드 서버(Linux)에서 **상시 서비스**로 구동할 수 있습니다.

### 주요 기능

| 명령           | 별칭                             | 설명                            |
| ------------ | ------------------------------ | ----------------------------- |
| `/check`     | `!check`, `/확인`, `!확인`         | 금일 출석 여부를 즉시 확인합니다.           |
| `/all`       | `!all`, `/전체확인`, `!전체확인`       | 전체 출결 현황을 보여줍니다. |
| `/remaining` | `!remaining`, `/남은시간`, `!남은시간` | 다음 자동 알림까지 남은 시간을 표시합니다.      |

> 모든 슬래시 명령은 `!` 접두사를 사용한 접두사(prefix) 명령으로도 호출할 수 있습니다.

---

## 아키텍처

```
attendance-bot/
├── attendance_bot.py   # Discord 봇 시작점(entry point) · 명령어/루프 처리
├── check_attendance.py # 세션 유지 · REST 호출 · 출석 데이터 파싱
├── requirements.txt    # 의존 패키지 목록
└── README.md
```

- 
  Discord 봇 초기화, 하이브리드(슬래시+프리픽스) 명령 정의, 1시간 주기 `tasks.loop` 로 출석 체크.
- 
  `requests.Session` 기반 로그인 유지, `cal_list` JSON 파싱, `check_attendance()` 로 금일 출석 여부 반환.

---

## 설치 및 실행

### 1) 의존 환경

- Python ≥ 3.9 (`zoneinfo` 모듈 사용)
- Discord API 접근 권한이 있는 봇 토큰

### 2) 소스 코드 가져오기

```bash
$ git clone https://github.com/easter423/d90-sentinel.git
$ cd d90-sentinel
```

### 3) 가상환경 및 라이브러리 설치

```bash
$ python -m venv venv
$ source venv/bin/activate
(venv)$ pip install -r requirements.txt
```

### 4) 환경 변수 설정

| 변수              | 설명                                  |
| --------------- | ----------------------------------- |
| `DISCORD_TOKEN` | Discord Developer Portal에서 발급한 봇 토큰 |
| `CHANNEL_ID`    | 알림을 보낼 Discord 채널 ID (정수)           |
| `HACKERS_ID`    | 해커스 챔프스터디 로그인 ID                    |
| `HACKERS_PW`    | 해커스 챔프스터디 비밀번호                      |

`.env` 파일에 저장하거나 **systemd 환경변수**로 주입할 수 있습니다.

### 5) 로컬에서 즉시 실행

```bash
(venv)$ python attendance_bot.py
```

봇이 온라인 상태가 되면 지정된 채널에 “봇이 실행되었습니다!” 메시지가 표시됩니다.

---

## Linux 서버(예: GCP Ubuntu 24.04) 상시 구동

### 1) systemd 서비스 파일 예시

`/etc/systemd/system/d90-sentinel.service`

```ini
[Unit]
Description=Discord 출석 봇
After=network.target

[Service]
User=YOUR_LINUX_USERNAME
WorkingDirectory=/home/YOUR_LINUX_USERNAME/d90-sentinel
Environment=DISCORD_TOKEN=...
Environment=CHANNEL_ID=...
Environment=HACKERS_ID=...
Environment=HACKERS_PW=...
ExecStart=/home/YOUR_LINUX_USERNAME/d90-sentinel/venv/bin/python attendance_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

> **중요 :** `~` 같은 상대 경로는 지원되지 않으므로 **절대 경로**를 지정해야 합니다.

### 2) 서비스 등록 & 제어

```bash
# 변경 내용 적용
$ sudo systemctl daemon-reload

# 부팅 시 자동시작
$ sudo systemctl enable d90-sentinel

# 서비스 시작 / 재시작 / 상태 확인
$ sudo systemctl start    d90-sentinel
$ sudo systemctl restart  d90-sentinel
$ sudo systemctl status   d90-sentinel

# 실시간 로그 확인
$ journalctl -fu d90-sentinel.service
```

### 3) 서버 관리 유용 명령어

| 명령                                         | 용도               |
| ------------------------------------------ | ---------------- |
| `pip install -r requirements.txt`          | 의존 패키지 일괄 설치     |
| `sudo timedatectl set-timezone Asia/Seoul` | 시스템 시간대를 KST로 설정 |
| `source venv/bin/activate`                 | 가상환경 활성화         |
| `git pull`                                 | 원격 저장소로부터 최신 내용 반영     |

---

## Discord 봇 생성 절차 (요약)

1. **Developer Portal** → *New Application* → 이름 입력 → *Create*.
2. 좌측 **Bot** → *Add Bot* → *Reset Token* 으로 토큰 발급·복사.
3. **OAuth2 ▶ URL Generator** 에서 *bot* 범위 선택, 권한은 *Send Messages* 등 최소 권한만 체크 후 생성된 URL로 서버에 초대.
4. **Bot ▶ Privileged Gateway Intents** 에서 **Message Content Intent** 활성화.

---

## 한계 및 향후 과제

- 로그인 ID·비밀번호 등 민감 정보가 환경 변수로만 분리되어 있음 → **비밀 관리 서비스**(AWS Secrets Manager, GCP Secret Manager 등) 연동 예정
- 다중 수강생 지원(여러 계정 각각 모니터링) 기능 미구현

---

## 변경 이력

| Version | 날짜         | 주요 변경 사항                                 |
| ------- | ---------- | ---------------------------------------- |
| v0.1.0  | 2025‑06‑30 | 최초 공개 · Discord 하이브리드 명령, systemd 가이드 포함 |

---

## 라이선스

이 프로젝트는 MIT License 하에 배포됩니다. 자유롭게 사용, 복사, 수정, 병합, 게시, 배포, 서브라이선스 및 판매할 수 있으며, 다음 조건을 따라야 합니다:

소스 코드 내 또는 바이너리 배포 시 원본 라이선스 사본을 포함해야 합니다.

본 소프트웨어는 "있는 그대로" 제공되며, 명시적이든 묵시적이든 어떤 종류의 보증도 제공되지 않습니다. 이에 대한 책임은 사용자에게 있습니다.

자세한 내용은 LICENSE 파일을 참고하십시오.

---

## 기여

Issue나 Pull Request는 언제든 환영합니다. 다만, **개인 정보 보호**와 **비밀키 노출**에 각별히 주의하십시오.

