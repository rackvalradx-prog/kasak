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
    if not os.path.exists(USERS_FILE):
        return
    f = open(USERS_FILE, "r")
    for line in f:
        line = line.strip()
        if line.isdigit():
            known_users.add(int(line))
    f.close()


def track_user(user_id):
    if not user_id:
        return
    if user_id in known_users:
        return
    known_users.add(user_id)
    f = open(USERS_FILE, "a")
    f.write(str(user_id) + "\n")
    f.close()


def clean_address(addr):
    if not addr:
        return "None"
    if "!" in addr:
        parts = []
        for p in addr.split("!"):
            p = p.strip()
            if p and p != ".":
                parts.append(p)
        if parts:
            return ", ".join(parts)
        return "None"
    cleaned = " ".join(addr.split())
    if cleaned:
        return cleaned
    return "None"


async def safe_delete(context, chat_id, msg_id):
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
    except Exception:
        return False
    if member.status == "member":
        return True
    if member.status == "administrator":
        return True
    if member.status == "creator":
        return True
    return False


async def send_join_message(update, context):
    user = update.message.from_user
    first_name = user.first_name or "User"
    btn1 = InlineKeyboardButton("Join Channel", url=CHANNEL_LINK)
    btn2 = InlineKeyboardButton("I have Joined", callback_data="check_joined")
    join_button = InlineKeyboardMarkup([[btn1], [btn2]])
    text = "Hello " + first_name + "!\n\nJoin our channel to use this bot.\nAfter joining, click I have Joined button."
    sent = await update.message.reply_text(text, reply_markup=join_button)
    context.user_data["join_msg_id"] = sent.message_id


async def delete_join_message(context, chat_id):
    msg_id = context.user_data.get("join_msg_id")
    if not msg_id:
        return
    await safe_delete(context, chat_id, msg_id)
    context.user_data.pop("join_msg_id", None)
    await context.bot.send_message(
        chat_id=chat_id,
        text="You have successfully joined our channel!\n\nYou can now use the bot freely. Send /start to begin.",
    )


async def check_joined_callback(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    track_user(user_id)
    member_ok = await is_member(user_id, context)
    if not member_ok:
        await query.answer("You have not joined yet! Please join first.", show_alert=True)
        return
    await safe_delete(context, query.message.chat_id, query.message.message_id)
    context.user_data.pop("join_msg_id", None)
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="You have successfully joined our channel!\n\nYou can now use the bot freely. Send /start to begin.",
    )


def main_menu_markup():
    btn_user = KeyboardButton(
        text="User",
        request_users=KeyboardButtonRequestUsers(request_id=1, max_quantity=1),
    )
    btn_group = KeyboardButton(
        text="Group",
        request_chat=KeyboardButtonRequestChat(request_id=2, chat_is_channel=False),
    )
    btn_channel = KeyboardButton(
        text="Channel",
        request_chat=KeyboardButtonRequestChat(request_id=3, chat_is_channel=True),
    )
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


async def gate(update, context):
    user_id = update.message.from_user.id
    track_user(user_id)
    chat_id = update.message.chat_id
    member_ok = await is_member(user_id, context)
    if not member_ok:
        await send_join_message(update, context)
        return False
    await delete_join_message(context, chat_id)
    return True


async def start(update, context):
    ok = await gate(update, context)
    if not ok:
        return
    context.user_data.clear()
    await show_main_menu(update, context)


async def back_command(update, context):
    ok = await gate(update, context)
    if not ok:
        return
    await show_main_menu(update, context, header="Back to main menu.")


async def cancel_command(update, context):
    ok = await gate(update, context)
    if not ok:
        return
    context.user_data.clear()
    await show_main_menu(update, context, header="Cancelled.")


async def settings_command(update, context):
    ok = await gate(update, context)
    if not ok:
        return
    settings_text = (
        "*Settings*\n\n"
        "*Username / UID Lookup* — Send any @username or numeric ID\n\n"
        "*Phone Number Lookup* — `/num <number>`\n\n"
        "*Aadhar Lookup* — `/aadhar <12-digit number>`\n\n"
        "*User / Group / Channel ID* — Use the buttons below\n\n"
        "*Help Guide* — Use /help to see full instructions\n\n"
        "_Thanks for using this bot._"
    )
    await update.message.reply_text(settings_text, parse_mode="Markdown")


