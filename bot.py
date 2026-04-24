import re
import os
from flask import Flask, request
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app_web = Flask(__name__)

# 🔹 MENU
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("TXT → HTML", callback_data="txt2html"),
         InlineKeyboardButton("HTML → TXT", callback_data="html2txt")],
        [InlineKeyboardButton("Extract Links", callback_data="extract"),
         InlineKeyboardButton("Compare Links", callback_data="compare")],
        [InlineKeyboardButton("Domain Changer", callback_data="domain"),
         InlineKeyboardButton("Merge TXT", callback_data="merge")],
        [InlineKeyboardButton("Split Links", callback_data="split"),
         InlineKeyboardButton("Text → TXT", callback_data="totxt")]
    ])

# 🔹 UTILS
def extract_links(text):
    return re.findall(r'https?://\S+', text)

def split_links(links, size=50):
    return [links[i:i+size] for i in range(0, len(links), size)]

async def send_file(update, lines, filename="output.txt"):
    with open(filename, "w") as f:
        f.write("\n".join(lines))
    await update.message.reply_document(InputFile(filename))
    os.remove(filename)

async def send_multiple_files(update, parts):
    for part in parts:
        await send_file(update, part)

# 🔹 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚡ Choose Tool:", reply_markup=main_menu())

# 🔹 BUTTON
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data.clear()
    context.user_data["mode"] = query.data

    if query.data == "compare":
        context.user_data["data"] = []
        await query.message.reply_text("Send OLD text/file")

    elif query.data == "domain":
        await query.message.reply_text("Send links text/file")

    elif query.data == "merge":
        context.user_data["files"] = []
        await query.message.reply_text("Send multiple TXT files")

    else:
        await query.message.reply_text("Send input")

# 🔹 TEXT HANDLER
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    text = update.message.text

    # DOMAIN FLOW
    if mode == "domain":
        if context.user_data.get("step") == "old":
            context.user_data["old"] = text
            context.user_data["step"] = "new"
            await update.message.reply_text("Send NEW domain")
            return
        elif context.user_data.get("step") == "new":
            new_domain = text
            old = context.user_data["old"]
            links = context.user_data["links"]
            changed = [link.replace(old, new_domain) for link in links]
            await send_file(update, changed)
            context.user_data.clear()
            return

    # FEATURES
    if mode == "txt2html":
        await update.message.reply_text(f"<html><body>{text}</body></html>")

    elif mode == "html2txt":
        clean = re.sub('<.*?>', '', text)
        await update.message.reply_text(clean)

    elif mode == "extract":
        links = extract_links(text)
        await send_file(update, links)

    elif mode == "compare":
        context.user_data.setdefault("data", []).append(text)

        if len(context.user_data["data"]) == 2:
            old, new = context.user_data["data"]

            old_links = set(extract_links(old))
            new_links = set(extract_links(new))

            added = list(new_links - old_links)
            removed = list(old_links - new_links)

            result = ["🆕 New Links:"] + added + ["", "❌ Removed Links:"] + removed
            await send_file(update, result)

            context.user_data.clear()
        else:
            await update.message.reply_text("Send NEW text/file")

    elif mode == "totxt":
        await send_file(update, text.splitlines())

    elif mode == "split":
        links = extract_links(text)
        parts = split_links(links, 50)
        await send_multiple_files(update, parts)

# 🔹 FILE HANDLER
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    content = await file.download_as_bytearray()
    text = content.decode("utf-8", errors="ignore")

    mode = context.user_data.get("mode")

    if mode == "merge":
        context.user_data["files"].append(text)
        if len(context.user_data["files"]) >= 2:
            merged = "\n".join(context.user_data["files"])
            await send_file(update, merged.splitlines())

    elif mode == "compare":
        context.user_data["data"].append(text)
        if len(context.user_data["data"]) == 2:
            old, new = context.user_data["data"]

            old_links = set(extract_links(old))
            new_links = set(extract_links(new))

            added = list(new_links - old_links)
            removed = list(old_links - new_links)

            result = ["🆕 New Links:"] + added + ["", "❌ Removed Links:"] + removed
            await send_file(update, result)
            context.user_data.clear()

    elif mode == "extract":
        await send_file(update, extract_links(text))

    elif mode == "split":
        parts = split_links(extract_links(text), 50)
        await send_multiple_files(update, parts)

    elif mode == "domain":
        context.user_data["links"] = extract_links(text)
        context.user_data["step"] = "old"
        await update.message.reply_text("Send OLD domain")

# 🔹 FLASK WEBHOOK
@app_web.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok"

@app_web.route("/")
def home():
    return "Bot Running 🚀"

# 🔹 APP INIT
application = ApplicationBuilder().token(TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
application.add_handler(MessageHandler(filters.Document.ALL, handle_file))

# 🔹 RUN
if __name__ == "__main__":
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
      )
