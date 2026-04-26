import os
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
    raise ValueError("TELEGRAM_BOT_TOKEN not set!")

BASE_URL = "https://api.subhxcosmo.in/api?key=RACKSUN&type=tg&term="
NUM_API = "https://ayush-multi-api.vercel.app/api/num?term="
ADHAR_API = "https://ayush-multi-api.vercel.app/api/adhar?term="
VEH_API = "https://ayush-multi-api.vercel.app/api/veh?term="
CHANNEL = "@racksun19"
CHANNEL_LINK = "https://t.me/racksun19"
FATHER_KEY = "Father" + chr(39) + "s Name"


def clean_address(addr):
    if not addr:
        return "None"
    if "!" in addr:
        parts = [p.strip() for p in addr.split("!")
                 if p and p.strip() and p.strip() != "."]
        return ", ".join(parts) if parts else "None"
    cleaned = " ".join(addr.split())
    return cleaned if cleaned else "None"


async def del_msg(context, chat_id, msg_id):
    try:
        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=msg_id,
        )
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


async def is_member(uid, context):
    try:
        m = await context.bot.get_chat_member(
            chat_id=CHANNEL,
            user_id=uid,
        )
        return m.status in ["member", "administrator", "creator"]
    except Exception:
        return False


async def send_join(update, context):
    user = update.message.from_user
    fname = user.first_name or "User"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ I have Joined",
                              callback_data="check_joined")],
    ])
    text = ("⚠️ *Hello " + fname + "!*\n\n"
            "Join our channel to use this bot.\n"
            "After joining, click *I have Joined*.")
    sent = await update.message.reply_text(
        text, reply_markup=kb, parse_mode="Markdown",
    )
    context.user_data["join_msg_id"] = sent.message_id


async def del_join(context, chat_id):
    mid = context.user_data.get("join_msg_id")
    if not mid:
        return
    try:
        await context.bot.delete_message(
            chat_id=chat_id, message_id=mid,
        )
    except Exception:
        pass
    context.user_data.pop("join_msg_id", None)
    await context.bot.send_message(
        chat_id=chat_id,
        text=("✅ *You have successfully joined!*\n\n"
              "You can now use the bot. Send /start."),
        parse_mode="Markdown",
    )


async def gate(update, context):
    uid = update.message.from_user.id
    cid = update.message.chat_id
    if not await is_member(uid, context):
        await send_join(update, context)
        return False
    await del_join(context, cid)
    return True


async def check_joined_cb(update, context):
    q = update.callback_query
    uid = q.from_user.id
    if await is_member(uid, context):
        await q.message.delete()
        context.user_data.pop("join_msg_id", None)
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text=("✅ *You have successfully joined!*\n\n"
                  "You can now use the bot. Send /start."),
            parse_mode="Markdown",
        )
    else:
        await q.answer(
            "❌ Not joined yet! Please join first.",
            show_alert=True,
        )


def menu_kb():
    b1 = KeyboardButton(
        text="User",
        request_users=KeyboardButtonRequestUsers(
            request_id=1, max_quantity=1,
        ),
    )
    b2 = KeyboardButton(
        text="Group",
        request_chat=KeyboardButtonRequestChat(
            request_id=2, chat_is_channel=False,
        ),
    )
    b3 = KeyboardButton(
        text="Channel",
        request_chat=KeyboardButtonRequestChat(
            request_id=3, chat_is_channel=True,
        ),
    )
    return ReplyKeyboardMarkup([[b1, b2, b3]], resize_keyboard=True)


async def show_menu(update, context, header=None):
    uid = update.message.from_user.id
    parts = []
    if header:
        parts.append(header + "\n\n")
    parts.append("*Welcome To @racksunbot*\n\n")
    parts.append("*Your ID :* `" + str(uid) + "`\n\n")
    parts.append("Send a Telegram username or number.\n")
    parts.append("Example: @username or 1234567890\n\n")
    parts.append("Or use buttons below to get IDs:")
    msg = "".join(parts)
    await update.message.reply_text(
        msg, reply_markup=menu_kb(), parse_mode="Markdown",
    )


async def start(update, context):
    if not await gate(update, context):
        return
    context.user_data.clear()
    await show_menu(update, context)


async def back_cmd(update, context):
    if not await gate(update, context):
        return
    await show_menu(update, context, header="🔙 *Back to main menu.*")


async def cancel_cmd(update, context):
    if not await gate(update, context):
        return
    context.user_data.clear()
    await show_menu(update, context, header="❌ *Cancelled.*")


