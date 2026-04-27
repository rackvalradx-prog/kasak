import os
import asyncio
import requests
from flask import Flask
from threading import Thread
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    KeyboardButtonRequestUsers,
    KeyboardButtonRequestChat,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.error import Forbidden, BadRequest, RetryAfter
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")

ADMIN_ID = 8300271033

BASE_URL = "https://api.subhxcosmo.in/api?key=RACKSUN&type=tg&term="
NUMBER_API_URL = "https://ayush-multi-api.vercel.app/api/num?term={number}"
AADHAR_API_URL = "https://ayush-multi-api.vercel.app/api/adhar?term={aadhar}"
CHANNEL_USERNAME = "@racksun19"
CHANNEL_LINK = "https://t.me/racksun19"

USERS_FILE = "users.txt"
known_users = set()


def load_users():
    global known_users
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line.isdigit():
                    known_users.add(int(line))
    print("Loaded " + str(len(known_users)) + " users from " + USERS_FILE)


def track_user(user_id):
    if user_id and user_id not in known_users:
        known_users.add(user_id)
        try:
            with open(USERS_FILE, "a") as f:
                f.write(str(user_id) + "\n")
        except Exception as e:
            print("track_user error:", e)


def clean_address(addr):
    if not addr:
        return "None"
    if "!" in addr:
        parts = [p.strip() for p in addr.split("!") if p and p.strip() and p.strip() != "."]
        return ", ".join(parts) if parts else "None"
    cleaned = " ".join(addr.split())
    return cleaned if cleaned else "None"


async def delete_searching(context, chat_id, msg_id):
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except Exception:
        pass


flask_app = Flask(__name__)


@flask_app.route("/")
def home():
    return "Bot is Alive!"


def run_flask():
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host="0.0.0.0", port=port)


def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()


async def is_member(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False


async def send_join_message(update, context):
    user = update.message.from_user
    first_name = user.first_name or "User"
    join_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ I have Joined", callback_data="check_joined")]
    ])
    text = "⚠️ *Hello " + first_name + "!*\n\nJoin our channel to use this bot.\nAfter joining, click *I have Joined* button."
    sent = await update.message.reply_text(text, reply_markup=join_button, parse_mode="Markdown")
    context.user_data["join_msg_id"] = sent.message_id


async def delete_join_message(context, chat_id):
    msg_id = context.user_data.get("join_msg_id")
    if msg_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            pass
        context.user_data.pop("join_msg_id", None)
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ *You have successfully joined our channel!*\n\nYou can now use the bot freely. Send /start to begin.",
            parse_mode="Markdown"
        )


async def check_joined_callback(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    track_user(user_id)
    if await is_member(user_id, context):
        await query.message.delete()
        context.user_data.pop("join_msg_id", None)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ *You have successfully joined our channel!*\n\nYou can now use the bot freely. Send /start to begin.",
            parse_mode="Markdown"
        )
    else:
        await query.answer("❌ You have not joined yet! Please join first.", show_alert=True)


def main_menu_markup():
    btn_user = KeyboardButton(text="User", request_users=KeyboardButtonRequestUsers(request_id=1, max_quantity=1))
    btn_group = KeyboardButton(text="Group", request_chat=KeyboardButtonRequestChat(request_id=2, chat_is_channel=False))
    btn_channel = KeyboardButton(text="Channel", request_chat=KeyboardButtonRequestChat(request_id=3, chat_is_channel=True))
    return ReplyKeyboardMarkup([[btn_user, btn_group, btn_channel]], resize_keyboard=True)


async def show_main_menu(update, context, header=None):
    user_id = update.message.from_user.id
    parts = []
    if header:
        parts.append(header + "\n\n")
    parts.append("*Welcome To @racksunbot*\n\n")
    parts.append("*Your ID :* `" + str(user_id) + "`\n\n")
    parts.append("Send me a Telegram username or number to look up.\n")
    parts.append("Example: @username or 1234567890\n\n")
    parts.append("Or use the buttons below to get User/Group/Channel ID:")
    welcome_msg = "".join(parts)
    await update.message.reply_text(welcome_msg, reply_markup=main_menu_markup(), parse_mode="Markdown")


