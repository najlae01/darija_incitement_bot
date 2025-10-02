import os, asyncio, json, time, logging
from datetime import timedelta, datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from translit import arabizi_to_arabic, normalize
from moderation import openai_moderate, tierb_inference
from heuristics import incitement_bonus

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OWNER_USER_ID = int(os.getenv("OWNER_USER_ID", "0"))
MOD_QUEUE_CHANNEL_ID = int(os.getenv("MOD_QUEUE_CHANNEL_ID", "0"))

THRESH_TEMP_MUTE = float(os.getenv("THRESH_TEMP_MUTE", "0.65"))
THRESH_ESCALATE  = float(os.getenv("THRESH_ESCALATE",  "0.85"))
THRESH_AUTO_BAN  = float(os.getenv("THRESH_AUTO_BAN",  "0.95"))

ACTION_DELETE_MESSAGE = os.getenv("ACTION_DELETE_MESSAGE", "true").lower() == "true"
ACTION_WARN_USER      = os.getenv("ACTION_WARN_USER", "true").lower() == "true"
ACTION_TEMP_MUTE      = os.getenv("ACTION_TEMP_MUTE", "true").lower() == "true"
ACTION_AUTO_BAN       = os.getenv("ACTION_AUTO_BAN", "false").lower() == "true"

TEMP_MUTE_SECONDS = int(os.getenv("TEMP_MUTE_SECONDS", "1800"))
CONTEXT_WINDOW = int(os.getenv("CONTEXT_WINDOW", "2"))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

AUDIT_LOG = "audit_incitement.jsonl"

def log_event(payload: dict):
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

async def get_context_snippets(message: discord.Message, n: int):
    snippets = []
    try:
        async for m in message.channel.history(limit=n+1, oldest_first=False):
            if m.id == message.id:
                continue
            snippets.append(f"{m.author.display_name}: {m.content}")
            if len(snippets) >= n:
                break
    except Exception:
        pass
    return list(reversed(snippets))

def score_message(text_arabic: str, context_text: str = "", text_raw_norm: str = "") -> tuple[float, dict]:
    """
    - text_arabic: transliterated/Arabic-normalized string (we send this to Tier A/B)
    - text_raw_norm: the normalized raw message (Latin/Arabizi as typed)
    """
    # Tier A (OpenAI moderation) on Arabic-normalized text + context
    mod = openai_moderate(text_arabic + ("\n\nCONTEXT:\n" + context_text if context_text else ""))
    score = float(mod.get("violence_score", 0.0))

    # Tier B (optional custom endpoint)
    b = tierb_inference(text_arabic, context_text)
    if b and isinstance(b.get("incitement_score"), (int, float)):
        score = max(score, float(b["incitement_score"]))
        cats = mod.get("categories", {})
        cats["tier_b_used"] = True
        mod["categories"] = cats

    # Heuristic bonus on BOTH forms
    bonus_a = incitement_bonus(text_arabic)
    bonus_r = incitement_bonus(text_raw_norm or "")
    score += max(bonus_a, bonus_r)

    return min(score, 1.0), mod

async def warn_user(user: discord.Member, reason: str, message_link: str):
    try:
        await user.send(
            f"⚠️ **Warning / تحذير**: Paimon doesn't like this.\n"
            f"Please keep it peaceful and don’t incite violence or war.\n"
            f"من فضلك خليك مسالم، وما تحرضش على العنف ولا الحرب.\n"
            f"Reference / المرجع: {message_link}"
        )
    except Exception:
        pass  # user may have DMs closed

async def temp_mute(member: discord.Member, seconds: int, reason: str):
    try:
        until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        await member.edit(communication_disabled_until=until, reason=reason)
    except Exception as e:
        logging.warning(f"Failed to timeout member: {e}")