async def settings_cmd(update, context):
    if not await gate(update, context):
        return
    text = (
        "⚙️ *Settings*\n\n"
        "*What this bot can do:*\n\n"
        "📱 *Username / UID Lookup*\n"
        "Send any @username or numeric ID\n\n"
        "📞 *Phone Number Lookup*\n"
        "Use `/num <number>`\n\n"
        "🪪 *Aadhar Lookup*\n"
        "Use `/aadhar <12 digits>`\n\n"
        "🚗 *Vehicle Lookup*\n"
        "Use `/veh <reg number>`\n\n"
        "👥 *User / Group / Channel ID*\n"
        "Use the buttons below\n\n"
        "❓ *Help Guide*\n"
        "Use /help\n\n"
        "—\n\n"
        "_Thanks for using this bot._"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_cmd(update, context):
    if not await gate(update, context):
        return
    text = (
        "🤖 *@racksunbot Help*\n\n"
        "📱 *Username / UID*\n"
        "Just send `@username` or `1234567890`\n\n"
        "📞 *Phone Number*\n"
        "`/num 9876543210`\n\n"
        "🪪 *Aadhar*\n"
        "`/aadhar 652507323571`\n\n"
        "🚗 *Vehicle*\n"
        "`/veh UP26R4007`\n\n"
        "📋 *Commands*\n"
        "/start — Start\n"
        "/num — Phone lookup\n"
        "/aadhar — Aadhar lookup\n"
        "/veh — Vehicle lookup\n"
        "/settings — Features\n"
        "/back — Main menu\n"
        "/cancel — Cancel\n"
        "/help — This help"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


def fmt_record(i, e, label_id=False):
    b = "\n*Record " + str(i) + "*\n"
    b += "*Name:* `" + str(e.get("name") or "None") + "`\n"
    b += "*Father:* `" + str(e.get("fname") or "None") + "`\n"
    b += "*Mobile:* `" + str(e.get("mobile") or "None") + "`\n"
    b += "*Alt Mobile:* `" + str(e.get("alt") or "None") + "`\n"
    if label_id:
        b += "*National ID:* `" + str(e.get("id") or "None") + "`\n"
    b += "*Email:* `" + str(e.get("email") or "None") + "`\n"
    b += "*Circle:* `" + str(e.get("circle") or "None") + "`\n"
    b += "*Address:* `" + clean_address(e.get("address")) + "`"
    return b


async def send_chunks(update, text):
    chunk = ""
    for line in text.split("\n"):
        if len(chunk) + len(line) + 1 > 3800:
            await update.message.reply_text(
                chunk, parse_mode="Markdown",
            )
            chunk = line + "\n"
        else:
            chunk += line + "\n"
    if chunk.strip():
        await update.message.reply_text(
            chunk, parse_mode="Markdown",
        )


async def num_lookup(update, context):
    if not await gate(update, context):
        return
    cid = update.message.chat_id
    if not context.args:
        await update.message.reply_text(
            "*Usage:* `/num 9876543219`",
            parse_mode="Markdown",
        )
        return
    num = context.args[0]
    num = num.replace("+", "").replace(" ", "").replace("-", "")
    s = await update.message.reply_text("🔍 Searching...")
    try:
        res = requests.get(NUM_API + num, timeout=15)
        data = res.json()
        entries = []
        if isinstance(data, dict):
            for k, v in data.items():
                if k.isdigit() and isinstance(v, dict):
                    entries.append(v)
        if not entries:
            await del_msg(context, cid, s.message_id)
            await update.message.reply_text(
                "*Data Not Found!*\n\n"
                "No info for this number.",
                parse_mode="Markdown",
            )
            return
        head = ("*Number:* `" + num + "`\n"
                "*Total Records:* `" + str(len(entries)) + "`\n")
        blocks = [head]
        for i, e in enumerate(entries, 1):
            blocks.append(fmt_record(i, e, label_id=True))
        text = "\n".join(blocks)
        await del_msg(context, cid, s.message_id)
        await send_chunks(update, text)
    except Exception as ex:
        await del_msg(context, cid, s.message_id)
        await update.message.reply_text("Error:\n" + str(ex))


async def aadhar_lookup(update, context):
    if not await gate(update, context):
        return
    cid = update.message.chat_id
    if not context.args:
        await update.message.reply_text(
            "*Usage:* `/aadhar 652507323571`",
            parse_mode="Markdown",
        )
        return
    a = context.args[0].replace(" ", "").replace("-", "")
    s = await update.message.reply_text("🔍 Searching...")
    try:
        res = requests.get(ADHAR_API + a, timeout=15)
        data = res.json()
        entries = []
        if isinstance(data, dict):
            for k, v in data.items():
                if k.isdigit() and isinstance(v, dict):
                    entries.append(v)
        if not entries:
            await del_msg(context, cid, s.message_id)
            await update.message.reply_text(
                "*Data Not Found!*\n\n"
                "No info for this Aadhar.",
                parse_mode="Markdown",
            )
            return
        head = ("*Aadhar:* `" + a + "`\n"
                "*Total Records:* `" + str(len(entries)) + "`\n")
        blocks = [head]
        for i, e in enumerate(entries, 1):
            blocks.append(fmt_record(i, e, label_id=False))
        text = "\n".join(blocks)
        await del_msg(context, cid, s.message_id)
        await send_chunks(update, text)
    except Exception as ex:
        await del_msg(context, cid, s.message_id)
        await update.message.reply_text("Error:\n" + str(ex))


async def vehicle_lookup(update, context):
    if not await gate(update, context):
        return
    cid = update.message.chat_id
    if not context.args:
        await update.message.reply_text(
            "*Usage:* `/veh UP26R4007`",
            parse_mode="Markdown",
        )
        return
    v = context.args[0].replace(" ", "").replace("-", "").upper()
    s = await update.message.reply_text("🔍 Searching...")
    try:
        res = requests.get(VEH_API + v, timeout=15)
        data = res.json()
        if not data or "Ownership Details" not in data:
            await del_msg(context, cid, s.message_id)
            await update.message.reply_text(
                "*Data Not Found!*\n\n"
                "No info for this vehicle.",
                parse_mode="Markdown",
            )
            return
        own = data.get("Ownership Details") or {}
        veh = data.get("Vehicle Details") or {}
        ins = data.get("Insurance Information") or {}
        dts = data.get("Important Dates & Validity") or {}
        oth = data.get("Other Information") or {}
        crd = data.get("Basic Card Info") or {}
        alert = data.get("Insurance Alert") or {}
        days = alert.get("Expired Days")
        ist = dts.get("Insurance Expiry In") or "N/A"
        if days and "expired" in ist.lower():
            ist = "Expired (" + str(days) + " days ago)"
        reg = data.get("registration_number") or v
        text = "🚗 *Vehicle:* `" + str(reg) + "`\n\n"
        text += "👤 *Owner Details*\n"
        text += ("*Name:* `"
                 + str(own.get("Owner Name") or "N/A") + "`\n")
        text += ("*Father:* `"
                 + str(own.get(FATHER_KEY) or "N/A") + "`\n")
        text += ("*Owner Serial:* `"
                 + str(own.get("Owner Serial No") or "N/A") + "`\n")
        text += ("*RTO:* `"
                 + str(own.get("Registered RTO") or "N/A")
                 + " (" + str(crd.get("Code") or "N/A") + ")`\n\n")
        text += "🚘 *Vehicle Info*\n"
        text += ("*Maker:* `"
                 + str(veh.get("Model Name") or "N/A") + "`\n")
        text += ("*Model:* `"
                 + str(veh.get("Maker Model") or "N/A") + "`\n")
        text += ("*Class:* `"
                 + str(veh.get("Vehicle Class") or "N/A") + "`\n")
        text += ("*Fuel:* `"
                 + str(veh.get("Fuel Type") or "N/A") + "`\n")
        text += ("*Fuel Norms:* `"
                 + str(veh.get("Fuel Norms") or "N/A") + "`\n")
        text += ("*Chassis:* `"
                 + str(veh.get("Chassis Number") or "N/A") + "`\n")
        text += ("*Engine:* `"
                 + str(veh.get("Engine Number") or "N/A") + "`\n")
        text += ("*Cubic Capacity:* `"
                 + str(oth.get("Cubic Capacity") or "N/A") + "`\n")
        text += ("*Seating:* `"
                 + str(oth.get("Seating Capacity") or "N/A") + "`\n\n")
        text += "🛡 *Insurance*\n"
        text += ("*Company:* `"
                 + str(ins.get("Insurance Company") or "N/A") + "`\n")
        text += ("*Policy No:* `"
                 + str(ins.get("Insurance No") or "N/A") + "`\n")
        text += ("*Expiry:* `"
                 + str(ins.get("Insurance Expiry") or "N/A") + "`\n")
        text += "*Status:* `" + str(ist) + "`\n\n"
        text += "📅 *Validity & Dates*\n"
        text += ("*Registration Date:* `"
                 + str(dts.get("Registration Date") or "N/A") + "`\n")
        text += ("*Vehicle Age:* `"
                 + str(dts.get("Vehicle Age") or "N/A") + "`\n")
        text += ("*Fitness Upto:* `"
                 + str(dts.get("Fitness Upto") or "N/A") + "`\n")
        text += ("*Tax Upto:* `"
                 + str(dts.get("Tax Upto") or "N/A") + "`\n")
        text += ("*PUC No:* `"
                 + str(dts.get("PUC No") or "N/A") + "`\n")
        text += ("*PUC Upto:* `"
                 + str(dts.get("PUC Upto") or "N/A") + "`\n")
        text += ("*PUC Status:* `"
                 + str(dts.get("PUC Expiry In") or "N/A") + "`\n\n")
        text += "ℹ️ *Other*\n"
        text += ("*Financer:* `"
                 + str(oth.get("Financer Name") or "N/A") + "`\n")
        text += ("*Permit Type:* `"
                 + str(oth.get("Permit Type") or "N/A") + "`\n")
        text += ("*Blacklist:* `"
                 + str(oth.get("Blacklist Status") or "N/A") + "`\n")
        text += ("*NOC:* `"
                 + str(oth.get("NOC Details") or "N/A") + "`\n\n")
        text += "🏢 *RTO Office*\n"
        text += ("*City:* `"
                 + str(crd.get("City Name") or "N/A") + "`\n")
        text += ("*Address:* `"
                 + str(crd.get("Address") or "N/A") + "`")
        await del_msg(context, cid, s.message_id)
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as ex:
        await del_msg(context, cid, s.message_id)
        await update.message.reply_text("Error:\n" + str(ex))


async def on_users_shared(update, context):
    if not await gate(update, context):
        return
    if update.message.users_shared:
        for u in update.message.users_shared.users:
            await update.message.reply_text(
                "*User ID:* `" + str(u.user_id) + "`",
                parse_mode="Markdown",
            )


async def on_chat_shared(update, context):
    if not await gate(update, context):
        return
    if update.message.chat_shared:
        cid = update.message.chat_shared.chat_id
        await update.message.reply_text(
            "*Chat ID:* `" + str(cid) + "`",
            parse_mode="Markdown",
        )


async def lookup(update, context):
    if not await gate(update, context):
        return
    cid = update.message.chat_id
    inp = update.message.text.strip()
    is_user = inp.startswith("@") and len(inp) > 1
    digits = inp.lstrip("+")
    is_num = digits.isdigit() and len(digits) >= 7
    if not is_user and not is_num:
        return
    s = await update.message.reply_text("🔍 Searching...")
    try:
        res = requests.get(BASE_URL + inp, timeout=10)
        data = res.json()
        result = data.get("result", data) if isinstance(data, dict) else data
        not_found = False
        text = ""
        if isinstance(result, dict):
            if not result.get("success", True):
                not_found = True
            else:
                fields = {
                    k: v for k, v in result.items()
                    if k not in ("success", "msg")
                }
                if not fields:
                    not_found = True
                else:
                    lines = ["*Result:*\n"]
                    for k, val in fields.items():
                        lbl = k.replace("_", " ").title()
                        lines.append(
                            "*" + lbl + ":* `" + str(val) + "`"
                        )
                    text = "\n".join(lines)
        elif not result:
            not_found = True
        else:
            text = "*Result:*\n`" + str(result) + "`"
        if not_found:
            text = ("*Data Not Found!*\n\n"
                    "No info for this username.")
        await del_msg(context, cid, s.message_id)
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as ex:
        await del_msg(context, cid, s.message_id)
        await update.message.reply_text("Error:\n" + str(ex))


if __name__ == "__main__":
    keep_alive()
    print("Flask Server Started!")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("num", num_lookup))
    app.add_handler(CommandHandler("aadhar", aadhar_lookup))
    app.add_handler(CommandHandler("veh", vehicle_lookup))
    app.add_handler(CommandHandler("vehicle", vehicle_lookup))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("back", back_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(CallbackQueryHandler(
        check_joined_cb, pattern="check_joined",
    ))
    app.add_handler(MessageHandler(
        filters.StatusUpdate.USERS_SHARED, on_users_shared,
    ))
    app.add_handler(MessageHandler(
        filters.StatusUpdate.CHAT_SHARED, on_chat_shared,
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, lookup,
    ))
    print("Bot is Online!")
    app.run_polling()
