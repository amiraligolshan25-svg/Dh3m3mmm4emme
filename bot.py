import asyncio
import os
import random
from datetime import datetime, timedelta
from telegram import Update, ChatMember, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ==================== بارگذاری متغیرهای محیطی ====================

from dotenv import load_dotenv

# بارگذاری فایل .env
load_dotenv()

# دریافت توکن از محیط
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ توکن ربات پیدا نشد! لطفاً فایل .env رو بررسی کن یا متغیر محیطی BOT_TOKEN رو تنظیم کن.")

# ==================== توابع کمکی ====================

# بررسی ادمین بودن
async def is_admin(update: Update, user_id: int) -> bool:
    try:
        chat_member = await update.effective_chat.get_member(user_id)
        return chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except:
        return False

# تبدیل زمان به ثانیه
def parse_time(time_str):
    time_str = time_str.lower()
    if time_str.endswith('s'):
        return int(time_str[:-1])
    elif time_str.endswith('m'):
        return int(time_str[:-1]) * 60
    elif time_str.endswith('h'):
        return int(time_str[:-1]) * 3600
    elif time_str.endswith('d'):
        return int(time_str[:-1]) * 86400
    else:
        return int(time_str)

# فرمت زمان به شکل خوانا
def format_time(seconds):
    if seconds < 60:
        return f"{seconds} ثانیه"
    elif seconds < 3600:
        return f"{seconds // 60} دقیقه"
    elif seconds < 86400:
        return f"{seconds // 3600} ساعت"
    else:
        return f"{seconds // 86400} روز"

# گرفتن اطلاعات کاربر
async def get_user_info(bot, user_id):
    try:
        user = await bot.get_chat(user_id)
        name = user.full_name or user.username or str(user_id)
        username = f"@{user.username}" if user.username else str(user_id)
        return name, username
    except:
        return str(user_id), str(user_id)

# ==================== پیام خوش‌آمدگویی ====================

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for new_member in update.message.new_chat_members:
        if new_member.id == context.bot.id:
            await update.message.reply_text(
                "🤖 سلام! من ربات مدیریت گروه هستم.\n"
                "برای مشاهده دستورات /start رو بزن."
            )
            return
        
        name = new_member.full_name or new_member.username or str(new_member.id)
        username = f"@{new_member.username}" if new_member.username else ""
        
        welcome_text = (
            f"🎉 **به گروه خوش اومدی!**\n\n"
            f"👤 {name} {username}\n\n"
            f"📌 لطفاً قوانین گروه رو مطالعه کن.\n"
            f"🤝 از حضورت خوشحالیم!"
        )
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')

