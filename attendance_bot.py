# attendance_bot.py  ─ hybrid version
import os, asyncio, traceback, discord
from discord.ext import tasks, commands
from discord.ext.commands import Paginator
from datetime import datetime, timezone
from check_attendance import check_attendance, fetch_cal_list

TOKEN      = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True
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

# ── /check  |  !확인 ────────────────────────────────
@bot.hybrid_command(
    name="check",
    aliases=["확인"],
    description="출석 상태를 확인합니다.",
    name_localizations={"ko": "확인"},
    description_localizations={"ko": "출석 상태를 확인합니다."},
)
async def cmd_check(ctx: commands.Context):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        ok = await asyncio.get_running_loop().run_in_executor(None, check_attendance)
        msg = "✅ 이미 출석했습니다!" if ok else "❌ 아직 미출석입니다!"
    except Exception as e:
        msg = f"🚨 오류: {e}"
    await ctx.send(f"[{now}] {msg}")

# ── /all  |  !전체확인 ──────────────────────────
@bot.hybrid_command(
    name="all",
    aliases=["전체확인"],
    description="전체 출석 현황을 확인합니다.",
    name_localizations={"ko": "전체확인"},
    description_localizations={"ko": "전체 출석 현황을 확인합니다."},
)
async def cmd_full(ctx: commands.Context):
    await ctx.defer()
    try:
        cal = await asyncio.get_running_loop().run_in_executor(None, fetch_cal_list)
        await ctx.send("📅 전체 출석 현황:")
        await ctx.send("전체 출석 일수: " + str(len(cal)))
        lines = [f"{d}: {v}" for d, v in sorted(cal.items())]
        pag = Paginator(prefix="```", suffix="```")
        for ln in lines:
            pag.add_line(ln)
        for page in pag.pages:
            await ctx.send(page)
    except Exception as e:
        await ctx.send(f"🚨 오류: {e}")

# ── /remaining  |  !남은시간 ────────────────────────
@bot.hybrid_command(
    name="remaining",
    aliases=["남은시간"],
    description="다음 자동 알림까지 남은 시간을 보여줍니다.",
    name_localizations={"ko": "남은시간"},
    description_localizations={"ko": "다음 자동 알림까지 남은 시간을 보여줍니다."},
)
async def cmd_remaining(ctx: commands.Context):
    if attendance_loop.next_iteration is None:
        await ctx.send("⏳ 아직 루프가 초기화되지 않았어요.")
        return
    now   = datetime.now(timezone.utc)
    nxt   = attendance_loop.next_iteration
    delta = nxt - now
    m, s  = divmod(int(delta.total_seconds()), 60)
    await ctx.send(f"⏰ 다음 자동 알림까지 {m}분 {s}초 남았습니다.")

# ── on_ready  (sync & 루프 시작) ─────────────────────
@bot.event
async def on_ready():
    print(f"✅ Bot ready: {bot.user} ({bot.user.id})")
    ch = bot.get_channel(CHANNEL_ID)
    if ch:
        await ch.send("🤖 봇이 실행되었습니다!")
    if not attendance_loop.is_running():
        attendance_loop.start()
    # Slash Command 동기화
    try:
        await bot.tree.sync()
    except Exception as e:
        print("Slash command sync failed:", e)

bot.run(TOKEN)   # 실시간 로그가 필요하면 python -u …
