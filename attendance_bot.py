# attendance_bot.py
import os, asyncio, traceback, discord
from discord.ext import tasks, commands
from datetime import datetime
from check_attendance import check_attendance   # ← 동기 함수

TOKEN      = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# ① Intents ─ Slash 명령만 쓰면 기본값이면 충분합니다
intents = discord.Intents.default()

# ② Bot 인스턴스 (prefix는 의미 없지만 필수 파라미터라 빈 문자열 사용)
bot = commands.Bot(command_prefix="", intents=intents)

# ③ Slash(/확인) 명령 등록
@bot.tree.command(name="확인", description="오늘 출석 여부를 즉시 확인합니다")
async def slash_check(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)          # 3초 제한 회피
    loop = asyncio.get_running_loop()
    try:
        ok = await loop.run_in_executor(None, check_attendance)
        msg = "✅ 이미 출석했습니다!" if ok else "❌ 아직 미출석입니다!"
    except Exception as e:
        msg = f"🚨 오류 발생: {e}"
    await interaction.followup.send(msg)

# ④ 1시간 주기 자동 체크 태스크
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

# ⑤ 봇 준비 → Slash 동기화 & 태스크 시작
@bot.event
async def on_ready():
    await bot.tree.sync()          # 길드 범위 지정 안 하면 전역 등록
    print(f"✅ Bot ready: {bot.user} ({bot.user.id})")
    ch = bot.get_channel(CHANNEL_ID)
    if ch:
        await ch.send(f"🤖 Toeic Bot 실행 완료 ({bot.user.id})")
    if not attendance_loop.is_running():
        attendance_loop.start()

bot.run(TOKEN)
