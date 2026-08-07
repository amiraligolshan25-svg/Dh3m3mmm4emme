from telegram import Update, ChatAdministratorRights
from telegram.ext import CommandHandler, ContextTypes

async def demote(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
def register(application):
    application.add_handler(CommandHandler("demote", demote))