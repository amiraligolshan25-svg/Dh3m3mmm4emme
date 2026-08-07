from telegram import Update, ChatAdministratorRights
from telegram.ext import CommandHandler, ContextTypes, Application, MessageHandler, filters
from dotenv import load_dotenv
import os


load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effectice_message
    await message.reply_text("test")
async def promote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    if not message.reply_to_message:
        await message.reply_text("روی پیام یه نفر ریپلی کن")
        return
    admin = await chat.get_member(update.effective_user.id)

    if admin.status != "creator":
        await message.reply_text(
            "فقط مالک گروه میتونه"
        )
        return
    target = message.reply_to_message.from_user

    try:
        await chat.promote_member(
            target.id,
            can_manage_chat=False,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False,
            can_manage_topics=False
        )
        await message.reply_text(
            f"کاربر {target.full_name} ادمین شد"
        )
    except Exception as e:
        await message.reply_text(f"خطا در ادمین کردن: {e}")
        
async def demote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    if not message.reply_to_message:
        await message.reply_text("روی پیام یه نفر ریپلی کن")
        return
    admin = await chat.get_member(update.effective_user.id)

    if admin.status != "creator":
        await message.reply_text(
            "فقط مالک گروه میتونه"
        )
        return
    target = message.reply_to_message.from_user

    try:
        await chat.promote_member(
            target.id,
            can_manage_chat=False,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_manage_topics=False
        )
        await message.reply_text(
            f"کاربر {target.full_name} از ادمینی در آمد"
        )
    except Exception as e:
        await message.reply_text(f"خطا در ادمین کردن: {e}")

def main():
    application = (Application.builder().token(TOKEN).build())
    application.add_handler(MessageHandler(filters.Regex(r'افزودن ادمین'), promote_cmd))
    application.add_handler(MessageHandler(filters.Regex(r'^حذف ادمین\s+\d+$'), demote_cmd))
    print("bot started")