# ==================== دستور /start ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🎮 بازی‌ها", callback_data="games"),
            InlineKeyboardButton("🕐 زمان", callback_data="time")
        ],
        [
            InlineKeyboardButton("📌 مدیریت", callback_data="management"),
            InlineKeyboardButton("ℹ️ راهنما", callback_data="help")
        ],
            InlineKeyboarfButton("درباره ی ربات", callback_data="about")
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 **ربات مدیریت و سرگرمی گروه**\n\n"
        "با من می‌تونی گروه رو مدیریت کنی و بازی کنی!\n"
        "از دکمه‌های زیر استفاده کن:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# ==================== دکمه‌های /start ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "games":
        text = (
            "🎮 **بازی‌های موجود:**\n\n"
            "🎲 `/dice` - تاس بینداز (۱ تا ۶)\n"
            "⚽ `/football` - ضربه پنالتی (گل یا نه)\n"
            "🏀 `/basket` - پرتاب بسکتبال (گل یا نه)\n"
            "🎰 `/lottery` - قرعه‌کشی (شانس ۱ تا ۱۰۰)\n"
            "🔢 `/random_number` - عدد تصادفی ۱ تا ۱۰۰\n"
            "🪙 `/coin` - شیر یا خط\n"
            "🎮 `/games` - نمایش همین منو"
        )
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == "time":
        now = datetime.now()
        persian_weekdays = {0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه", 3: "پنج‌شنبه", 4: "جمعه", 5: "شنبه", 6: "یک‌شنبه"}
        weekday = persian_weekdays[now.weekday()]
        
        text = (
            f"🕐 **تاریخ و زمان فعلی:**\n\n"
            f"📅 تاریخ: {now.year}/{now.month:02d}/{now.day:02d}\n"
            f"📆 روز هفته: {weekday}\n"
            f"⏰ زمان: {now.hour:02d}:{now.minute:02d}:{now.second:02d}\n"
            f"🔢 هفته: {now.isocalendar()[1]}\n"
            f"📊 روز سال: {now.timetuple().tm_yday}"
        )
        await query.edit_message_text(text, parse_mode='Markdown')
    elif query.data == "about":
        text = ("this robot is created by @Real_NoName"
        )
        await query.edit_message_text(text, parse_mode='Markdown')
    elif query.data == "management":
        text = (
            "📌 **دستورات مدیریتی (فقط ادمین‌ها):**\n\n"
            "🚫 `/ban @user [دلیل]` - بن کردن\n"
            "✅ `/unban @user` - آن‌بن کردن\n"
            "👢 `/kick @user [دلیل]` - کیک کردن\n"
            "🔇 `/mute @user 5m` - میوت کردن\n"
            "🔊 `/unmute @user` - آن‌میوت کردن\n"
            "📌 `/pin` - پین کردن (ریپلی)\n"
            "📌 `/unpin` - آنپین کردن (ریپلی)\n\n"
            "⏱️ زمان‌ها: 30s, 5m, 2h, 1d"
        )
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == "help":
        text = (
            "ℹ️ **راهنمای ربات**\n\n"
            "🎮 **بازی‌ها:**\n"
            "• `/dice` - تاس\n"
            "• `/football` - پنالتی\n"
            "• `/basket` - بسکتبال\n"
            "• `/lottery` - قرعه‌کشی\n"
            "• `/random_number` - عدد تصادفی\n"
            "• `/coin` - شیر یا خط\n"
            "• `/games` - منوی بازی‌ها\n\n"
            "🕐 **ابزارها:**\n"
            "• `/time` - تاریخ و زمان\n\n"
            "📌 **مدیریت (فقط ادمین‌ها):**\n"
            "• `/ban`, `/unban`, `/kick`\n"
            "• `/mute`, `/unmute`\n"
            "• `/pin`, `/unpin`\n\n"
            "😂 **سرگرمی:**\n"
            "• `/kickme` - خودت رو کیک کن!"
        )
        await query.edit_message_text(text, parse_mode='Markdown')

# ==================== بازی‌ها ====================

# 1. دستور /games
async def games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎮 **بازی‌های موجود:**\n\n"
        "🎲 `/dice` - تاس بینداز (۱ تا ۶)\n"
        "⚽ `/football` - ضربه پنالتی (گل یا نه)\n"
        "🏀 `/basket` - پرتاب بسکتبال (گل یا نه)\n"
        "🎰 `/lottery` - قرعه‌کشی (شانس ۱ تا ۱۰۰)\n"
        "🔢 `/random_number` - عدد تصادفی ۱ تا ۱۰۰\n"
        "🪙 `/coin` - شیر یا خط\n"
        "🎮 `/games` - نمایش همین منو"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

# 2. دستور /dice
async def roll_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dice = random.randint(1, 6)
    emojis = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
    
    text = (
        f"🎲 **تاس انداختی!**\n\n"
        f"{emojis[dice]} عدد **{dice}** آمد!\n"
    )
    
    if dice == 6:
        text += "\n🎉 **تبریک! شش آوردی!**"
    elif dice == 1:
        text += "\n😅 **ای وای! یک آوردی!**"
    
    await update.message.reply_text(text, parse_mode='Markdown')

# 3. دستور /football
async def football(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = random.choice(["گل 🥅⚽", "گل نشد ❌", "به تیر خورد 🥅💥", "گلر گرفت 🧤"])
    power = random.randint(1, 100)
    
    text = (
        f"⚽ **ضربه پنالتی!**\n\n"
        f"💪 قدرت ضربه: {power}%\n"
        f"📊 نتیجه: {result}\n"
    )
    
    if "گل" in result:
        text += "\n🎉 **گل! هورااا!**"
    else:
        text += "\n😅 **دفعه بعد حتماً!**"
    
    await update.message.reply_text(text, parse_mode='Markdown')

# 4. دستور /basket
async def basketball(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = random.choice(["گل 🏀✅", "گل نشد ❌", "به حلقه خورد 🥅💥", "دفاع کرد 🛡️"])
    accuracy = random.randint(1, 100)
    
    text = (
        f"🏀 **پرتاب بسکتبال!**\n\n"
        f"🎯 دقت پرتاب: {accuracy}%\n"
        f"📊 نتیجه: {result}\n"
    )
    
    if "گل" in result:
        text += "\n🎉 **گل! عالی بود!**"
    else:
        text += "\n😅 **دفعه بعد دقیق‌تر!**"
    
    await update.message.reply_text(text, parse_mode='Markdown')

# 5. دستور /lottery
async def lottery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.full_name or update.effective_user.username or "کاربر"
    chance = random.randint(1, 100)
    lucky_number = random.randint(1, 100)
    
    text = (
        f"🎰 **قرعه‌کشی!**\n\n"
        f"👤 {user_name}\n"
        f"🔢 عدد شانس شما: **{chance}**\n"
        f"🎯 عدد برنده: **{lucky_number}**\n\n"
    )
    
    if chance >= 80:
        text += "🎉 **تبریک! شما برنده جایزه بزرگ شدی!** 🎁"
    elif chance >= 50:
        text += "😊 **نزدیک بود! بازم امتحان کن!**"
    elif chance >= 20:
        text += "😐 **شانس نیاوردی! دفعه بعد!**"
    else:
        text += "😅 **امروز روز شانس تو نیست!**"
    
    await update.message.reply_text(text, parse_mode='Markdown')

# 6. دستور /random_number
async def random_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number = random.randint(1, 100)
    
    text = (
        f"🔢 **عدد تصادفی:**\n\n"
        f"🎯 عدد شما: **{number}**\n"
    )
    
    if number <= 10:
        text += "\n😅 **عدد خیلی کوچیک!**"
    elif number <= 30:
        text += "\n😊 **عدد متوسط!**"
    elif number <= 70:
        text += "\n👍 **عدد خوبی بود!**"
    else:
        text += "\n🎉 **عدد بزرگی! عالی!**"
    
    await update.message.reply_text(text, parse_mode='Markdown')

# 7. دستور /coin
async def coin_flip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = random.choice(["شیر 🦁", "خط 🪙"])
    
    text = (
        f"🪙 **شیر یا خط!**\n\n"
        f"📊 نتیجه: **{result}**\n"
    )
    
    if result == "شیر 🦁":
        text += "\n🦁 **شیر!**"
    else:
        text += "\n🪙 **خط!**"
    
    await update.message.reply_text(text, parse_mode='Markdown')

# ==================== دستور /time ====================

async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    persian_weekdays = {0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه", 3: "پنج‌شنبه", 4: "جمعه", 5: "شنبه", 6: "یک‌شنبه"}
    weekday = persian_weekdays[now.weekday()]
    
    text = (
        f"🕐 **تاریخ و زمان فعلی:**\n\n"
        f"📅 تاریخ: {now.year}/{now.month:02d}/{now.day:02d}\n"
        f"📆 روز هفته: {weekday}\n"
        f"⏰ زمان: {now.hour:02d}:{now.minute:02d}:{now.second:02d}\n"
        f"🔢 هفته: {now.isocalendar()[1]}\n"
        f"📊 روز سال: {now.timetuple().tm_yday}"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

# ==================== دستورات مدیریتی ====================

# /ban
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not await is_admin(update, user_id):
        await update.message.reply_text("⛔ فقط ادمین‌ها می‌تونن از این دستور استفاده کنن!")
        return
    
    target_user_id = None
    reason = ""
    
    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
        if context.args:
            reason = " " + " ".join(context.args)
    elif context.args:
        target = context.args[0]
        if target.startswith("@"):
            try:
                user = await context.bot.get_chat(target)
                target_user_id = user.id
            except:
                await update.message.reply_text("❌ کاربر با این یوزرنیم پیدا نشد!")
                return
        elif target.isdigit():
            target_user_id = int(target)
        else:
            await update.message.reply_text("❌ یوزرنیم یا آیدی نامعتبر!")
            return
        if len(context.args) > 1:
            reason = " " + " ".join(context.args[1:])
    else:
        await update.message.reply_text("❌ نحوه استفاده:\n1. ریپلی: /ban\n2. با یوزرنیم: /ban @username\n3. با آیدی: /ban 123456789")
        return
    
    if target_user_id == context.bot.id:
        await update.message.reply_text("❌ نمی‌تونم خودم رو بن کنم! 😄")
        return
    
    if await is_admin(update, target_user_id):
        await update.message.reply_text("❌ نمی‌تونم ادمین رو بن کنم!")
        return
    
    try:
        name, username = await get_user_info(context.bot, target_user_id)
        admin_name, _ = await get_user_info(context.bot, user_id)
        await context.bot.ban_chat_member(chat_id, target_user_id)
        await update.message.reply_text(f"🚫 کاربر {name} ({username}) توسط {admin_name} بن شد!{reason}")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا:\n{str(e)}")

# /unban
async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not await is_admin(update, user_id):
        await update.message.reply_text("⛔ فقط ادمین‌ها می‌تونن از این دستور استفاده کنن!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ لطفاً یوزرنیم یا آیدی رو وارد کن:\n/unban @username")
        return
    
    target = context.args[0]
    try:
        if target.startswith("@"):
            user = await context.bot.get_chat(target)
            target_user_id = user.id
        elif target.isdigit():
            target_user_id = int(target)
        else:
            await update.message.reply_text("❌ یوزرنیم یا آیدی نامعتبر!")
            return
        await context.bot.unban_chat_member(chat_id, target_user_id, only_if_banned=True)
        name, username = await get_user_info(context.bot, target_user_id)
        await update.message.reply_text(f"✅ بن کاربر {name} ({username}) برداشته شد!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا:\n{str(e)}")

# /kick
async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not await is_admin(update, user_id):
        await update.message.reply_text("⛔ فقط ادمین‌ها می‌تونن از این دستور استفاده کنن!")
        return
    
    target_user_id = None
    reason = ""
    
    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
        if context.args:
            reason = " " + " ".join(context.args)
    elif context.args:
        target = context.args[0]
        if target.startswith("@"):
            try:
                user = await context.bot.get_chat(target)
                target_user_id = user.id
            except:
                await update.message.reply_text("❌ کاربر با این یوزرنیم پیدا نشد!")
                return
        elif target.isdigit():
            target_user_id = int(target)
        else:
            await update.message.reply_text("❌ یوزرنیم یا آیدی نامعتبر!")
            return
        if len(context.args) > 1:
            reason = " " + " ".join(context.args[1:])
    else:
        await update.message.reply_text("❌ نحوه استفاده:\n1. ریپلی: /kick\n2. با یوزرنیم: /kick @username\n3. با آیدی: /kick 123456789")
        return
    
    if target_user_id == context.bot.id:
        await update.message.reply_text("❌ نمی‌تونم خودم رو کیک کنم! 😄")
        return
    
    if await is_admin(update, target_user_id):
        await update.message.reply_text("❌ نمی‌تونم ادمین رو کیک کنم!")
        return
    
    try:
        name, username = await get_user_info(context.bot, target_user_id)
        admin_name, _ = await get_user_info(context.bot, user_id)
        await context.bot.ban_chat_member(chat_id, target_user_id, revoke_messages=False)
        await context.bot.unban_chat_member(chat_id, target_user_id)
        await update.message.reply_text(f"👢 کاربر {name} ({username}) توسط {admin_name} از گروه خارج شد!{reason}")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا:\n{str(e)}")

# /mute
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not await is_admin(update, user_id):
        await update.message.reply_text("⛔ فقط ادمین‌ها می‌تونن از این دستور استفاده کنن!")
        return
    
    target_user_id = None
    mute_duration = 300
    
    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
        if context.args:
            try:
                mute_duration = parse_time(context.args[0])
            except:
                await update.message.reply_text("❌ زمان نامعتبر! مثال: 5m, 1h, 30s")
                return
    elif context.args:
        target = context.args[0]
        if target.startswith("@") or target.isdigit():
            if target.startswith("@"):
                try:
                    user = await context.bot.get_chat(target)
                    target_user_id = user.id
                except:
                    await update.message.reply_text("❌ کاربر با این یوزرنیم پیدا نشد!")
                    return
            else:
                target_user_id = int(target)
            if len(context.args) > 1:
                try:
                    mute_duration = parse_time(context.args[1])
                except:
                    await update.message.reply_text("❌ زمان نامعتبر! مثال: 5m, 1h, 30s")
                    return
        else:
            try:
                mute_duration = parse_time(target)
                await update.message.reply_text("❌ لطفاً کاربر رو مشخص کن!\n/mute @username [زمان]")
                return
            except:
                await update.message.reply_text("❌ نحوه استفاده:\n/mute @username 5m")
                return
    else:
        await update.message.reply_text("❌ نحوه استفاده:\n1. ریپلی: /mute 5m\n2. با یوزرنیم: /mute @username 5m\n3. با آیدی: /mute 123456789 5m")
        return
    
    if target_user_id == context.bot.id:
        await update.message.reply_text("❌ نمی‌تونم خودم رو میوت کنم! 😄")
        return
    
    if await is_admin(update, target_user_id):
        await update.message.reply_text("❌ نمی‌تونم ادمین رو میوت کنم!")
        return
    
    try:
        name, username = await get_user_info(context.bot, target_user_id)
        admin_name, _ = await get_user_info(context.bot, user_id)
        until_date = datetime.now() + timedelta(seconds=mute_duration)
        await context.bot.restrict_chat_member(
            chat_id,
            target_user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        time_text = format_time(mute_duration)
        await update.message.reply_text(f"🔇 کاربر {name} ({username}) توسط {admin_name} به مدت {time_text} میوت شد!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا:\n{str(e)}")

# /unmute
async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not await is_admin(update, user_id):
        await update.message.reply_text("⛔ فقط ادمین‌ها می‌تونن از این دستور استفاده کنن!")
        return
    
    target_user_id = None
    
    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
    elif context.args:
        target = context.args[0]
        if target.startswith("@"):
            try:
                user = await context.bot.get_chat(target)
                target_user_id = user.id
            except:
                await update.message.reply_text("❌ کاربر پیدا نشد!")
                return
        elif target.isdigit():
            target_user_id = int(target)
        else:
            await update.message.reply_text("❌ یوزرنیم یا آیدی نامعتبر!")
            return
    else:
        await update.message.reply_text("❌ ریپلی کن یا یوزرنیم/آیدی رو وارد کن:\n/unmute @user")
        return
    
    try:
        name, username = await get_user_info(context.bot, target_user_id)
        await context.bot.restrict_chat_member(
            chat_id,
            target_user_id,
            permissions=ChatPermissions(can_send_messages=True)
        )
        await update.message.reply_text(f"✅ کاربر {name} ({username}) آن‌میوت شد!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا:\n{str(e)}")

# /pin
async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not await is_admin(update, user_id):
        await update.message.reply_text("⛔ فقط ادمین‌ها می‌تونن پیام رو پین کنن!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ روی پیامی که می‌خوای پین کنی ریپلی کن:\n/pin")
        return
    
    try:
        disable_notification = True
        if context.args and context.args[0].lower() == "notify":
            disable_notification = False
        
        await context.bot.pin_chat_message(
            chat_id,
            update.message.reply_to_message.message_id,
            disable_notification=disable_notification
        )
        await update.message.reply_text("📌 پیام با موفقیت پین شد!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا:\n{str(e)}")

# /unpin
async def unpin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not await is_admin(update, user_id):
        await update.message.reply_text("⛔ فقط ادمین‌ها می‌تونن پیام رو آنپین کنن!")
        return
    
    try:
        if update.message.reply_to_message:
            await context.bot.unpin_chat_message(
                chat_id,
                update.message.reply_to_message.message_id
            )
            await update.message.reply_text("📌 پیام مورد نظر آنپین شد!")
        else:
            await context.bot.unpin_all_chat_messages(chat_id)
            await update.message.reply_text("📌 همه پیام‌های پین شده آنپین شدند!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا:\n{str(e)}")

# /kickme
async def kick_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        await context.bot.ban_chat_member(chat_id, user_id, revoke_messages=False)
        await context.bot.unban_chat_member(chat_id, user_id)
        await update.message.reply_text("😂 خودت رو کیک کردی! دوباره بیا!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

# /link
async def group_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    try:
        chat_member = update.effective_chat.get_member(user_id)
        if chat_member not in ["administrator", "creator"]:
            await update.message.reply_text("فقط ادمین ها میتونن لینک دعوت بگیرن")
            return
    except Exception as e:
        try:
            link = await context.bot.createChatInviteLink(chat_id, None, None, None, False)
            await update.effective_message.reply_text(f"link: {link.invite_link}")
        except Exception as e:
            await update.effective_message.reply_text(f"error: {e}")

# ==================== اجرای اصلی ====================
def main():
    app = Application.builder().token(TOKEN).build()
    
    # پیام خوش‌آمدگویی
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    
    # منوی اصلی با دکمه
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # بازی‌ها
    app.add_handler(CommandHandler("games", games_menu))
    app.add_handler(CommandHandler("dice", roll_dice))
    app.add_handler(CommandHandler("football", football))
    app.add_handler(CommandHandler("basket", basketball))
    app.add_handler(CommandHandler("lottery", lottery))
    app.add_handler(CommandHandler("random_number", random_number))
    app.add_handler(CommandHandler("coin", coin_flip))
    
    # ابزارها
    app.add_handler(CommandHandler("time", get_time))
    
    # دستورات مدیریتی
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("kick", kick_user))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("unmute", unmute_user))
    app.add_handler(CommandHandler("pin", pin_message))
    app.add_handler(CommandHandler("unpin", unpin_message))
    app.add_handler(CommandHandler("kickme", kick_me))
    app.add_handler(CommandHandler("link", group_link))
    
    print("🤖 ربات مدیریت و سرگرمی گروه روشن شد...")
    print(f"✅ توکن: {TOKEN[:10]}... (مخفی شده)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
