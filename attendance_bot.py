# attendance_bot.py
import os, asyncio, traceback, discord
from discord.ext import tasks, commands
from datetime import datetime, timezone
from check_attendance import check_attendance   # ← 동기 함수

TOKEN      = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# ① Intents ─ Slash 명령만 쓰면 기본값이면 충분합니다
intents = discord.Intents.default()

intents.message_content = True  # 필수: prefix 명령어 처리 위해 필요
bot = commands.Bot(command_prefix="!", intents=intents)

# ③ Slash(/확인) 명령 등록
#@bot.tree.command(name="확인", description="오늘 출석 여부를 즉시 확인합니다")
@bot.command(name="확인")
async def cmd_check(ctx):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        ok = await asyncio.get_running_loop().run_in_executor(None, check_attendance)
        msg = "✅ 이미 출석했습니다!" if ok else "❌ 아직 미출석입니다!"
    except Exception as e:
        msg = f"🚨 오류 발생: {e}"
    await ctx.send(f"[{now}] {msg}")

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

# ─────────────────────────────────────────────────────────
# !남은시간  → 다음 자동 알림까지 남은 시간 표시
# ─────────────────────────────────────────────────────────
@bot.command(name="남은시간")
async def cmd_remaining(ctx):
    if attendance_loop.next_iteration is None:          # 루프가 아직 안 돌았다면
        await ctx.send("⏳ 아직 루프가 초기화되지 않았어요.")
        return
    now  = datetime.now(timezone.utc)
    next = attendance_loop.next_iteration               # UTC datetime 객체 :contentReference[oaicite:3]{index=3}
    remaining = next - now
    minutes, seconds = divmod(int(remaining.total_seconds()), 60)
    await ctx.send(f"⏰ 다음 자동 알림까지 {minutes}분 {seconds}초 남았습니다.")

# ⑤ 봇 준비 → Slash 동기화 & 태스크 시작
@bot.event
async def on_ready():
    #await bot.tree.sync()          # 길드 범위 지정 안 하면 전역 등록
    print(f"✅ Bot ready: {bot.user} ({bot.user.id})")
    ch = bot.get_channel(CHANNEL_ID)
    if ch:
        await ch.send(f"🤖 Toeic Bot 실행 완료 ({bot.user.id})")
    if not attendance_loop.is_running():
        attendance_loop.start()

bot.run(TOKEN)
