# attendance_bot.py  –  Discord slash-command 버전
import os, asyncio, traceback
import discord
from discord.ext import tasks
from check_attendance import check_attendance     # 동기 함수
from datetime import datetime

# ── 환경 변수 ─────────────────────────────────────────────
TOKEN      = os.getenv("DISCORD_TOKEN")           # 필수
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))         # 알림 받을 채널 ID

# ── Intents : Slash 명령은 guilds 권한만으로 충분 ────────
intents = discord.Intents.default()               # message_content 불필요
bot = discord.Bot(intents=intents)                # prefix 없이도 OK (discord.py ≥2.3)

# ─────────────────────────────────────────────────────────
# 1. Slash Command: /확인
# ─────────────────────────────────────────────────────────
@bot.tree.command(name="확인", description="오늘 출석 여부를 즉시 확인합니다")
async def slash_check(interaction: discord.Interaction):
    """/확인 입력 시 즉시 출석 여부 반환"""
    await interaction.response.defer(ephemeral=True)   # 응답 지연 선언
    loop = asyncio.get_event_loop()
    try:
        ok = await loop.run_in_executor(None, check_attendance)
        msg = "✅ 이미 출석했습니다!" if ok else "❌ 아직 미출석입니다!"
    except Exception as e:
        msg = f"🚨 오류 발생: {e}"
    await interaction.followup.send(msg)

# ─────────────────────────────────────────────────────────
# 2. 1시간 주기 자동 출석 체크
# ─────────────────────────────────────────────────────────
@tasks.loop(hours=1)
async def attendance_loop():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    channel = bot.get_channel(CHANNEL_ID)
    try:
        ok = await asyncio.get_running_loop().run_in_executor(None, check_attendance)
        if not ok:
            await channel.send(f"❌ [{now}] 아직 미출석입니다! 빨리 출석하세요.")
    except Exception:
        err = traceback.format_exc(limit=1)
        await channel.send(f"🚨 [{now}] 출석 체크 오류!\n```{err}```")

# ─────────────────────────────────────────────────────────
# 3. on_ready: Slash 동기화 + 태스크 시작
# ─────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    await bot.tree.sync()                      # 슬래시 명령 전역 등록 :contentReference[oaicite:3]{index=3}
    print(f"✅ Bot ready: {bot.user} (ID {bot.user.id})")
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(f"🤖 Toeic Bot이 실행되었습니다 ({bot.user.id})")
    if not attendance_loop.is_running():
        attendance_loop.start()

# ─────────────────────────────────────────────────────────
bot.run(TOKEN)
