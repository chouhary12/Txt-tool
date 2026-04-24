import re
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")

# 🔹 MENU
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("TXT → HTML", callback_data="txt2html"),
         InlineKeyboardButton("HTML → TXT", callback_data="html2txt")],
        [InlineKeyboardButton("Extract Links", callback_data="extract"),
         InlineKeyboardButton("Compare Links", callback_data="compare")],
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
        await query.message.reply_text("Send OLD text")

    else:
        await query.message.reply_text("Send input")

# 🔹 TEXT HANDLER
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    text = update.message.text

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
            await update.message.reply_text("Send NEW text")

    elif mode == "totxt":
        await send_file(update, text.splitlines())

    elif mode == "split":
        links = extract_links(text)
        parts = split_links(links, 50)
        for part in parts:
            await send_file(update, part)

# 🔹 APP INIT
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# 🔹 RUN
app.run_polling()