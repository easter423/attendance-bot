# attendance_bot.py
import os, asyncio, traceback, discord
from discord.ext import tasks, commands
from discord.ext.commands import Paginator
from datetime import datetime, timezone
from check_attendance import check_attendance, fetch_cal_list

TOKEN      = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True            # prefix 명령 필수
bot = commands.Bot(command_prefix="!", intents=intents)

# ── 1시간마다 자동 체크 ─────────────────────────────
@tasks.loop(hours=1)
async def attendance_loop():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    ch  = bot.get_channel(CHANNEL_ID)
    try:
        ok = await asyncio.get_running_loop().run_in_executor(None, check_attendance)
        if not ok:
            await ch.send(f"❌ [{now}] 아직 미출석입니다! 빨리 출석하세요.")
    except Exception:
        err = traceback.format_exc(limit=1)
        await ch.send(f"🚨 출석 체크 오류!\n```{err}```")

# ── !확인 ───────────────────────────────────────────
@bot.command(name="확인")
async def cmd_check(ctx):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        ok = await asyncio.get_running_loop().run_in_executor(None, check_attendance)
        msg = "✅ 이미 출석했습니다!" if ok else "❌ 아직 미출석입니다!"
    except Exception as e:
        msg = f"🚨 오류: {e}"
    await ctx.send(f"[{now}] {msg}")

# ── !전체확인 ───────────────────────────────────────
@bot.command(name="전체확인")
async def cmd_full(ctx):
    await ctx.defer()
    try:
        cal = await asyncio.get_running_loop().run_in_executor(None, fetch_cal_list)
        lines = [f"{d}: {v}" for d, v in sorted(cal.items())]
        pag = Paginator(prefix="```", suffix="```")
        for ln in lines:
            pag.add_line(ln)
        for page in pag.pages:
            await ctx.send(page)
    except Exception as e:
        await ctx.send(f"🚨 오류: {e}")

# ── !남은시간 ──────────────────────────────────────
@bot.command(name="남은시간")
async def cmd_remaining(ctx):
    if attendance_loop.next_iteration is None:
        await ctx.send("⏳ 아직 루프가 초기화되지 않았어요.")
        return
    now   = datetime.now(timezone.utc)
    nxt   = attendance_loop.next_iteration
    delta = nxt - now
    m, s  = divmod(int(delta.total_seconds()), 60)
    await ctx.send(f"⏰ 다음 자동 알림까지 {m}분 {s}초 남았습니다.")

# ── on_ready ───────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Bot ready: {bot.user} ({bot.user.id})")
    ch = bot.get_channel(CHANNEL_ID)
    if ch:
        await ch.send("🤖 봇이 실행되었습니다!")
    if not attendance_loop.is_running():
        attendance_loop.start()

bot.run(TOKEN)  # systemd에서는 python -u 로 실행해 실시간 로그 확보
