# -*- coding: utf-8 -*-
import os, traceback
import discord
from discord.ext import tasks, commands
from check_attendance import check_attendance  # 같은 폴더라면 바로 import
from datetime import datetime

TOKEN       = os.getenv("DISCORD_TOKEN")      # 환경변수 or 직접 문자열
CHANNEL_ID  = int(os.getenv("CHANNEL_ID"))    # 알림 보낼 텍스트채널 ID

# ── Discord Intents (메시지 전송만이면 최소 설정) ───
intents = discord.Intents.default()           # 메시지 읽기는 불필요
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot logged in: {bot.user} (ID: {bot.user.id})")
    if not attendance_loop.is_running():
        attendance_loop.start()

# ── 1시간마다 출석 체크 루프 ───
@tasks.loop(hours=1)
async def attendance_loop():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    channel = bot.get_channel(CHANNEL_ID)

    try:
        ok = check_attendance()
        if not ok:
            await channel.send(f"❌ [{now}] 아직 미출석입니다! 빨리 출석하세요.")
    except Exception:
        err = traceback.format_exc(limit=1)
        await channel.send(f"🚨 [{now}] 출석 체크 중 오류!\n```{err}```")

# ── 봇 시작 ───
bot.run(TOKEN)
