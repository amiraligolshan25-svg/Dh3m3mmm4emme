from datetime import datetime, timedelta, timezone

from telegram import Update, ChatPermissions
from telegram.ext import CommandHandler, ContextTypes


# =========================
#       PARSE TIME
# =========================

def parse_time(value: str):

    if len(value) < 2:
        return None

    try:
        number = int(value[:-1])
    except ValueError:
        return None

    unit = value[-1].lower()

    units = {
        "s": timedelta(seconds=number),
        "m": timedelta(minutes=number),
        "h": timedelta(hours=number),
        "d": timedelta(days=number),
    }

    return units.get(unit)


# =========================
#       GET TARGET
# =========================

async def get_target(update, context):

    message = update.effective_message

    # Reply
    if message.reply_to_message:
        return message.reply_to_message.from_user

    # ID
    if context.args:

        target = context.args[0]

        if target.isdigit():

            try:
                member = await update.effective_chat.get_member(
                    int(target)
                )

                return member.user

            except Exception:
                return None

    return None


# =========================
#          MUTE
# =========================

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message
    chat = update.effective_chat

    # -------------------------
    # Admin check
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
    # Target
    # -------------------------

    target = await get_target(
        update,
        context
    )

    if target is None:

        await message.reply_text(
            "❌ کاربر پیدا نشد.\n\n"
            "استفاده:\n"
            "• Reply → /mute\n"
            "• /mute 123456789"
        )

        return

    # -------------------------
    # Duration
    # -------------------------

    duration = None

    # Reply → /mute 10m
    if message.reply_to_message:

        if context.args:
            duration = parse_time(
                context.args[0]
            )

    # /mute 123456789 10m
    else:

        if len(context.args) >= 2:
            duration = parse_time(
                context.args[1]
            )

    if duration is None:

        await message.reply_text(
            "❌ مدت زمان را وارد کن.\n\n"
            "مثال:\n"
            "/mute 10m\n"
            "/mute 2h\n"
            "/mute 1d\n\n"
            "یا با ID:\n"
            "/mute 123456789 10m"
        )

        return

    # -------------------------
    # Don't mute admin
    # -------------------------

    target_member = await chat.get_member(
        target.id
    )

    if target_member.status in (
        "administrator",
        "creator"
    ):

        await message.reply_text(
            "❌ نمی‌توانی یک ادمین را میوت کنی."
        )

        return

    # -------------------------
    # Calculate time
    # -------------------------

    until_date = datetime.now(
        timezone.utc
    ) + duration

    # -------------------------
    # Permissions
    # -------------------------

    permissions = ChatPermissions(
        can_send_messages=False
    )

    # -------------------------
    # MUTE
    # -------------------------

    try:

        await chat.restrict_member(
            user_id=target.id,
            permissions=permissions,
            until_date=until_date
        )

        await message.reply_text(
            f"🔇 {target.full_name} میوت شد.\n"
            f"⏱ مدت: {format_duration(duration)}"
        )

    except Exception as e:

        await message.reply_text(
            f"❌ خطا در میوت:\n{e}"
        )


# =========================
#        UNMUTE
# =========================
async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message
    chat = update.effective_chat

    # -------------------------
    # Admin check
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
    # Target
    # -------------------------

    target = await get_target(
        update,
        context
    )

    if target is None:

        await message.reply_text(
            "❌ کاربر پیدا نشد.\n\n"
            "استفاده:\n"
            "• Reply → /unmute\n"
            "• /unmute 123456789"
        )

        return

    # -------------------------
    # Restore permissions
    # -------------------------

    permissions = ChatPermissions(
        can_send_messages=True,
        can_send_audios=True,
        can_send_documents=True,
        can_send_photos=True,
        can_send_videos=True,
        can_send_video_notes=True,
        can_send_voice_notes=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_change_info=False,
        can_invite_users=True,
        can_pin_messages=False,
        can_manage_topics=False
    )

    # -------------------------
    # UNMUTE
    # -------------------------

    try:

        await chat.restrict_member(
            user_id=target.id,
            permissions=permissions
        )

        await message.reply_text(
            f"🔊 {target.full_name} آن‌میوت شد."
        )

    except Exception as e:

        await message.reply_text(
            f"❌ خطا در آن‌میوت:\n{e}"
        )


# =========================
#     FORMAT DURATION
# =========================

def format_duration(duration):

    seconds = int(
        duration.total_seconds()
    )

    if seconds < 60:
        return f"{seconds} ثانیه"

    minutes = seconds // 60

    if minutes < 60:
        return f"{minutes} دقیقه"

    hours = minutes // 60

    if hours < 24:
        return f"{hours} ساعت"

    days = hours // 24

    return f"{days} روز"


# =========================
#        REGISTER
# =========================

def register(application):

    application.add_handler(
        CommandHandler(
            "mute",
            mute
        )
    )

    application.add_handler(
        CommandHandler(
            "unmute",
            unmute
        )
    )