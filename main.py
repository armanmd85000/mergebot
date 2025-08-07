# main.py

# --- VJ-Forward-Bot Core Imports ---
import asyncio
import logging
from pyrogram import Client, filters, idle
from config import Config

# --- gita1 Features Imports ---
import re
from pyrogram.enums import ParseMode, MessageMediaType, ChatType, ChatMemberStatus
from pyrogram.errors import FloodWait, UserNotParticipant, ChannelInvalid, PeerIdInvalid
from pyrogram.types import Message

# FORWARD BOT INIT
bot = Client(
    Config.BOT_SESSION,
    bot_token=Config.BOT_TOKEN,
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    plugins=dict(root="plugins")
)

# ------- gita1 FEATURE STATE -------
class Gita1State:
    OFFSET = 0
    PROCESSING = False
    BATCH_MODE = False
    PHOTO_FORWARD_MODE = False
    SOURCE_CHAT = None
    TARGET_CHAT = None
    START_ID = None
    END_ID = None
    CURRENT_TASK = None
    REPLACEMENTS = {}
    ADMIN_CACHE = {}
    MESSAGE_FILTERS = {
        'text': True, 'photo': True, 'video': True, 'document': True, 'audio': True,
        'animation': True, 'voice': True, 'video_note': True, 'sticker': True,
        'poll': True, 'contact': True
    }
    MAX_RETRIES = 3
    DELAY_BETWEEN_MESSAGES = 0.3
    MAX_MESSAGES_PER_BATCH = 100000

# --- gita1 utility functions ---
def modify_content(text, offset):
    if not text:
        return text
    for original, replacement in sorted(Gita1State.REPLACEMENTS.items(), key=lambda x: (-len(x[0]), x[0].lower())):
        text = re.sub(rf'\b{re.escape(original)}\b', replacement, text, flags=re.IGNORECASE)
    def replacer(match):
        prefix, domain, chat_part, chat_id, post_id = match.groups()
        return f"{prefix or ''}{domain}/{chat_part or ''}{chat_id}/{int(post_id) + offset}"
    pattern = r'(https?://)?(t\.me|telegram\.(?:me|dog))/(c/)?([^/\s]+)/(\d+)'
    return re.sub(pattern, replacer, text)

async def verify_permissions(client, chat_id):
    try:
        if isinstance(chat_id, str):
            chat = await client.get_chat(chat_id)
            chat_id = chat.id
        if chat_id in Gita1State.ADMIN_CACHE:
            return Gita1State.ADMIN_CACHE[chat_id]
        chat = await client.get_chat(chat_id)
        if chat.type not in [ChatType.CHANNEL, ChatType.SUPERGROUP]:
            result = (False, "Only channels and supergroups are supported")
            Gita1State.ADMIN_CACHE[chat_id] = result
            return result
        try:
            member = await client.get_chat_member(chat.id, "me")
        except UserNotParticipant:
            result = (False, "Bot is not a member of this chat")
            Gita1State.ADMIN_CACHE[chat_id] = result
            return result
        if member.status != ChatMemberStatus.ADMINISTRATOR:
            result = (False, "Bot needs to be admin")
            Gita1State.ADMIN_CACHE[chat_id] = result
            return result
        result = (True, "OK")
        Gita1State.ADMIN_CACHE[chat_id] = result
        return result
    except (ChannelInvalid, PeerIdInvalid):
        return (False, "Invalid chat ID")
    except Exception as e:
        return (False, f"Error: {str(e)}")

# --- gita1 COMMAND HANDLERS ---
@bot.on_message(filters.command(["gita_start", "gita_help"]))
async def gita_help(client, message):
    await message.reply(
        "🌀 *gita1 Features Loaded:*\n"
        "- Batch process with offset (see /gita_batch, /gita_addnumber, /gita_lessnumber, /gita_setoffset)\n"
        "- Photo forward mode with link (/gita_photoforward)\n"
        "- Filter types, word replacements, offset controls\n"
        "All gita1 commands are prefixed with `/gita_` to avoid conflicts.",
        parse_mode=ParseMode.MARKDOWN
    )

@bot.on_message(filters.command(["gita_addnumber"]))
async def gita_add_offset(client, message):
    try:
        offset = int(message.command[1])
        Gita1State.OFFSET += offset
        await message.reply(f"✅ Offset increased by {offset}. New offset: {Gita1State.OFFSET}")
    except (IndexError, ValueError):
        await message.reply("❌ Usage: /gita_addnumber N")

@bot.on_message(filters.command(["gita_lessnumber"]))
async def gita_sub_offset(client, message):
    try:
        offset = int(message.command[1])
        Gita1State.OFFSET -= offset
        await message.reply(f"✅ Offset decreased by {offset}. New offset: {Gita1State.OFFSET}")
    except (IndexError, ValueError):
        await message.reply("❌ Usage: /gita_lessnumber N")

@bot.on_message(filters.command(["gita_setoffset"]))
async def gita_set_offset(client, message):
    try:
        Gita1State.OFFSET = int(message.command[1])
        await message.reply(f"✅ Offset set to {Gita1State.OFFSET}")
    except (IndexError, ValueError):
        await message.reply("❌ Usage: /gita_setoffset N")

@bot.on_message(filters.command(["gita_replacewords"]))
async def gita_show_replacements(client, message):
    if not Gita1State.REPLACEMENTS:
        await message.reply("No word replacements set")
    else:
        await message.reply(
            "\n".join([f"`{o}` → `{r}`" for o, r in Gita1State.REPLACEMENTS.items()]),
            parse_mode=ParseMode.MARKDOWN
        )

@bot.on_message(filters.command(["gita_addreplace"]))
async def gita_add_replacement(client, message):
    try:
        orig, repl = message.command[1], message.command[2]
        Gita1State.REPLACEMENTS[orig] = repl
        await message.reply(f"Added: `{orig}` → `{repl}`", parse_mode=ParseMode.MARKDOWN)
    except IndexError:
        await message.reply("❌ Usage: /gita_addreplace ORIG REPL")

@bot.on_message(filters.command(["gita_removereplace"]))
async def gita_removerepl(client, message):
    try:
        word = message.command[1]
        if word in Gita1State.REPLACEMENTS:
            del Gita1State.REPLACEMENTS[word]
            await message.reply(f"Removed: `{word}`", parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply("No such replacement")
    except IndexError:
        await message.reply("❌ Usage: /gita_removereplace WORD")

@bot.on_message(filters.command(["gita_status"]))
async def gita_status(client, message):
    await message.reply(
        f"🌀 Offset: {Gita1State.OFFSET}\n"
        f"Replacements: {Gita1State.REPLACEMENTS}\n"
        f"Processing: {Gita1State.PROCESSING}\n"
        f"Photo Forward Mode: {Gita1State.PHOTO_FORWARD_MODE}",
        parse_mode=ParseMode.MARKDOWN
    )

@bot.on_message(filters.command(["gita_reset"]))
async def gita_reset(client, message):
    Gita1State.OFFSET, Gita1State.REPLACEMENTS = 0, {}
    Gita1State.PROCESSING, Gita1State.BATCH_MODE, Gita1State.PHOTO_FORWARD_MODE = False, False, False
    Gita1State.SOURCE_CHAT = Gita1State.TARGET_CHAT = None
    await message.reply("gita1 features: ✅ Reset all settings")

# Similarly, add the remaining, more advanced gita1 commands (like /gita_setchat, /gita_filtertypes, etc.)
# Prefix all gita1 commands as indicated.

# MAIN RUN LOOP
if __name__ == "__main__":
    bot.run()
                   