async def start(update, context):
    user_id = update.message.from_user.id
    track_user(user_id)
    chat_id = update.message.chat_id
    if not await is_member(user_id, context):
        await send_join_message(update, context)
        return
    await delete_join_message(context, chat_id)
    context.user_data.clear()
    await show_main_menu(update, context)


async def back_command(update, context):
    user_id = update.message.from_user.id
    track_user(user_id)
    chat_id = update.message.chat_id
    if not await is_member(user_id, context):
        await send_join_message(update, context)
        return
    await delete_join_message(context, chat_id)
    await show_main_menu(update, context, header="🔙 *Back to main menu.*")


async def cancel_command(update, context):
    user_id = update.message.from_user.id
    track_user(user_id)
    chat_id = update.message.chat_id
    if not await is_member(user_id, context):
        await send_join_message(update, context)
        return
    await delete_join_message(context, chat_id)
    context.user_data.clear()
    await show_main_menu(update, context, header="❌ *Cancelled.*")


async def settings_command(update, context):
    user_id = update.message.from_user.id
    track_user(user_id)
    chat_id = update.message.chat_id
    if not await is_member(user_id, context):
        await send_join_message(update, context)
        return
    await delete_join_message(context, chat_id)
    settings_text = (
        "⚙️ *Settings*\n\n"
        "*What this bot can do:*\n\n"
        "📱 *Username / UID Lookup*\n"
        "Send any @username or numeric ID to get details instantly\n\n"
        "📞 *Phone Number Lookup*\n"
        "Use `/num <number>` to fetch available information\n\n"
        "🪪 *Aadhar Lookup*\n"
        "Use `/aadhar <12-digit number>` to fetch info\n\n"
        "👥 *User / Group / Channel ID*\n"
        "Use the buttons below to get IDs easily\n\n"
        "⚡ *Fast and Automatic*\n"
        "No extra commands needed for basic lookups\n\n"
        "❓ *Help Guide*\n"
        "Use /help to see full instructions\n\n"
        "—\n\n"
        "_Thanks for using this bot._"
    )
    await update.message.reply_text(settings_text, parse_mode="Markdown")


