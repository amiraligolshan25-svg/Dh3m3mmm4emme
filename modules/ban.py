from telegram import Update
from telegram.ext import CommandHandler, ContextTypes


# =========================
#       GET TARGET
# =========================

async def get_target(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message

    # -------------------------
    # Reply
    # -------------------------

    if message.reply_to_message:
        return message.reply_to_message.from_user

    # -------------------------
    # ID / Username
    # -------------------------

    if context.args:

        target = context.args[0]

        # User ID
        if target.isdigit():

            try:
                user_id = int(target)

                chat_member = await update.effective_chat.get_member(
                    user_id
                )

                return chat_member.user

            except Exception:
                return None

        # Username
        if target.startswith("@"):

            username = target[1:]

            try:
                members = await update.effective_chat.get_member(
                    username
                )

                return members.user

            except Exception:
                return None

    return None


# =========================
#           BAN
# =========================

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message
    chat = update.effective_chat

    # -------------------------
    # Check Admin
    # -------------------------

    if update.effective_user is None:
        return

    admin = await chat.get_member(
        update.effective_user.id
    )

    if admin.status not in ("administrator", "creator"):

        await message.reply_text(
            "❌ فقط ادمین‌ها می‌توانند از این دستور استفاده کنند."
        )

        return

    # -------------------------
    # Get Target
    # -------------------------

    target = await get_target(
        update,
        context
    )

    if target is None:

        await message.reply_text(
            "❌ کاربر پیدا نشد.\n\n"
            "روش استفاده:\n"
            "• Reply → /ban\n"
            "• /ban @username\n"
            "• /ban user_id"
        )

        return

    # -------------------------
    # Don't Ban Yourself
    # -------------------------

    if target.id == update.effective_user.id:

        await message.reply_text(
            "❌ نمی‌تونی خودت رو بن کنی."
        )

        return

    # -------------------------
    # Don't Ban Bot
    # -------------------------

    if target.id == context.bot.id:

        await message.reply_text(
            "❌ نمی‌تونی خود ربات رو بن کنی."
        )

        return

    # -------------------------
    # Check Target Permissions
    # -------------------------

    target_member = await chat.get_member(
        target.id
    )

    if target_member.status in (
        "administrator",
        "creator"
    ):

        await message.reply_text(
            "❌ نمی‌تونی یک ادمین رو بن کنی."
        )

        return

    # -------------------------
    # BAN
    # -------------------------

    try:

        await chat.ban_member(
            target.id
        )

        await message.reply_text(
            f"🔨 کاربر {target.full_name} بن شد."
        )

    except Exception as e:

        await message.reply_text(
            f"❌ خطا در بن کردن کاربر:\n{e}"
        )


# =========================
#         UNBAN
# =========================

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message
    chat = update.effective_chat

    # -------------------------
    # Check Admin
    # -------------------------

    admin = await chat.get_member(
        update.effective_user.id
    )

    if admin.status not in ("administrator", "creator"):

        await message.reply_text(
            "❌ فقط ادمین‌ها می‌توانند از این دستور استفاده کنند."
        )

        return

    # -------------------------
    # Get ID
    # -------------------------

    if not context.args:
        await message.reply_text(
            "❌ آیدی کاربر را وارد کن.\n\n"
            "مثال:\n"
            "/unban 123456789"
        )

        return

    try:

        user_id = int(context.args[0])

    except ValueError:

        await message.reply_text(
            "❌ User ID نامعتبر است."
        )

        return

    # -------------------------
    # UNBAN
    # -------------------------

    try:

        await chat.unban_member(
            user_id,
            only_if_banned=True
        )

        await message.reply_text(
            "✅ کاربر آن‌بن شد."
        )

    except Exception as e:

        await message.reply_text(
            f"❌ خطا در آن‌بن:\n{e}"
        )


# =========================
#        REGISTER
# =========================

def register(application):

    application.add_handler(
        CommandHandler(
            "ban",
            ban
        )
    )

    application.add_handler(
        CommandHandler(
            "unban",
            unban
        )
    )