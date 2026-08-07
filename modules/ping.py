import time

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start = time.perf_counter
    message = await update.effective_message.reply_text(
        "Pinging..."
    )
    end = time.perf_counter()

    ping = round((end - start) * 100)

    await message.edit_text(f"Pong!\n {ping} ms")

def register(application):
    application.add_handler(CommandHandler("ping", ping))