async def escalate_to_mods(message: discord.Message, score: float, details: dict):
    guild = message.guild
    ch = guild.get_channel(MOD_QUEUE_CHANNEL_ID) if guild else None
    content_preview = (message.content[:800] + ("…" if len(message.content) > 800 else ""))

    embed = discord.Embed(
        title="⚠️ Incitement review needed",
        description=f"**Channel:** {message.channel.mention}\n"
                    f"**Score:** {score:.2f}\n"
                    f"**Jump:** [link]({message.jump_url})",
        color=0xE67E22
    )

    # Explicitly show author info
    embed.add_field(
        name="Author",
        value=(f"{message.author.mention}\n"
               f"Username: {message.author} (ID: {message.author.id})"),
        inline=False
    )
    embed.add_field(
        name="Message",
        value=content_preview or "*<no text>*",
        inline=False
    )
    embed.add_field(
        name="Details",
        value=f"Categories: {details.get('categories', {})}",
        inline=False
    )

    try:
        if ch is None:
            raise PermissionError("Mod queue channel not found")
        perms = ch.permissions_for(guild.me)
        if not (perms.view_channel and perms.send_messages):
            raise PermissionError("Bot lacks view/send in mod queue")

        await ch.send(embed=embed)
    except Exception as e:
        try:
            perms_here = message.channel.permissions_for(guild.me)
            if perms_here.send_messages:
                await message.channel.send(
                    f"🛡️ I couldn’t post to the mod queue ({e}). "
                    f"Please check `MOD_QUEUE_CHANNEL_ID` and channel permissions."
                )
        except Exception:
            pass
        logging.warning(f"Escalation failed: {e}")

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
    except Exception as e:
        logging.warning(f"Slash sync failed: {e}")
    logging.info(f"Logged in as {bot.user}")

@bot.tree.command(name="incitement", description="Admin tools for incitement moderation.")
@app_commands.describe(action="review: show last N flags")
@app_commands.describe(n="how many items to show (default 5)")
async def incitement(interaction: discord.Interaction, action: str, n: int = 5):
    if interaction.user.id != OWNER_USER_ID and not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Unauthorized.", ephemeral=True)
        return
    if action.lower() == "review":
        # stream last N items
        items = []
        try:
            with open(AUDIT_LOG, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if len(items) >= n:
                        break
                    items.append(json.loads(line))
        except FileNotFoundError:
            pass
        if not items:
            await interaction.response.send_message("No audit entries yet.", ephemeral=True)
            return
        out = []
        for it in items:
            out.append(f"- **{it.get('author_name')}** in <#{it.get('channel_id')}> — score `{it.get('score'):.2f}` — [jump]({it.get('jump_url')})\n"
                       f"  `{it.get('text')[:120].replace('`','')}{'…' if len(it.get('text'))>120 else ''}`")
        await interaction.response.send_message("\n".join(out), ephemeral=True)
    else:
        await interaction.response.send_message("Unknown action.", ephemeral=True)

@bot.event
async def on_message(message: discord.Message):
    logging.info(f"Seen: {message.content} from {message.author}")
    if message.author.bot:
        return
    # Skip DMs (optional): handle only guild messages
    if not message.guild:
        return

    raw = message.content or ""
    if not raw.strip():
        return

    # 1) Normalize + transliterate
    norm = normalize(raw)
    ar = arabizi_to_arabic(norm)

    # 2) Context window
    ctx_snips = await get_context_snippets(message, CONTEXT_WINDOW)
    ctx = "\n".join(ctx_snips)

    # 3) Score
    score, details = score_message(ar, ctx, text_raw_norm=norm)

    action_taken = None
    reason = "suspected incitement to violence"

    if score >= THRESH_AUTO_BAN and ACTION_AUTO_BAN:
        try:
            await message.author.ban(reason=reason)
            action_taken = "auto_ban"
        except Exception as e:
            logging.warning(f"Ban failed: {e}")
            await escalate_to_mods(message, score, details)
            action_taken = "escalated_ban_failed"
    elif score >= THRESH_ESCALATE:
        await escalate_to_mods(message, score, details)
        action_taken = "escalate"
        if ACTION_TEMP_MUTE:
            await temp_mute(message.author, TEMP_MUTE_SECONDS, reason)
    elif score >= THRESH_TEMP_MUTE:
        if ACTION_WARN_USER:
            await warn_user(message.author, reason, message.jump_url)
        if ACTION_TEMP_MUTE:
            await temp_mute(message.author, TEMP_MUTE_SECONDS, reason)
        action_taken = "warn_and_timeout"

    # Optional: delete message on any action
    if action_taken and ACTION_DELETE_MESSAGE:
        try:
            await message.delete()
        except Exception:
            pass

    # Log audit
    if action_taken:
        log_event({
            "ts": time.time(),
            "guild_id": message.guild.id if message.guild else None,
            "channel_id": message.channel.id,
            "message_id": message.id,
            "author_id": message.author.id,
            "author_name": str(message.author),
            "score": score,
            "details": details,
            "text": raw,
            "normalized": ar,
            "ctx": ctx,
            "action": action_taken,
            "jump_url": message.jump_url,
        })

    # Allow commands to work
    await bot.process_commands(message)

if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_BOT_TOKEN missing in environment.")
    bot.run(TOKEN)
