# ==================== تنظیمات با متغیر محیطی ====================

import os
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی از فایل .env
load_dotenv()

# دریافت توکن و آیدی مالک از متغیرهای محیطی
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

# تنظیمات پیش‌فرض
WARN_LIMIT = 3
MUTE_DURATION = 3600

# ==================== کد اصلی ربات ====================

import logging
import json
import re
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Union
from functools import wraps

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ChatPermissions, Message, ChatMember, User
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler
)
from telegram.constants import ParseMode

# ==================== تنظیمات لاگ ====================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== دیتابیس ====================

class DataStore:
    def __init__(self, file_path="data.json"):
        self.file_path = file_path
        self.data = self._load()
    
    def _load(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "warns": {},
                "filters": {},
                "notes": {},
                "banned_words": [],
                "welcome": {},
                "goodbye": {},
                "settings": {},
                "locked": {},
                "saved": {},
                "rules": {},
                "force_join": {},
                "custom_admins": {}
            }
    
    def _save(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def get_warns(self, chat_id: int, user_id: int) -> int:
        key = f"{chat_id}:{user_id}"
        return self.data["warns"].get(key, 0)
    
    def add_warn(self, chat_id: int, user_id: int) -> int:
        key = f"{chat_id}:{user_id}"
        self.data["warns"][key] = self.data["warns"].get(key, 0) + 1
        self._save()
        return self.data["warns"][key]
    
    def clear_warns(self, chat_id: int, user_id: int):
        key = f"{chat_id}:{user_id}"
        if key in self.data["warns"]:
            del self.data["warns"][key]
            self._save()
    
    def get_filters(self, chat_id: int) -> Dict:
        return self.data["filters"].get(str(chat_id), {})
    
    def add_filter(self, chat_id: int, word: str, reply: str):
        if str(chat_id) not in self.data["filters"]:
            self.data["filters"][str(chat_id)] = {}
        self.data["filters"][str(chat_id)][word.lower()] = reply
        self._save()
    
    def remove_filter(self, chat_id: int, word: str) -> bool:
        if str(chat_id) in self.data["filters"]:
            if word.lower() in self.data["filters"][str(chat_id)]:
                del self.data["filters"][str(chat_id)][word.lower()]
                self._save()
                return True
        return False
    
    def is_locked(self, chat_id: int, lock_type: str) -> bool:
        return self.data["locked"].get(str(chat_id), {}).get(lock_type, False)
    
    def set_lock(self, chat_id: int, lock_type: str, value: bool):
        if str(chat_id) not in self.data["locked"]:
            self.data["locked"][str(chat_id)] = {}
        self.data["locked"][str(chat_id)][lock_type] = value
        self._save()
    
    def save_message(self, chat_id: int, name: str, content: str):
        if str(chat_id) not in self.data["saved"]:
            self.data["saved"][str(chat_id)] = {}
        self.data["saved"][str(chat_id)][name] = content
        self._save()
    
    def get_saved_message(self, chat_id: int, name: str) -> Optional[str]:
        return self.data["saved"].get(str(chat_id), {}).get(name)
    
    def get_all_saved(self, chat_id: int) -> Dict:
        return self.data["saved"].get(str(chat_id), {})

store = DataStore()

# ==================== دیتابیس‌های اضافی ====================

good_data = {}
stats_data = {}
spam_counter = {}
last_message_time = {}
tickets = {}
poll_data = {}

# ==================== ابزارهای کمکی ====================

async def get_target_user(update: Update) -> Optional[User]:
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    
    if update.message.text:
        words = update.message.text.split()
        for word in words:
            if word.startswith("@"):
                username = word.replace("@", "")
                try:
                    member = await update.effective_chat.get_member(username)
                    return member.user
                except:
                    pass
    return None

async def get_target_user_with_args(update: Update) -> tuple[Optional[User], Optional[str]]:
    message = update.message
    target_user = None
    remaining_text = ""
    
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        if message.text:
            text = message.text
            words = text.split()
            if words and words[0] in ["بن", "آن بن", "رفع بن", "سکوت", "رفع سکوت", "اخطار", "گزارش", "مدیر", "حذف مدیر"]:
                words = words[1:]
            remaining_text = " ".join(words)
        return target_user, remaining_text
    
    if message.text:
        words = message.text.split()
        for i, word in enumerate(words):
            if word.startswith("@"):
                username = word.replace("@", "")
                try:
                    member = await update.effective_chat.get_member(username)
                    target_user = member.user
                    remaining_text = " ".join(words[i+1:])
                    return target_user, remaining_text
                except:
                    pass
        
        if not target_user and words:
            if words[0] in ["بن", "آن بن", "رفع بن", "سکوت", "رفع سکوت", "اخطار", "گزارش", "مدیر", "حذف مدیر"]:
                remaining_text = " ".join(words[1:])
    
    return target_user, remaining_text

def parse_time(text: str) -> Optional[int]:
    if not text:
        return None
    
    persian_to_english = {
        '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
        '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
    }
    for p, e in persian_to_english.items():
        text = text.replace(p, e)
    
    patterns = [
        (r"(\d+)\s*[mM]|(\d+)\s*دقیقه", lambda x: int(x) * 60),
        (r"(\d+)\s*[hH]|(\d+)\s*ساعت", lambda x: int(x) * 3600),
        (r"(\d+)\s*[dD]|(\d+)\s*روز", lambda x: int(x) * 86400),
        (r"(\d+)\s*[sS]|(\d+)\s*ثانیه", lambda x: int(x)),
    ]
    
    for pattern, converter in patterns:
        match = re.search(pattern, text)
        if match:
            for group in match.groups():
                if group and group.isdigit():
                    return converter(group)
    return None

def get_user_mention(user) -> str:
    if user.username:
        return f"@{user.username}"
    return f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"

async def is_group_admin(update: Update, user_id: int) -> bool:
    try:
        member = await update.effective_chat.get_member(user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False

def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if user_id == OWNER_ID:
            return await func(update, context, *args, **kwargs)
        
        try:
            member = await update.effective_chat.get_member(user_id)
            if member.status in ["administrator", "creator"]:
                return await func(update, context, *args, **kwargs)
        except:
            pass
        
        if str(chat_id) in store.data["custom_admins"]:
            if user_id in store.data["custom_admins"][str(chat_id)]:
                return await func(update, context, *args, **kwargs)
        
        await update.message.reply_text(
            "⛔ **دسترسی محدود!**\nفقط ادمین‌های گروه میتوانند از این دستور استفاده کنند.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    return wrapper

def owner_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.id != OWNER_ID:
            await update.message.reply_text(
                "⛔ **دسترسی محدود!**\nاین دستور فقط برای مالک ربات است.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# ==================== دستورات عمومی ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_owner = user.id == OWNER_ID
    
    text = f"🤖 **سلام {user.first_name}!**\n\n"
    text += "من یک ربات مدیریت پیشرفته برای گروه‌های تلگرام هستم.\n\n"
    text += "📋 **دستورات پایه:**\n"
    text += "• `آمار` - مشاهده اطلاعات کاربر\n"
    text += "• `آیدی` - مشاهده آیدی عددی\n"
    text += "• `قوانین` - نمایش قوانین گروه\n"
    text += "• `قود` - دریافت امتیاز (هر ۱۰ دقیقه)\n\n"
    
    if is_owner:
        text += "👑 **شما مالک ربات هستید!**\n"
    
    keyboard = [
        [InlineKeyboardButton("📖 راهنما", callback_data="help_menu")],
        [InlineKeyboardButton("📋 قوانین", callback_data="show_rules")],
        [InlineKeyboardButton("📊 آمار من", callback_data="my_info")],
        [InlineKeyboardButton("🎮 بازی‌ها", callback_data="games_menu")]
    ]
    
    if is_owner:
        keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🛠 **راهنمای کامل ربات**\n\n"
    text += "📌 **دستورات عمومی:**\n"
    text += "• `آمار` - اطلاعات کاربر (با ریپلی یا منشن)\n"
    text += "• `آیدی` - آیدی عددی کاربر\n"
    text += "• `قوانین` - نمایش قوانین\n"
    text += "• `قود` - دریافت امتیاز\n"
    text += "• `تگ ادمین/مالک` - تگ کردن\n"
    text += "• `ذخیره نام متن` - ذخیره پیام\n"
    text += "• `دریافت نام` - دریافت پیام ذخیره شده\n\n"
    
    text += "👮 **دستورات ادمین:**\n"
    text += "• `بن @user` - بن کاربر\n"
    text += "• `آن بن @user` - رفع بن\n"
    text += "• `سکوت @user 10m` - سکوت کاربر\n"
    text += "• `رفع سکوت @user` - رفع سکوت\n"
    text += "• `اخطار @user دلیل` - اخطار\n"
    text += "• `پاک کردن اخطار @user` - پاک کردن اخطار\n"
    text += "• `تعداد اخطار @user` - مشاهده اخطار\n"
    text += "• `فیلتر کلمه پاسخ` - افزودن فیلتر\n"
    text += "• `حذف فیلتر کلمه` - حذف فیلتر\n"
    text += "• `قفل نوع` - قفل پیشرفته\n"
    text += "• `مدیر` (با ریپلی) - افزودن مدیر\n"
    text += "• `حذف مدیر` (با ریپلی) - حذف مدیر\n"
    text += "• `اخراج @user` - اخراج کاربر\n\n"
    
    text += "🎮 **بازی‌ها:**\n"
    text += "• `بسکتبال` - بازی بسکتبال\n"
    text += "• `فوتبال` - بازی فوتبال\n"
    text += "• `تاس` - بازی تاس\n"
    text += "• `لاتری` - بازی لاتری\n"
    text += "• `عدد شانسی عدد` - حدس عدد\n"
    text += "• `بولینگ` - بازی بولینگ\n"
    text += "• `بازی‌ها` - منوی بازی‌ها\n\n"
    
    text += "📌 **همه دستورات با ریپلی هم کار می‌کنند!**"
    
    keyboard = [[InlineKeyboardButton("❌ بستن", callback_data="close")]]
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ammar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update)
    if not target:
        target = update.effective_user
    
    chat = update.effective_chat
    
    try:
        member = await chat.get_member(target.id)
        status = member.status
    except:
        status = "unknown"
    
    status_map = {
        "creator": "👑 سازنده گروه",
        "administrator": "🛡 ادمین",
        "member": "👤 عضو",
        "restricted": "🔇 محدود شده",
        "left": "🚪 خارج شده",
        "kicked": "🚫 بن شده"
    }
    
    warn_count = store.get_warns(chat.id, target.id)
    key = f"{chat.id}:{target.id}"
    good_total = good_data.get(key, {}).get("total", 0)
    
    text = f"📊 **آمار کاربر**\n\n"
    text += f"👤 نام: {target.full_name}\n"
    text += f"🆔 آیدی: `{target.id}`\n"
    text += f"👤 یوزرنیم: @{target.username if target.username else 'ندارد'}\n"
    text += f"📊 وضعیت: {status_map.get(status, status)}\n"
    text += f"⚠️ اخطارها: {warn_count} از {WARN_LIMIT}\n"
    text += f"⭐ قود: {good_total}"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update)
    if not target:
        target = update.effective_user
    
    await update.message.reply_text(
        f"🆔 **آیدی کاربر:**\n\n"
        f"👤 {target.full_name}\n"
        f"🆔 `{target.id}`\n"
        f"👤 @{target.username if target.username else 'ندارد'}",
        parse_mode=ParseMode.MARKDOWN
    )

async def ghavanin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    default_rules = (
        "📋 **قوانین گروه:**\n\n"
        "1️⃣ احترام به یکدیگر\n"
        "2️⃣ عدم ارسال محتوای نامناسب\n"
        "3️⃣ عدم ارسال اسپم\n"
        "4️⃣ رعایت قوانین جمهوری اسلامی ایران\n"
        "5️⃣ در صورت تخلف، اخطار یا بن خواهید شد"
    )
    
    rules = store.data.get("rules", {}).get(str(chat_id), default_rules)
    await update.message.reply_text(rules, parse_mode=ParseMode.MARKDOWN)

async def good_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    now = datetime.now()
    
    key = f"{chat_id}:{user_id}"
    
    last_good = good_data.get(key, {}).get("last_time")
    
    if last_good:
        time_diff = (now - last_good).total_seconds()
        if time_diff < 600:
            remaining = 600 - int(time_diff)
            minutes = remaining // 60
            seconds = remaining % 60
            await update.message.reply_text(
                f"⏳ **صبر کن!**\n"
                f"تا دریافت قود بعدی {minutes} دقیقه و {seconds} ثانیه مونده.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
    
    good_amount = random.randint(5, 10)
    
    if key not in good_data:
        good_data[key] = {"total": 0, "last_time": now}
    
    good_data[key]["total"] += good_amount
    good_data[key]["last_time"] = now
    
    messages = [
        f"🌟 **{good_amount} قود** دریافت کردی! عالی!",
        f"🎉 **{good_amount} قود**! ادامه بده!",
        f"💪 **{good_amount} قود**! خیلی خوب!",
        f"🔥 **{good_amount} قود**! فوق‌العاده!",
        f"⭐ **{good_amount} قود**! به راهت ادامه بده!",
        f"🏆 **{good_amount} قود**! تو بهترینی!",
    ]
    
    await update.message.reply_text(
        f"{random.choice(messages)}\n\n"
        f"📊 مجموع قودهای شما: **{good_data[key]['total']}**",
        parse_mode=ParseMode.MARKDOWN
    )

# ==================== دستورات مدیریتی ====================
@admin_only
async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "نحوه استفاده\n"
            "حذف 100\n"
            "حذف 50",
            parse_mode = ParseMode.MARKDOWN
        )
        return
    try:
        count = int(context.args[0])
    except ValueError:
        await update.message.reply_text("یک عدد وارد کن")
        return
    if count > 100:
        count = 100
        await update.message.reply_text("حداکثر 100 پیام")
    if count < 1:
        await update.message.reply_text("حداقل 100 پیام")
        return

    try:
        message_id = update.message.message_id
        message_ids = list(range(message_id - count, message_id))

        await update.effective_chat.delete_messages(message_ids)

        msg = await update.message.reply_text(f"تعداد {count} پیام پاک شد")
        await msg.delete(delay=3)
    except Expection as e:
        await update.message.reply_text(f"خطا: {str(e)}")
@admin_only
async def persian_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update)
    
    if not target:
        await update.message.reply_text("❗ روی پیام کاربر ریپلی بزنید یا بنویسید `بن @username`")
        return
    
    if target.id == update.effective_user.id:
        await update.message.reply_text("🙃 نمی‌تونی خودتو بن کنی!")
        return
    
    if target.id == OWNER_ID:
        await update.message.reply_text("👑 نمی‌توانید مالک ربات را بن کنید!")
        return
    
    try:
        member = await update.effective_chat.get_member(target.id)
        if member.status in ["administrator", "creator"]:
            await update.message.reply_text("⛔ نمی‌توانید یک ادمین را بن کنید!")
            return
    except:
        pass
    
    try:
        await update.effective_chat.ban_member(target.id)
        await update.message.reply_text(
            f"🚫 کاربر {get_user_mention(target)} **بن** شد.",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

@admin_only
async def persian_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update)
    
    if not target and context.args:
        user_input = context.args[0]
        if user_input.startswith("@"):
            try:
                member = await update.effective_chat.get_member(user_input)
                target = member.user
            except:
                pass
        else:
            try:
                user_id = int(user_input)
                target = User(id=user_id, first_name="کاربر", is_bot=False)
            except:
                pass
    
    if not target:
        await update.message.reply_text("❗ روی پیام کاربر ریپلی بزنید یا بنویسید `آن بن @username`")
        return
    
    try:
        await update.effective_chat.unban_member(target.id)
        await update.message.reply_text(
            f"✅ کاربر {get_user_mention(target)} از **بن** خارج شد.",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

@admin_only
async def persian_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target, remaining_text = await get_target_user_with_args(update)
    
    if not target:
        await update.message.reply_text("❗ روی پیام کاربر ریپلی بزنید یا بنویسید `سکوت @username 10m`")
        return
    
    if target.id == update.effective_user.id:
        await update.message.reply_text("🙃 خودتو سکوت نکن!")
        return
    
    duration = None
    if remaining_text:
        parsed_time = parse_time(remaining_text)
        if parsed_time:
            duration = parsed_time
    
    try:
        if duration:
            until_date = datetime.now() + timedelta(seconds=duration)
            await update.effective_chat.restrict_member(
                target.id,
                ChatPermissions(can_send_messages=False),
                until_date=until_date
            )
            
            if duration < 60:
                time_text = f"{duration} ثانیه"
            elif duration < 3600:
                time_text = f"{duration//60} دقیقه"
            elif duration < 86400:
                time_text = f"{duration//3600} ساعت"
            else:
                time_text = f"{duration//86400} روز"
            
            await update.message.reply_text(
                f"🔇 کاربر {get_user_mention(target)} به مدت **{time_text}** سکوت شد.",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.effective_chat.restrict_member(
                target.id,
                ChatPermissions(can_send_messages=False)
            )
            await update.message.reply_text(
                f"🔇 کاربر {get_user_mention(target)} **به طور دائمی** سکوت شد.",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

@admin_only
async def persian_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update)
    
    if not target:
        await update.message.reply_text("❗ روی پیام کاربر ریپلی بزنید یا بنویسید `رفع سکوت @username`")
        return
    
    try:
        await update.effective_chat.restrict_member(
            target.id,
            ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_photos=True,
                can_send_polls=True,
                can_send_videos=True,
                can_send_documents=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_invite_users=True
            )
        )
        await update.message.reply_text(
            f"🔊 سکوت کاربر {get_user_mention(target)} **برداشته شد**.",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

@admin_only
async def persian_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target, reason = await get_target_user_with_args(update)
    
    if not target:
        await update.message.reply_text("❗ روی پیام کاربر ریپلی بزنید یا بنویسید `اخطار @username دلیل`")
        return
    
    if target.id == update.effective_user.id:
        await update.message.reply_text("🙃 نمی‌تونی به خودت اخطار بدی!")
        return
    
    if target.id == OWNER_ID:
        await update.message.reply_text("👑 نمی‌توانید به مالک ربات اخطار دهید!")
        return
    
    try:
        member = await update.effective_chat.get_member(target.id)
        if member.status in ["administrator", "creator"]:
            await update.message.reply_text("⛔ نمی‌توانید به یک ادمین اخطار دهید!")
            return
    except:
        pass
    
    chat_id = update.effective_chat.id
    
    if not reason:
        reason = "بدون دلیل"
    
    warn_count = store.add_warn(chat_id, target.id)
    
    warn_text = (
        f"⚠️ **اخطار به کاربر** {get_user_mention(target)}\n\n"
        f"📊 تعداد اخطارها: **{warn_count}** از {WARN_LIMIT}\n"
        f"📝 دلیل: {reason}\n"
        f"👮 اخطاردهنده: {get_user_mention(update.effective_user)}"
    )
    
    await update.message.reply_text(warn_text, parse_mode=ParseMode.HTML)
    
    if warn_count >= WARN_LIMIT:
        try:
            until_date = datetime.now() + timedelta(seconds=MUTE_DURATION)
            await update.effective_chat.restrict_member(
                target.id,
                ChatPermissions(can_send_messages=False),
                until_date=until_date
            )
            
            await update.message.reply_text(
                f"🚫 **کاربر {get_user_mention(target)} به صورت خودکار سکوت شد!**\n"
                f"⏱ مدت: {MUTE_DURATION//60} دقیقه",
                parse_mode=ParseMode.HTML
            )
            
            store.clear_warns(chat_id, target.id)
        except Exception as e:
            await update.message.reply_text(f"❌ خطا: {str(e)}")

@admin_only
async def persian_unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update)
    
    if not target:
        await update.message.reply_text("❗ روی پیام کاربر ریپلی بزنید یا بنویسید `پاک کردن اخطار @username`")
        return
    
    chat_id = update.effective_chat.id
    old_count = store.get_warns(chat_id, target.id)
    
    if old_count == 0:
        await update.message.reply_text(f"✅ کاربر {get_user_mention(target)} اخطاری ندارد!", parse_mode=ParseMode.HTML)
        return
    
    store.clear_warns(chat_id, target.id)
    await update.message.reply_text(
        f"✅ **تمام {old_count} اخطار** کاربر {get_user_mention(target)} پاک شد.",
        parse_mode=ParseMode.HTML
    )

@admin_only
async def persian_warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update)
    if not target:
        target = update.effective_user
    
    chat_id = update.effective_chat.id
    warn_count = store.get_warns(chat_id, target.id)
    
    text = f"📊 **اطلاعات اخطارهای کاربر**\n\n"
    text += f"👤 کاربر: {get_user_mention(target)}\n"
    text += f"🆔 آیدی: `{target.id}`\n"
    text += f"📊 تعداد اخطارها: **{warn_count}** از {WARN_LIMIT}\n"
    
    if warn_count == 0:
        text += "\n✅ این کاربر اخطاری ندارد."
    elif warn_count < WARN_LIMIT:
        remaining = WARN_LIMIT - warn_count
        text += f"\n⚠️ تا سکوت خودکار {remaining} اخطار دیگر باقی است."
    else:
        text += "\n🚫 این کاربر به دلیل اخطار زیاد سکوت شده است."
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

@admin_only
async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update)
    
    if not target:
        await update.message.reply_text("❗ روی پیام کاربر ریپلی بزنید یا بنویسید `اخراج @username`")
        return
    
    if target.id == update.effective_user.id:
        await update.message.reply_text("🙃 نمی‌تونی خودتو اخراج کنی!")
        return
    
    if target.id == OWNER_ID:
        await update.message.reply_text("👑 نمی‌توانید مالک ربات را اخراج کنید!")
        return
    
    try:
        member = await update.effective_chat.get_member(target.id)
        if member.status in ["administrator", "creator"]:
            await update.message.reply_text("⛔ نمی‌توانید یک ادمین را اخراج کنید!")
            return
    except:
        pass
    
    try:
        await update.effective_chat.ban_member(target.id)
        await update.effective_chat.unban_member(target.id)
        await update.message.reply_text(
            f"👢 کاربر {get_user_mention(target)} از گروه **اخراج شد**.",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

# ==================== سیستم فیلتر ====================

@admin_only
async def filter_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if len(text.split()) < 3:
        await update.message.reply_text(
            "❗ **نحوه استفاده:**\n"
            "`فیلتر کلمه پاسخ`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    parts = text.split(maxsplit=2)
    word = parts[1].lower()
    reply = parts[2]
    
    chat_id = update.effective_chat.id
    store.add_filter(chat_id, word, reply)
    
    await update.message.reply_text(
        f"✅ **فیلتر '{word}' با موفقیت اضافه شد.**",
        parse_mode=ParseMode.MARKDOWN
    )

@admin_only
async def filter_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if len(text.split()) < 3:
        await update.message.reply_text(
            "❗ **نحوه استفاده:**\n"
            "`حذف فیلتر کلمه`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    word = text.split(maxsplit=2)[1].lower()
    chat_id = update.effective_chat.id
    
    if store.remove_filter(chat_id, word):
        await update.message.reply_text(f"✅ **فیلتر '{word}' حذف شد.**", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"❌ فیلتر '{word}' پیدا نشد.")

# ==================== سیستم ذخیره ====================

@admin_only
async def save_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text
    
    if len(text.split()) < 3:
        await update.message.reply_text(
            "❗ **نحوه استفاده:**\n"
            "`ذخیره نام متن`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    parts = text.split(maxsplit=2)
    name = parts[1]
    content = parts[2]
    
    store.save_message(chat_id, name, content)
    await update.message.reply_text(f"✅ **پیام با نام '{name}' ذخیره شد.**", parse_mode=ParseMode.MARKDOWN)

async def get_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text
    
    if len(text.split()) < 2:
        await update.message.reply_text(
            "❗ **نحوه استفاده:**\n"
            "`دریافت نام`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    name = text.split(maxsplit=1)[1]
    content = store.get_saved_message(chat_id, name)
    
    if content:
        await update.message.reply_text(
            f"📝 **{name}:**\n{content}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(f"❌ پیام با نام '{name}' پیدا نشد.")

# ==================== سیستم تگ ====================

async def tag_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    text = update.message.text
    
    if len(text.split()) < 2:
        await update.message.reply_text(
            "❗ **نحوه استفاده:**\n"
            "`تگ ادمین` - تگ ادمین‌ها\n"
            "`تگ مالک` - تگ مالک",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    tag_type = text.split(maxsplit=1)[1].strip()
    
    if tag_type == "ادمین":
        admins = []
        try:
            async for member in chat.get_administrators():
                if not member.user.is_bot:
                    admins.append(
                        f"@{member.user.username}" if member.user.username 
                        else f"[{member.user.full_name}](tg://user?id={member.user.id})"
                    )
        except:
            pass
        
        if admins:
            await update.message.reply_text(
                f"🛡 **ادمین‌های گروه:**\n\n" + "\n".join(admins),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ ادمینی یافت نشد.")
    
    elif tag_type == "مالک":
        owner_id = OWNER_ID
        try:
            owner = await context.bot.get_chat(owner_id)
            username = f"@{owner.username}" if owner.username else f"[{owner.full_name}](tg://user?id={owner_id})"
            await update.message.reply_text(
                f"👑 **مالک ربات:**\n{username}",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            await update.message.reply_text(f"👑 آیدی مالک: `{owner_id}`", parse_mode=ParseMode.MARKDOWN)
    
    else:
        await update.message.reply_text(
            f"❌ نوع تگ '{tag_type}' نامعتبر است.\n"
            "انواع مجاز: `ادمین`, `مالک`",
            parse_mode=ParseMode.MARKDOWN
        )

# ==================== بازی‌ها ====================

async def basketball_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    shots = [
        "🏀 **پرش!** توپ وارد حلقه شد! 🎉",
        "🏀 توپ به حلقه خورد و بیرون افتاد! 😅",
        "🏀 توپ به تخته خورد و وارد شد! 🎯",
        "🏀 **سه امتیازی!** عالی بود! 🏆",
        "🏀 توپ از کنار حلقه رد شد! 😔",
        "🏀 دانک! تماشایی بود! 🔥",
        "🏀 توپ به تخته خورد و برگشت! ❌"
    ]
    result = random.choice(shots)
    
    await update.message.reply_text(
        f"🏀 **بازی بسکتبال**\n\n"
        f"👤 {user.full_name} پرتاب کرد!\n\n"
        f"{result}",
        parse_mode=ParseMode.MARKDOWN
    )

async def football_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    results = [
        "⚽ **گل!** ضربه عالی به تیرک زد و وارد شد! 🎉",
        "⚽ ضربه به تیرک خورد و بیرون رفت! 😅",
        "⚽ **گل!** دروازه‌بان رو فریب دادی! 🎯",
        "⚽ دروازه‌بان ضربه رو گرفت! ❌",
        "⚽ **گل!** ضربه ایستگاهی تماشایی! 🔥",
        "⚽ توپ به اوت رفت! 😔",
        "⚽ **هت‌تریک!** بینظیر بودی! 🏆"
    ]
    result = random.choice(results)
    
    await update.message.reply_text(
        f"⚽ **بازی فوتبال - پنالتی**\n\n"
        f"👤 {user.full_name} ضربه زد!\n\n"
        f"{result}",
        parse_mode=ParseMode.MARKDOWN
    )

async def dice_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    dice = random.randint(1, 6)
    dice_emojis = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    
    messages = {
        1: "شروع بدی داشتی! 😅",
        2: "بد نبود! 💪",
        3: "متوسط! 👍",
        4: "خوب بود! 🎯",
        5: "عالی! 🔥",
        6: "**جکپات!** 🎉🎉🎉"
    }
    
    await update.message.reply_text(
        f"🎲 **بازی تاس**\n\n"
        f"👤 {user.full_name} پرتاب کرد!\n\n"
        f"{dice_emojis[dice-1]} **عدد {dice}**\n\n"
        f"{messages[dice]}",
        parse_mode=ParseMode.MARKDOWN
    )

async def lottery_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_winner = random.random() < 0.1
    
    if is_winner:
        prize = random.choice(["🎁 ۱۰۰ امتیاز", "🎁 یک جایزه ویژه", "🎁 تخفیف ۵۰٪", "🎁 کارت هدیه"])
        result = f"🎉 **تبریک! شما برنده شدید!**\n\n🏆 جایزه شما: {prize}"
    else:
        results = [
            "متاسفانه برنده نشدی! 😔 دفعه بعد امتحان کن.",
            "جایزه به یکی دیگه رسید! 😅 بازم امتحان کن.",
            "شانس نیاوردی! 💪 ادامه بده.",
            "نزدیک بود! 🔥 یک بار دیگه امتحان کن."
        ]
        result = random.choice(results)
    
    await update.message.reply_text(
        f"🎰 **بازی لاتری**\n\n"
        f"👤 {user.full_name}\n\n"
        f"{result}",
        parse_mode=ParseMode.MARKDOWN
    )

async def lucky_number_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    number = random.randint(1, 1000)

    keyboard = [
        [InlineKeyboardButton("عدد جدید", callback_data="lucky_new")],
        [InlineKeyboardButton("بازی ها", callback_data="games_menu")],
        [InlineKeyboardButton("بستن", callback_data="close")],
    ]
    await update.message.reply_text(
        f"عدد شانسی\n"
        f"\n"
        f"{user.full_name}"
        f"\n"
        f"عدد شما: {number}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
async def bowling_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    pins = random.randint(0, 10)
    
    messages = {
        0: "همه پین‌ها سر جاشون! 😅",
        1: "فقط یکی رو زدی! 😔",
        2: "دو تا! بد نیست! 💪",
        3: "سه تا! 👍",
        4: "چهار تا! خوب بود! 🎯",
        5: "نصفشون رو زدی! 🔥",
        6: "شش تا! عالی! 💪",
        7: "هفت تا! خیلی خوب! 🎉",
        8: "هشت تا! عالی بود! 🏆",
        9: "نزدیک بود کامل بشه! 🔥",
        10: "🎯 **استرایک!** همه پین‌ها رو زدی! 🎉🎉🎉"
    }
    
    emoji = "🎳" + "🟢" * pins + "⚪" * (10 - pins)
    
    await update.message.reply_text(
        f"🎳 **بازی بولینگ**\n\n"
        f"👤 {user.full_name} پرتاب کرد!\n\n"
        f"📊 پین‌های افتاده: **{pins}** از ۱۰\n"
        f"{emoji}\n\n"
        f"{messages[pins]}",
        parse_mode=ParseMode.MARKDOWN
    )

async def games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏀 بسکتبال", callback_data="game_basketball")],
        [InlineKeyboardButton("⚽ فوتبال", callback_data="game_football")],
        [InlineKeyboardButton("🎲 تاس", callback_data="game_dice")],
        [InlineKeyboardButton("🎰 لاتری", callback_data="game_lottery")],
        [InlineKeyboardButton("🔢 عدد شانسی", callback_data="game_lucky")],
        [InlineKeyboardButton("🎳 بولینگ", callback_data="game_bowling")],
        [InlineKeyboardButton("❌ بستن", callback_data="close")]
    ]
    
    await update.message.reply_text(
        "🎮 **منوی بازی‌ها**\n\nیک بازی رو انتخاب کن! 😊",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== دکمه‌های شیشه‌ای ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "help_menu":
        await help_command(update, context)
        await query.message.delete()
    
    elif data == "show_rules":
        await ghavanin_command(update, context)
        await query.message.delete()
    
    elif data == "my_info":
        await ammar_command(update, context)
        await query.message.delete()
    
    elif data == "games_menu":
        await games_menu(update, context)
        await query.message.delete()
        
    elif data == "close":
        await query.message.delete()
    
    elif data.startswith("game_"):
        game = data.replace("game_", "")
        
        class FakeUpdate:
            def __init__(self, original_update):
                self.effective_user = original_update.effective_user
                self.effective_chat = original_update.effective_chat
                self.message = type('obj', (object,), {
                    'reply_text': query.message.reply_text,
                    'text': game
                })()
        
        fake_update = FakeUpdate(update)
        
        if game == "basketball":
            await basketball_game(fake_update, context)
        elif game == "football":
            await football_game(fake_update, context)
        elif game == "dice":
            await dice_game(fake_update, context)
        elif game == "lottery":
            await lottery_game(fake_update, context)
        elif game == "lucky":
            await lucky_number_game(fake_update, context)
        elif game == "bowling":
            await bowling_game(fake_update, context)
        
        await query.message.delete()

# ==================== فیلتر پیام‌ها و آنتی‌اسپم ====================

async def check_antispam(update: Update) -> bool:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    key = f"{chat_id}:{user_id}"
    
    if await is_group_admin(update, user_id):
        return True
    
    now = datetime.now()
    
    if key in spam_counter:
        if (now - spam_counter[key]["first_time"]).total_seconds() > 2:
            spam_counter[key] = {"count": 1, "first_time": now}
            return True
    
    if key not in spam_counter:
        spam_counter[key] = {"count": 1, "first_time": now}
        return True
    
    spam_counter[key]["count"] += 1
    
    if spam_counter[key]["count"] >= 5:
        try:
            until_date = now + timedelta(seconds=60)
            await update.effective_chat.restrict_member(
                user_id,
                ChatPermissions(can_send_messages=False),
                until_date=until_date
            )
            
            await update.message.delete()
            await update.message.reply_text(
                f"🚫 **کاربر {get_user_mention(update.effective_user)} به دلیل اسپم به مدت ۱ دقیقه سکوت شد.**",
                parse_mode=ParseMode.HTML
            )
            
            del spam_counter[key]
            return False
        except:
            pass
    
    return True

async def check_delay(update: Update) -> bool:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    key = f"{chat_id}:{user_id}"
    
    if await is_group_admin(update, user_id):
        return True
    
    now = datetime.now()
    
    if key in last_message_time:
        time_diff = (now - last_message_time[key]).total_seconds()
        if time_diff < 1:
            await update.message.delete()
            await update.message.reply_text("⏳ **لطفاً ۱ ثانیه صبر کنید.**", parse_mode=ParseMode.MARKDOWN)
            return False
    
    last_message_time[key] = now
    return True

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    text = update.message.text
    
    if text == "قوانین" or text == "قوانین گروه":
        await ghavanin_command(update, context)
        return
    
    if not await check_antispam(update):
        return
    
    if not await check_delay(update):
        return
    
    chat_id = update.effective_chat.id
    filters = store.get_filters(chat_id)
    for word, reply in filters.items():
        if word in text.lower():
            await update.message.reply_text(reply)
            break

# ==================== رویدادهای گروه ====================

async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return
    
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            await update.message.reply_text(
                "🤖 **سلام! من ربات مدیریت گروه هستم.**\n"
                "برای مشاهده راهنما از /help استفاده کنید.",
                parse_mode=ParseMode.MARKDOWN
            )
            continue
        
        welcome_text = store.data["welcome"].get(str(update.effective_chat.id))
        if welcome_text:
            text = welcome_text.replace("{user}", f"[{member.full_name}](tg://user?id={member.id})")
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def handle_left_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.left_chat_member:
        return
    
    member = update.message.left_chat_member
    goodbye_text = store.data["goodbye"].get(str(update.effective_chat.id))
    
    if goodbye_text:
        text = goodbye_text.replace("{user}", f"[{member.full_name}](tg://user?id={member.id})")
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ==================== تابع اصلی ====================
async def lucky_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "lucky_new":
        user = query.from_user
        number = random_randint(1, 1000)

        keyboard = [
            [InlineKeyboardButton("عدد جدید", callback_data="lucky_new")],
            [InlineKeyboardButton("بازی ها", callback_data="games_menu")],
            [InlineKeyboardButton("بستن", callback_data="close")],
        ]
        await update.message.reply_text(
            f"عدد شانسی\n"
            f"\n"
            f"{user.full_name}"
            f"\n"
            f"عدد شما: {number}",
            parse_mode = ParseMode.MARKDOWN,
            reply_markup = InlineKeyboardMarkup(keyboard)
        )
def main():
    if not BOT_TOKEN:
        print("❌ خطا: توکن ربات تنظیم نشده است!")
        print("لطفاً فایل .env را ایجاد کنید و BOT_TOKEN را تنظیم کنید.")
        return
    
    if OWNER_ID == 0:
        print("❌ خطا: آیدی مالک تنظیم نشده است!")
        print("لطفاً فایل .env را ایجاد کنید و OWNER_ID را تنظیم کنید.")
        return
    
    print("✅ ربات در حال راه‌اندازی...")
    print(f"🤖 توکن: {BOT_TOKEN[:10]}...")
    print(f"👑 آیدی مالک: {OWNER_ID}")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # دستورات عمومی
    application.add_handler(CallbackQueryHandler(lucky_callback, pattern=r'^lucky_'))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # دستورات فارسی
    application.add_handler(MessageHandler(filters.Regex(r'^آمار(\s|$)') | filters.Regex(r'^آمار$'), ammar_command))
    application.add_handler(MessageHandler(filters.Regex(r'^آیدی(\s|$)') | filters.Regex(r'^آیدی$'), id_command))
    application.add_handler(MessageHandler(filters.Regex(r'^قوانین(\s|$)') | filters.Regex(r'^قوانین$'), ghavanin_command))
    application.add_handler(MessageHandler(filters.Regex(r'^قود(\s|$)') | filters.Regex(r'^قود$'), good_command))
    
    # سیستم ذخیره
    application.add_handler(MessageHandler(filters.Regex(r'^ذخیره(\s|$)') | filters.Regex(r'^ذخیره$'), save_command))
    application.add_handler(MessageHandler(filters.Regex(r'^دریافت(\s|$)') | filters.Regex(r'^دریافت$'), get_command))
    
    # سیستم تگ
    application.add_handler(MessageHandler(filters.Regex(r'^تگ(\s|$)') | filters.Regex(r'^تگ$'), tag_command))
    
    # سیستم فیلتر
    application.add_handler(MessageHandler(filters.Regex(r'^فیلتر(\s|$)') | filters.Regex(r'^فیلتر$'), filter_add))
    application.add_handler(MessageHandler(filters.Regex(r'^حذف فیلتر(\s|$)') | filters.Regex(r'^حذف فیلتر$'), filter_remove))
    
    # دستورات مدیریتی
    application.add_handler(MessageHandler(filters.Regex(r'^بن(\s|$)') | filters.Regex(r'^بن$'), persian_ban))
    application.add_handler(MessageHandler(filters.Regex(r'^(آن بن|رفع بن)(\s|$)') | filters.Regex(r'^(آن بن|رفع بن)$'), persian_unban))
    application.add_handler(MessageHandler(filters.Regex(r'^سکوت(\s|$)') | filters.Regex(r'^سکوت$'), persian_mute))
    application.add_handler(MessageHandler(filters.Regex(r'حذف سکوت(\s|$)') | filters.Regex(r'^حذف سکوت$'), persian_unmute))
    application.add_handler(MessageHandler(filters.Regex(r'^اخطار(\s|$)') | filters.Regex(r'^اخطار$'), persian_warn))
    application.add_handler(MessageHandler(filters.Regex(r'^(پاک کردن اخطار|پاک کردن اخطارها)(\s|$)') | filters.Regex(r'^(پاک کردن اخطار|پاک کردن اخطارها)$'), persian_unwarn))
    application.add_handler(MessageHandler(filters.Regex(r'^تعداد اخطار(\s|$)') | filters.Regex(r'^تعداد اخطار$'), persian_warns))
    application.add_handler(MessageHandler(filters.Regex(r'^اخراج(\s|$)') | filters.Regex(r'^اخراج$'), kick_command))
    
    # بازی‌ها
    application.add_handler(MessageHandler(filters.Regex(r'^بسکتبال(\s|$)') | filters.Regex(r'^بسکتبال$'), basketball_game))
    application.add_handler(MessageHandler(filters.Regex(r'^فوتبال(\s|$)') | filters.Regex(r'^فوتبال$'), football_game))
    application.add_handler(MessageHandler(filters.Regex(r'^تاس(\s|$)') | filters.Regex(r'^تاس$'), dice_game))
    application.add_handler(MessageHandler(filters.Regex(r'^لاتری(\s|$)') | filters.Regex(r'^لاتری$'), lottery_game))
    application.add_handler(MessageHandler(filters.Regex(r'^عدد شانسی(\s|$)') | filters.Regex(r'^عدد شانسی$'), lucky_number_game))
    application.add_handler(MessageHandler(filters.Regex(r'^بولینگ(\s|$)') | filters.Regex(r'^بولینگ$'), bowling_game))
    application.add_handler(MessageHandler(filters.Regex(r'^بازی‌ها(\s|$)') | filters.Regex(r'^بازی‌ها$'), games_menu))
    application.add_handler(MessageHandler(filters.Regex(r'^حذف(\s|$)') | filters.Regex(r'^حذف$'), clear_command))

    # دکمه‌ها
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # رویدادهای گروه
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_member))
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, handle_left_member))
    
    # فیلتر پیام‌ها
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    
    print("✅ ربات با موفقیت راه‌اندازی شد!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
