import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta, UTC
import logging
from dotenv import load_dotenv
import os

# ==========================
# CONFIGURAÇÃO INICIAL
# ==========================

load_dotenv()
from typing import cast

TOKEN = cast(str, os.getenv("DISCORD_TOKEN"))

afk_env = os.getenv("AFK_MINUTES")

if afk_env is None:
    raise RuntimeError("AFK_MINUTES não definido no .env")

AFK_MINUTES = int(afk_env)
AFK_LIMIT = timedelta(minutes=AFK_MINUTES)

# ==========================
# LOGGING
# ==========================

handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")

# ==========================
# INTENTS
# ==========================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================
# CONTROLE DE ATIVIDADE
# ==========================

last_activity = {}

# ==========================
# EVENTOS
# ==========================


@bot.event
async def on_ready():
    print(f"{bot.user} conectado!")
    check_afk.start()


@bot.event
async def on_voice_state_update(member, before, after):
    """
    Atualiza timestamp quando:
    - Entra em canal
    - Sai
    - Troca de canal
    - Muta / Desmuta
    """

    if member.bot:
        return

    # Se entrou ou alterou algo em canal de voz
    if after.channel:
        last_activity[member.id] = datetime.now(UTC)
    else:
        # Saiu do canal
        last_activity.pop(member.id, None)


# ==========================
# LOOP DE VERIFICAÇÃO AFK
# ==========================


@tasks.loop(seconds=60)
async def check_afk():
    now = datetime.now(UTC)

    for guild in bot.guilds:
        for voice_channel in guild.voice_channels:
            for member in voice_channel.members:

                if member.bot:
                    continue

                last = last_activity.get(member.id)

                if not last:
                    # Se não tem registro ainda
                    last_activity[member.id] = now
                    continue

                if (now - last) > AFK_LIMIT:
                    try:
                        await member.move_to(None)
                        print(f"[AFK] {member} removido do canal {voice_channel.name}")
                        last_activity.pop(member.id, None)
                    except discord.Forbidden:
                        print(f"Sem permissão para remover {member}")
                    except Exception as e:
                        print(f"Erro ao remover {member}: {e}")


@check_afk.before_loop
async def before_check_afk():
    await bot.wait_until_ready()


# ==========================
# COMANDO OPCIONAL
# ==========================


@bot.command()
async def afktime(ctx):
    """Mostra o tempo configurado de AFK"""
    await ctx.send(f"Tempo limite de AFK: {AFK_MINUTES} minutos")


# ==========================
# EXECUÇÃO
# ==========================

bot.run(TOKEN, log_handler=handler, log_level=logging.INFO)