async def help_command(update, context):
    ok = await gate(update, context)
    if not ok:
        return
    help_text = (
        "*Welcome to @racksunbot Help*\n\n"
        "*Username / UID Lookup* — Send the username or UID directly.\n"
        "Examples: `@username` or `1234567890`\n\n"
        "*Phone Number Lookup* — `/num 9876543210`\n\n"
        "*Aadhar Lookup* — `/aadhar 652507323571`\n\n"
        "*Available Commands*\n"
        "/start /num /aadhar /settings /back /cancel /help"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def stats_command(update, context):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        return
    msg = "*Bot Stats*\n\n*Total Users:* `" + str(len(known_users)) + "`"
    await update.message.reply_text(msg, parse_mode="Markdown")


async def send_one_user(context, uid, reply_msg, text_after, from_chat_id):
    try:
        if reply_msg:
            await context.bot.copy_message(
                chat_id=uid,
                from_chat_id=from_chat_id,
                message_id=reply_msg.message_id,
            )
        else:
            await context.bot.send_message(chat_id=uid, text=text_after)
        return True
    except Exception:
        return False


async def broadcast_command(update, context):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("Not authorized.")
        return
    reply_msg = update.message.reply_to_message
    text_after = update.message.text.partition(" ")[2].strip()
    if not reply_msg and not text_after:
        await update.message.reply_text("Usage: /broadcast <message>  or reply to any message with /broadcast")
        return
    total = len(known_users)
    if total == 0:
        await update.message.reply_text("No users to broadcast to yet.")
        return
    status = await update.message.reply_text("Broadcasting to " + str(total) + " users...")
    sent = 0
    failed = 0
    from_chat_id = update.message.chat_id
    for uid in list(known_users):
        ok = await send_one_user(context, uid, reply_msg, text_after, from_chat_id)
        if ok:
            sent = sent + 1
        else:
            failed = failed + 1
        await asyncio.sleep(0.05)
    report = "Broadcast Complete\nTotal: " + str(total) + "\nSent: " + str(sent) + "\nFailed: " + str(failed)
    await update.message.reply_text(report)


async def send_long(update, text):
    chunk = ""
    for line in text.split("\n"):
        if len(chunk) + len(line) + 1 > 3800:
            await update.message.reply_text(chunk, parse_mode="Markdown")
            chunk = line + "\n"
        else:
            chunk = chunk + line + "\n"
    if chunk.strip():
        await update.message.reply_text(chunk, parse_mode="Markdown")


async def num_lookup(update, context):
    ok = await gate(update, context)
    if not ok:
        return
    chat_id = update.message.chat_id
    if not context.args:
        await update.message.reply_text("*Usage:* `/num 9876543219`", parse_mode="Markdown")
        return
    number = context.args[0].replace("+", "").replace(" ", "").replace("-", "")
    searching = await update.message.reply_text("Searching...")
    url = NUMBER_API_URL.format(number=number)
    try:
        res = requests.get(url, timeout=15)
        data = res.json()
    except Exception as e:
        await safe_delete(context, chat_id, searching.message_id)
        await update.message.reply_text("Error:\n" + str(e))
        return
    entries = []
    if isinstance(data, dict):
        for k in data:
            v = data[k]
            if k.isdigit() and isinstance(v, dict):
                entries.append(v)
    if not entries:
        await safe_delete(context, chat_id, searching.message_id)
        await update.message.reply_text("*Data Not Found!*\n\nNo information found for this number.", parse_mode="Markdown")
        return
    header = "*Number:* `" + number + "`\n*Total Records:* `" + str(len(entries)) + "`\n"
    blocks = [header]
    i = 0
    for entry in entries:
        i = i + 1
        block = "\n*Record " + str(i) + "*\n"
        block = block + "*Name:* `" + str(entry.get("name") or "None") + "`\n"
        block = block + "*Father:* `" + str(entry.get("fname") or "None") + "`\n"
        block = block + "*Mobile:* `" + str(entry.get("mobile") or "None") + "`\n"
        block = block + "*Alt Mobile:* `" + str(entry.get("alt") or "None") + "`\n"
        block = block + "*National ID:* `" + str(entry.get("id") or "None") + "`\n"
        block = block + "*Email:* `" + str(entry.get("email") or "None") + "`\n"
        block = block + "*Circle:* `" + str(entry.get("circle") or "None") + "`\n"
        block = block + "*Address:* `" + clean_address(entry.get("address")) + "`"
        blocks.append(block)
    text = "\n".join(blocks)
    await safe_delete(context, chat_id, searching.message_id)
    await send_long(update, text)


async def aadhar_lookup(update, context):
    ok = await gate(update, context)
    if not ok:
        return
    chat_id = update.message.chat_id
    if not context.args:
        await update.message.reply_text("*Usage:* `/aadhar 652507323571`", parse_mode="Markdown")
        return
    aadhar = context.args[0].replace(" ", "").replace("-", "")
    searching = await update.message.reply_text("Searching...")
    url = AADHAR_API_URL.format(aadhar=aadhar)
    try:
        res = requests.get(url, timeout=15)
        data = res.json()
    except Exception as e:
        await safe_delete(context, chat_id, searching.message_id)
        await update.message.reply_text("Error:\n" + str(e))
        return
    entries = []
    if isinstance(data, dict):
        for k in data:
            v = data[k]
            if k.isdigit() and isinstance(v, dict):
                entries.append(v)
    if not entries:
        await safe_delete(context, chat_id, searching.message_id)
        await update.message.reply_text("*Data Not Found!*\n\nNo information found for this Aadhar.", parse_mode="Markdown")
        return
    header = "*Aadhar:* `" + aadhar + "`\n*Total Records:* `" + str(len(entries)) + "`\n"
    blocks = [header]
    i = 0
    for entry in entries:
        i = i + 1
        block = "\n*Record " + str(i) + "*\n"
        block = block + "*Name:* `" + str(entry.get("name") or "None") + "`\n"
        block = block + "*Father:* `" + str(entry.get("fname") or "None") + "`\n"
        block = block + "*Mobile:* `" + str(entry.get("mobile") or "None") + "`\n"
        block = block + "*Alt Mobile:* `" + str(entry.get("alt") or "None") + "`\n"
        block = block + "*Email:* `" + str(entry.get("email") or "None") + "`\n"
        block = block + "*Circle:* `" + str(entry.get("circle") or "None") + "`\n"
        block = block + "*Address:* `" + clean_address(entry.get("address")) + "`"
        blocks.append(block)
    text = "\n".join(blocks)
    await safe_delete(context, chat_id, searching.message_id)
    await send_long(update, text)


async def handle_users_shared(update, context):
    ok = await gate(update, context)
    if not ok:
        return
    if not update.message.users_shared:
        return
    for user in update.message.users_shared.users:
        await update.message.reply_text("*User ID:* `" + str(user.user_id) + "`", parse_mode="Markdown")


async def handle_chat_shared(update, context):
    ok = await gate(update, context)
    if not ok:
        return
    if not update.message.chat_shared:
        return
    await update.message.reply_text("*Chat ID:* `" + str(update.message.chat_shared.chat_id) + "`", parse_mode="Markdown")


async def lookup(update, context):
    ok = await gate(update, context)
    if not ok:
        return
    chat_id = update.message.chat_id
    user_input = update.message.text.strip()
    is_username = user_input.startswith("@") and len(user_input) > 1
    digits_only = user_input.lstrip("+")
    is_number = digits_only.isdigit() and len(digits_only) >= 7
    if not is_username and not is_number:
        return
    searching = await update.message.reply_text("Searching...")
    url = BASE_URL + user_input
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
    except Exception as e:
        await safe_delete(context, chat_id, searching.message_id)
        await update.message.reply_text("Error:\n" + str(e))
        return
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
            for k in result:
                v = result[k]
                if k != "success" and k != "msg":
                    fields[k] = v
            if not fields:
                not_found = True
            else:
                lines = ["*Result:*\n"]
                for key in fields:
                    value = fields[key]
                    label = key.replace("_", " ").title()
                    lines.append("*" + label + ":* `" + str(value) + "`")
                text = "\n".join(lines)
    elif not result:
        not_found = True
    else:
        text = "*Result:*\n`" + str(result) + "`"
    if not_found:
        text = "*Data Not Found!*\n\nNo information found for this username."
    await safe_delete(context, chat_id, searching.message_id)
    await update.message.reply_text(text, parse_mode="Markdown")


if __name__ == "__main__":
    load_users()
    keep_alive()
    print("Flask Server Started!")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("num", num_lookup))
    app.add_handler(CommandHandler("aadhar", aadhar_lookup))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("back", back_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CallbackQueryHandler(check_joined_callback, pattern="check_joined"))
    app.add_handler(MessageHandler(filters.StatusUpdate.USERS_SHARED, handle_users_shared))
    app.add_handler(MessageHandler(filters.StatusUpdate.CHAT_SHARED, handle_chat_shared))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lookup))
    print("Bot is Online!")
    app.run_polling()