async def help_command(update, context):
    user_id = update.message.from_user.id
    track_user(user_id)
    chat_id = update.message.chat_id
    if not await is_member(user_id, context):
        await send_join_message(update, context)
        return
    await delete_join_message(context, chat_id)
    help_text = (
        "🤖 *Welcome to @racksunbot Help*\n\n"
        "Here is how to use this bot:\n\n"
        "📱 *Telegram Username / UID Lookup*\n"
        "  Just send the username or UID directly in chat.\n"
        "  No command needed.\n\n"
        "  Examples:\n"
        "   • `@username`\n"
        "   • `1234567890`\n\n"
        "📞 *Phone Number Lookup*\n"
        "  Use the /num command followed by the number.\n\n"
        "  Example:\n"
        "   • `/num 9876543210`\n\n"
        "🪪 *Aadhar Lookup*\n"
        "  Use the /aadhar command followed by 12-digit Aadhar.\n\n"
        "  Example:\n"
        "   • `/aadhar 652507323571`\n\n"
        "📋 *Available Commands*\n"
        "  /start    — Start the bot\n"
        "  /num      — Phone number lookup\n"
        "  /aadhar   — Aadhar lookup\n"
        "  /settings — Show bot features\n"
        "  /back     — Back to main menu\n"
        "  /cancel   — Cancel current action\n"
        "  /help     — Show this help message"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def broadcast_command(update, context):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ *You are not authorized to use this command.*", parse_mode="Markdown")
        return
    reply_msg = update.message.reply_to_message
    text_after = update.message.text.partition(" ")[2].strip()
    if not reply_msg and not text_after:
        await update.message.reply_text(
            "*Usage:*\n"
            "1. `/broadcast <your message>` — text broadcast\n"
            "2. Reply to any message with `/broadcast` — copies that message to all users",
            parse_mode="Markdown"
        )
        return
    total = len(known_users)
    if total == 0:
        await update.message.reply_text("No users to broadcast to yet.")
        return
    status = await update.message.reply_text("📣 Broadcasting to " + str(total) + " users...")
    sent = 0
    failed = 0
    blocked = 0
    for uid in list(known_users):
        try:
            if reply_msg:
                await context.bot.copy_message(
                    chat_id=uid,
                    from_chat_id=update.message.chat_id,
                    message_id=reply_msg.message_id,
                )
            else:
                await context.bot.send_message(chat_id=uid, text=text_after)
            sent += 1
        except Forbidden:
            blocked += 1
        except BadRequest:
            failed += 1
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
            try:
                if reply_msg:
                    await context.bot.copy_message(
                        chat_id=uid,
                        from_chat_id=update.message.chat_id,
                        message_id=reply_msg.message_id,
                    )
                else:
                    await context.bot.send_message(chat_id=uid, text=text_after)
                sent += 1
            except Exception:
                failed += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    report = (
        "✅ *Broadcast Complete*\n\n"
        "*Total:* `" + str(total) + "`\n"
        "*Sent:* `" + str(sent) + "`\n"
        "*Blocked:* `" + str(blocked) + "`\n"
        "*Failed:* `" + str(failed) + "`"
    )
    try:
        await status.edit_text(report, parse_mode="Markdown")
    except Exception:
        await update.message.reply_text(report, parse_mode="Markdown")


async def stats_command(update, context):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        return
    await update.message.reply_text(
        "📊 *Bot Stats*\n\n*Total Users:* `" + str(len(known_users)) + "`",
        parse_mode="Markdown"
    )


async def users_command(update, context):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        return
    if not os.path.exists(USERS_FILE) or len(known_users) == 0:
        await update.message.reply_text("No users saved yet.")
        return
    try:
        with open(USERS_FILE, "rb") as f:
            await context.bot.send_document(
                chat_id=update.message.chat_id,
                document=f,
                filename="users.txt",
                caption="📂 *Users Backup*\n\n*Total Users:* `" + str(len(known_users)) + "`",
                parse_mode="Markdown",
            )
    except Exception as e:
        await update.message.reply_text("Error sending file:\n" + str(e))


async def num_lookup(update, context):
    user_id = update.message.from_user.id
    track_user(user_id)
    chat_id = update.message.chat_id
    if not await is_member(user_id, context):
        await send_join_message(update, context)
        return
    await delete_join_message(context, chat_id)
    if not context.args:
        await update.message.reply_text("*Usage:* `/num 9876543219`", parse_mode="Markdown")
        return
    number = context.args[0].replace("+", "").replace(" ", "").replace("-", "")
    searching = await update.message.reply_text("🔍 Searching...")
    try:
        url = NUMBER_API_URL.format(number=number)
        res = requests.get(url, timeout=15)
        data = res.json()
        entries = []
        if isinstance(data, dict):
            for k, v in data.items():
                if k.isdigit() and isinstance(v, dict):
                    entries.append(v)
        if not entries:
            await delete_searching(context, chat_id, searching.message_id)
            await update.message.reply_text("*Data Not Found!*\n\nNo information found for this number.", parse_mode="Markdown")
            return
        header = "*Number:* `" + number + "`\n*Total Records:* `" + str(len(entries)) + "`\n"
        blocks = [header]
        for i, entry in enumerate(entries, 1):
            block = "\n*Record " + str(i) + "*\n"
            block += "*Name:* `" + str(entry.get("name") or "None") + "`\n"
            block += "*Father:* `" + str(entry.get("fname") or "None") + "`\n"
            block += "*Mobile:* `" + str(entry.get("mobile") or "None") + "`\n"
            block += "*Alt Mobile:* `" + str(entry.get("alt") or "None") + "`\n"
            block += "*National ID:* `" + str(entry.get("id") or "None") + "`\n"
            block += "*Email:* `" + str(entry.get("email") or "None") + "`\n"
            block += "*Circle:* `" + str(entry.get("circle") or "None") + "`\n"
            block += "*Address:* `" + clean_address(entry.get("address")) + "`"
            blocks.append(block)
        text = "\n".join(blocks)
        await delete_searching(context, chat_id, searching.message_id)
        chunk = ""
        for line in text.split("\n"):
            if len(chunk) + len(line) + 1 > 3800:
                await update.message.reply_text(chunk, parse_mode="Markdown")
                chunk = line + "\n"
            else:
                chunk += line + "\n"
        if chunk.strip():
            await update.message.reply_text(chunk, parse_mode="Markdown")
    except Exception as e:
        await delete_searching(context, chat_id, searching.message_id)
        await update.message.reply_text("Error:\n" + str(e))


async def aadhar_lookup(update, context):
    user_id = update.message.from_user.id
    track_user(user_id)
    chat_id = update.message.chat_id
    if not await is_member(user_id, context):
        await send_join_message(update, context)
        return
    await delete_join_message(context, chat_id)
    if not context.args:
        await update.message.reply_text("*Usage:* `/aadhar 652507323571`", parse_mode="Markdown")
        return
    aadhar = context.args[0].replace(" ", "").replace("-", "")
    searching = await update.message.reply_text("🔍 Searching...")
    try:
        url = AADHAR_API_URL.format(aadhar=aadhar)
        res = requests.get(url, timeout=15)
        data = res.json()
        entries = []
        if isinstance(data, dict):
            for k, v in data.items():
                if k.isdigit() and isinstance(v, dict):
                    entries.append(v)
        if not entries:
            await delete_searching(context, chat_id, searching.message_id)
            await update.message.reply_text("*Data Not Found!*\n\nNo information found for this Aadhar.", parse_mode="Markdown")
            return
        header = "*Aadhar:* `" + aadhar + "`\n*Total Records:* `" + str(len(entries)) + "`\n"
        blocks = [header]
        for i, entry in enumerate(entries, 1):
            block = "\n*Record " + str(i) + "*\n"
            block += "*Name:* `" + str(entry.get("name") or "None") + "`\n"
            block += "*Father:* `" + str(entry.get("fname") or "None") + "`\n"
            block += "*Mobile:* `" + str(entry.get("mobile") or "None") + "`\n"
            block += "*Alt Mobile:* `" + str(entry.get("alt") or "None") + "`\n"
            block += "*Email:* `" + str(entry.get("email") or "None") + "`\n"
            block += "*Circle:* `" + str(entry.get("circle") or "None") + "`\n"
            block += "*Address:* `" + clean_address(entry.get("address")) + "`"
            blocks.append(block)
        text = "\n".join(blocks)
        await delete_searching(context, chat_id, searching.message_id)
        chunk = ""
        for line in text.split("\n"):
            if len(chunk) + len(line) + 1 > 3800:
                await update.message.reply_text(chunk, parse_mode="Markdown")
                chunk = line + "\n"
            else:
                chunk += line + "\n"
        if chunk.strip():
            await update.message.reply_text(chunk, parse_mode="Markdown")
    except Exception as e:
        await delete_searching(context, chat_id, searching.message_id)
        await update.message.reply_text("Error:\n" + str(e))


async def handle_users_shared(update, context):
    user_id = update.message.from_user.id
    track_user(user_id)
    chat_id = update.message.chat_id
    if not await is_member(user_id, context):
        await send_join_message(update, context)
        return
    await delete_join_message(context, chat_id)
    if update.message.users_shared:
        for user in update.message.users_shared.users:
            await update.message.reply_text("*User ID:* `" + str(user.user_id) + "`", parse_mode="Markdown")


async def handle_chat_shared(update, context):
    user_id = update.message.from_user.id
    track_user(user_id)
    chat_id = update.message.chat_id
    if not await is_member(user_id, context):
        await send_join_message(update, context)
        return
    await delete_join_message(context, chat_id)
    if update.message.chat_shared:
        await update.message.reply_text("*Chat ID:* `" + str(update.message.chat_shared.chat_id) + "`", parse_mode="Markdown")


async def lookup(update, context):
    user_id = update.message.from_user.id
    track_user(user_id)
    chat_id = update.message.chat_id
    if not await is_member(user_id, context):
        await send_join_message(update, context)
        return
    await delete_join_message(context, chat_id)
    user_input = update.message.text.strip()
    is_username = user_input.startswith("@") and len(user_input) > 1
    is_number = user_input.lstrip("+").isdigit() and len(user_input.lstrip("+")) >= 7
    if not is_username and not is_number:
        return
    searching = await update.message.reply_text("🔍 Searching...")
    try:
        url = BASE_URL + user_input
        res = requests.get(url, timeout=10)
        data = res.json()
        if "result" in data:
            result = data["result"]
        else:
            result = data
        not_found = False
        text = ""
        if isinstance(result, dict):
            if not result.get("success", True):
                not_found = True
            else:
                fields = {}
                for k, v in 
