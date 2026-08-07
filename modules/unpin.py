from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

async def unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    if not message.reply_to_message:
        await message.reply_text("روی یک پیام ریپلی کن!")
        return
    member = await chat.get_member(update.effective_user.id)
    if member.status not in ("administrator","creator"):
        await message.reply_text("این دستور فقط برای ادمین هاست")
        return
    try:
        await message.reply_to_message.unpin()
        await message.delete()
    except Exception:
        await message.reply_text("آن پین با مشکل مواجه شد")
        
def register(application):
    application.add_handler(CommandHandler("unpin", unpin))