from telegram import Update
from telegram.ext import CommandHandler, ContextTypes


# =========================
#      ADMIN CHECK
# =========================

async def is_admin(update: Update) -> bool:

    chat = update.effective_chat
    user = update.effective_user

    if not chat or not user:
        return False

    member = await chat.get_member(user.id)

    return member.status in (
        "administrator",
        "creator"
    )


# =========================
#        CLEAR
# =========================

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message
    chat = update.effective_chat

    # -------------------------
    # Admin
    # -------------------------

    if not await is_admin(update):

        await message.reply_text(
            "❌ فقط ادمین‌ها می‌توانند از این دستور استفاده کنند."
        )

        return

    # -------------------------
    # Reply
    # -------------------------

    if message.reply_to_message:

        try:

            await message.reply_to_message.delete()
            await message.delete()

        except Exception:

            await message.reply_text(
                "❌ نتونستم پیام رو حذف کنم."
            )

        return

    # -------------------------
    # Number
    # -------------------------

    if context.args:

        try:
            amount = int(context.args[0])

        except ValueError:

            await message.reply_text(
                "❌ تعداد پیام نامعتبر است."
            )

            return

        # محدودیت برای جلوگیری از اشتباه
        if amount < 1 or amount > 100:

            await message.reply_text(
                "❌ تعداد باید بین 1 تا 100 باشد."
            )

            return

        deleted = 0

        # Telegram اجازه حذف پیام با ID ناموجود را نمی‌دهد.
        # از پیام فعلی به عقب حرکت می‌کنیم.

        for message_id in range(
            message.message_id - amount,
            message.message_id + 1
        ):

            if message_id <= 0:
                continue

            try:

                await context.bot.delete_message(
                    chat_id=chat.id,
                    message_id=message_id
                )

                deleted += 1

            except Exception:
                pass

        return

    # -------------------------
    # Usage
    # -------------------------

    await message.reply_text(
        "🧹 روش استفاده:\n\n"
        "• روی پیام ریپلای کن و /clear بزن\n"
        "• /clear 10"
    )


# =========================
#        REGISTER
# =========================

def register(application):

    application.add_handler(
        CommandHandler(
            "clear",
            clear
        )
    )