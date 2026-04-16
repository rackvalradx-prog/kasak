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
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")

BASE_URL = "https://api.subhxcosmo.in/api?key=RACKSUN&type=tg&term="

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    btn_user = KeyboardButton(text="User", request_users=KeyboardButtonRequestUsers(request_id=1, max_quantity=1))
    btn_group = KeyboardButton(text="Group", request_chat=KeyboardButtonRequestChat(request_id=2, chat_is_channel=False))
    btn_channel = KeyboardButton(text="Channel", request_chat=KeyboardButtonRequestChat(request_id=3, chat_is_channel=True))
    markup = ReplyKeyboardMarkup([[btn_user, btn_group, btn_channel]], resize_keyboard=True)
    welcome_msg = (
        "*Welcome To @racksunbot*\n\n"
        f"*Your ID :* `{update.message.from_user.id}`\n\n"
        "Send me a Telegram username or number to look up.\n"
        "Example: @username or 1234567890\n\n"
        "Or use the buttons below to get User/Group/Channel ID:"
    )
    await update.message.reply_text(welcome_msg, reply_markup=markup, parse_mode="Markdown")

async def handle_users_shared(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.users_shared:
        for user in update.message.users_shared.users:
            await update.message.reply_text(f"*User ID:* `{user.user_id}`", parse_mode="Markdown")

async def handle_chat_shared(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_shared:
        await update.message.reply_text(f"*Chat ID:* `{update.message.chat_shared.chat_id}`", parse_mode="Markdown")

async def lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    await update.message.reply_text("Searching...")
    try:
        url = BASE_URL + user_input
        res = requests.get(url, timeout=10)
        data = res.json()

        if "result" in data:
            result = data["result"]
        else:
            result = data

        not_found = False
        if isinstance(result, dict):
            if not result.get("success", True):
                not_found = True
            else:
                fields = {k: v for k, v in result.items() if k not in ("success", "msg")}
                if not fields:
                    not_found = True
                else:
                    lines = ["*Result:*\n"]
                    for key, value in fields.items():
                        label = key.replace("_", " ").title()
                        lines.append(f"*{label}:* `{value}`")
                    text = "\n".join(lines)
        elif not result:
            not_found = True
        else:
            text = f"*Result:*\n`{result}`"

        if not_found:
            text = "*Data Not Found!*\n\nNo information found for this number/username."

        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"Error:\n{str(e)}")

if __name__ == "__main__":
    keep_alive()
    print("Flask Server Started!")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.USERS_SHARED, handle_users_shared))
    app.add_handler(MessageHandler(filters.StatusUpdate.CHAT_SHARED, handle_chat_shared))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lookup))
    print("Bot is Online!")
    app.run_polling()
