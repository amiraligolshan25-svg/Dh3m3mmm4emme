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
    ContextTypes, CallbackQueryHandler, ChatMemberHandler
)
from telegram.constants import ParseMode
import config

# ==================== تنظیمات اولیه ====================

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
    
    # ===== مدیریت اخطارها =====
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
    
    # ===== مدیریت فیلترها =====
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
    
    # ===== مدیریت قفل‌ها =====
    def is_locked(self, chat_id: int, lock_type: str) -> bool:
        return self.data["locked"].get(str(chat_id), {}).get(lock_type, False)
    
    def set_lock(self, chat_id: int, lock_type: str, value: bool):
        if str(chat_id) not in self.data["locked"]:
            self.data["locked"][str(chat_id)] = {}
        self.data["locked"][str(chat_id)][lock_type] = value
        self._save()
    
    # ===== مدیریت پیام‌های ذخیره شده =====
    def save_message(self, chat_id: int, name: str, content: str):
        if str(chat_id) not in self.data["saved"]:
            self.data["saved"][str(chat_id)] = {}
        self.data["saved"][str(chat_id)][name] = content
        self._save()
    
    def get_saved_message(self, chat_id: int, name: str) -> Optional[str]:
        return self.data["saved"].get(str(chat_id), {}).get(name)
    
    def get_all_saved(self, chat_id: int) -> Dict:
        return self.data["saved"].get(str(chat_id), {})
    
    def delete_saved(self, chat_id: int, name: str) -> bool:
        if str(chat_id) in self.data["saved"]:
            if name in self.data["saved"][str(chat_id)]:
                del self.data["saved"][str(chat_id)][name]
                self._save()
                return True
        return False

store = DataStore()

# ==================== دکوریتورهای دسترسی ====================

def admin_only(func):
    """فقط ادمین‌های گروه میتوانند استفاده کنند"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if user_id == config.OWNER_ID:
            return await func(update, context, *args, **kwargs)
        
        # بررسی ادمین بودن در گروه
        try:
            member = await update.effective_chat.get_member(user_id)
            if member.status in ["administrator", "creator"]:
                return await func(update, context, *args, **kwargs)
        except:
            pass
        
        # بررسی ادمین سفارشی
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
    """فقط مالک ربات میتواند استفاده کند"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.id != config.OWNER_ID:
            await update.message.reply_text(
                "⛔ **دسترسی محدود!**\nاین دستور فقط برای مالک ربات است.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# ==================== ابزارهای کمکی ====================

async def get_target_user(update: Update) -> Optional[User]:
    """دریافت کاربر هدف از ریپلای یا منشن"""
    message = update.message
    
    if message.reply_to_message:
        return message.reply_to_message.from_user
    
    if message.text:
        words = message.text.split()
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
    """دریافت کاربر هدف و متن باقی‌مانده"""
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
    """تبدیل زمان به ثانیه (پشتیبانی از فارسی و انگلیسی)"""
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
    """ساخت منشن از کاربر"""
    if user.username:
        return f"@{user.username}"
    return f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"

async def is_group_admin(update: Update, user_id: int) -> bool:
    """بررسی ادمین بودن در گروه"""
    try:
        member = await update.effective_chat.get_member(user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False

# ==================== دیتابیس‌های اضافی ====================

# سیستم قود
good_data = {}

# سیستم آمار
stats_data = {}

# سیستم آنتی‌اسپم
spam_counter = {}

# سیستم تاخیر
last_message_time = {}

# ==================== دستورات عمومی ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع"""
    user = update.effective_user
    is_owner = user.id == config.OWNER_ID
    
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
    """دستور راهنما"""
    user_id = update.effective_user.id
    is_admin = await is_group_admin(update, user_id)
    is_owner = user_id == config.OWNER_ID
    
    text = "🛠 **راهنمای کامل ربات**\n\n"
    text += "📌 **دستورات عمومی:**\n"
    text += "• `آمار` - اطلاعات کاربر (با ریپلی یا منشن)\n"
    text += "• `آیدی` - آیدی عددی کاربر\n"
    text += "• `قوانین` - نمایش قوانین\n"
    text += "• `قود` - دریافت امتیاز\n"
    text += "• `تگ ادمین/مالک` - تگ کردن\n"
    text += "• `ذخیره نام متن` - ذخیره پیام\n"
    text += "• `دریافت نام` - دریافت پیام ذخیره شده\n\n"
    
    if is_admin or is_owner:
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
    
    if is_owner:
        text += "👑 **دستورات مالک:**\n"
        text += "• `عضویت اجباری روشن/خاموش`\n"
        text += "• `عضویت اجباری افزودن @channel`\n"
        text += "• `عضویت اجباری حذف @channel`\n"
        text += "• `نظرسنجی رندوم فعال/غیرفعال`\n"
        text += "• `نظرسنجی رندوم سوال متن`\n\n"
    
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

# ==================== دستورات آمار و آیدی ====================

async def ammar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش اطلاعات کاربر"""
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
    
    # دریافت قود
    key = f"{chat.id}:{target.id}"
    good_total = good_data.get(key, {}).get("total", 0)
    
    text = f"📊 **آمار کاربر**\n\n"
    text += f"👤 نام: {target.full_name}\n"
    text += f"🆔 آیدی: `{target.id}`\n"
    text += f"👤 یوزرنیم: @{target.username if target.username else 'ندارد'}\n"
    text += f"📊 وضعیت: {status_map.get(status, status)}\n"
    text += f"⚠️ اخطارها: {warn_count} از {config.WARN_LIMIT}\n"
    text += f"⭐ قود: {good_total}"
    
    if target.is_bot:
        text += f"\n🤖 این کاربر یک ربات است."
    
    if status in ["administrator", "creator"]:
        text += f"\n\n🔰 این کاربر ادمین گروه است."
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آیدی عددی کاربر"""
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
    """نمایش قوانین گروه"""
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

# ==================== سیستم قود ====================

async def good_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت قود - هر ۱۰ دقیقه"""
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

# ==================== سیستم ذخیره ====================

@admin_only
async def save_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ذخیره پیام"""
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
    
    await update.message.reply_text(
        f"✅ **پیام با نام '{name}' ذخیره شد.**",
        parse_mode=ParseMode.MARKDOWN
    )

async def get_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت پیام ذخیره شده"""
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

@admin_only
async def saved_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لیست پیام‌های ذخیره شده"""
    chat_id = update.effective_chat.id
    items = store.get_all_saved(chat_id)
    
    if items:
        text = "📋 **لیست پیام‌های ذخیره شده:**\n\n"
        for name, content in items.items():
            text += f"• `{name}`: {content[:30]}...\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("📭 هیچ پیامی ذخیره نشده است.")

# ==================== سیستم تگ ====================

async def tag_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تگ کردن کاربران"""
    chat = update.effective_chat
    text = update.message.text
    
    if len(text.split()) < 2:
        await update.message.reply_text(
            "❗ **نحوه استفاده:**\n"
            "`تگ ادمین` - تگ ادمین‌ها\n"
            "`تگ مالک` - تگ مالک\n"
            "`تگ کل` - تگ همه (فقط ادمین)",
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
        owner_id = config.OWNER_ID
        try:
            owner = await context.bot.get_chat(owner_id)
            username = f"@{owner.username}" if owner.username else f"[{owner.full_name}](tg://user?id={owner_id})"
            await update.message.reply_text(
                f"👑 **مالک ربات:**\n{username}",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            await update.message.reply_text(f"👑 آیدی مالک: `{owner_id}`", parse_mode=ParseMode.MARKDOWN)
    
    elif tag_type == "کل":
        if not await is_group_admin(update, update.effective_user.id):
            await update.message.reply_text("⛔ فقط ادمین‌ها می‌توانند همه را تگ کنند.")
            return
        
        await update.message.reply_text(
            "📢 **تگ همه اعضا**\n"
            "این قابلیت به دلیل جلوگیری از اسپم محدود شده است.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    else:
        await update.message.reply_text(
            f"❌ نوع تگ '{tag_type}' نامعتبر است.\n"
            "انواع مجاز: `ادمین`, `مالک`, `کل`",
            parse_mode=ParseMode.MARKDOWN
        )

# ==================== سیستم آمار گروه ====================

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار گروه"""
    chat_id = update.effective_chat.id
    text = update.message.text
    
    stats_type = "روزانه"
    if len(text.split()) > 1:
        stats_type = text.split(maxsplit=1)[1].strip()
    
    chat_stats = stats_data.get(str(chat_id), {})
    
    if stats_type == "روزانه":
        today = datetime.now().strftime("%Y-%m-%d")
        daily = chat_stats.get("daily", {}).get(today, {})
        
        text = f"📊 **آمار روزانه** ({today})\n\n"
        text += f"💬 پیام‌ها: {daily.get('messages', 0)}\n"
        text += f"👤 کاربران فعال: {daily.get('active_users', 0)}"
    
    elif stats_type == "هفتگی":
        week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d")
        weekly = chat_stats.get("weekly", {}).get(week_start, {})
        
        text = f"📊 **آمار هفتگی** (هفته {datetime.now().isocalendar()[1]})\n\n"
        text += f"💬 پیام‌ها: {weekly.get('messages', 0)}\n"
        text += f"👤 کاربران جدید: {weekly.get('new_users', 0)}"
    
    elif stats_type == "کل":
        total = chat_stats.get("total", {})
        
        text = f"📊 **آمار کلی گروه**\n\n"
        text += f"💬 کل پیام‌ها: {total.get('messages', 0)}\n"
        text += f"📅 تاریخ ایجاد: {total.get('created', 'نامشخص')}"
    
    else:
        await update.message.reply_text(
            f"❌ نوع آمار '{stats_type}' نامعتبر است.\n"
            "انواع مجاز: `روزانه`, `هفتگی`, `کل`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ==================== دستورات مدیریتی فارسی ====================

@admin_only
async def persian_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بن کردن کاربر"""
    target = await get_target_user(update)
    
    if not target:
        await update.message.reply_text(
            "❗ روی پیام کاربر ریپلی بزنید یا بنویسید `بن @username`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if target.id == update.effective_user.id:
        await update.message.reply_text("🙃 نمی‌تونی خودتو بن کنی!")
        return
    
    if target.id == config.OWNER_ID:
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
        
        keyboard = [[
            InlineKeyboardButton("🔓 رفع بن", callback_data=f"unban_{target.id}")
        ]]
        await update.message.reply_text(
            f"🚫 کاربر {get_user_mention(target)} **بن** شد.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

@admin_only
async def persian_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رفع بن کاربر"""
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
        await update.message.reply_text(
            "❗ روی پیام کاربر ریپلی بزنید یا بنویسید `آن بن @username`",
            parse_mode=ParseMode.MARKDOWN
        )
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
    """سکوت کاربر"""
    target, remaining_text = await get_target_user_with_args(update)
    
    if not target:
        await update.message.reply_text(
            "❗ روی پیام کاربر ریپلی بزنید یا بنویسید `سکوت @username 10m`",
            parse_mode=ParseMode.MARKDOWN
        )
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
    """رفع سکوت کاربر"""
    target = await get_target_user(update)
    
    if not target:
        await update.message.reply_text(
            "❗ روی پیام کاربر ریپلی بزنید یا بنویسید `رفع سکوت @username`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        await update.effective_chat.restrict_member(
            target.id,
            ChatPermissions(
                can_send_messages=True,
                can_send_media=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_send_polls=True,
                can_change_info=True,
                can_invite_users=True,
                can_pin_messages=True
            )
        )
        await update.message.reply_text(
            f"🔊 سکوت کاربر {get_user_mention(target)} **برداشته شد**.",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

# ==================== سیستم اخطار ====================

@admin_only
async def persian_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اخطار به کاربر"""
    target, reason = await get_target_user_with_args(update)
    
    if not target:
        await update.message.reply_text(
            "❗ روی پیام کاربر ریپلی بزنید یا بنویسید `اخطار @username دلیل`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if target.id == update.effective_user.id:
        await update.message.reply_text("🙃 نمی‌تونی به خودت اخطار بدی!")
        return
    
    if target.id == config.OWNER_ID:
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
        f"📊 تعداد اخطارها: **{warn_count}** از {config.WARN_LIMIT}\n"
        f"📝 دلیل: {reason}\n"
        f"👮 اخطاردهنده: {get_user_mention(update.effective_user)}"
    )
    
    keyboard = [[
        InlineKeyboardButton("📋 مشاهده اخطارها", callback_data=f"view_warns_{target.id}"),
        InlineKeyboardButton("🗑 پاک کردن اخطارها", callback_data=f"clear_warns_{target.id}")
    ]]
    
    await update.message.reply_text(
        warn_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    try:
        await context.bot.send_message(
            chat_id=target.id,
            text=f"⚠️ شما در گروه {update.effective_chat.title} اخطار دریافت کردید!\n"
                 f"📊 تعداد اخطارها: {warn_count}/{config.WARN_LIMIT}\n"
                 f"📝 دلیل: {reason}"
        )
    except:
        pass
    
    if warn_count >= config.WARN_LIMIT:
        try:
            until_date = datetime.now() + timedelta(seconds=config.MUTE_DURATION)
            await update.effective_chat.restrict_member(
                target.id,
                ChatPermissions(can_send_messages=False),
                until_date=until_date
            )
            
            await update.message.reply_text(
                f"🚫 **کاربر {get_user_mention(target)} به صورت خودکار سکوت شد!**\n"
                f"⏱ مدت: {config.MUTE_DURATION//60} دقیقه",
                parse_mode=ParseMode.HTML
            )
            
            store.clear_warns(chat_id, target.id)
        except Exception as e:
            await update.message.reply_text(f"❌ خطا: {str(e)}")

@admin_only
async def persian_unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک کردن اخطارها"""
    target = await get_target_user(update)
    
    if not target:
        await update.message.reply_text(
            "❗ روی پیام کاربر ریپلی بزنید یا بنویسید `پاک کردن اخطار @username`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    chat_id = update.effective_chat.id
    old_count = store.get_warns(chat_id, target.id)
    
    if old_count == 0:
        await update.message.reply_text(
            f"✅ کاربر {get_user_mention(target)} اخطاری ندارد!",
            parse_mode=ParseMode.HTML
        )
        return
    
    store.clear_warns(chat_id, target.id)
    await update.message.reply_text(
        f"✅ **تمام {old_count} اخطار** کاربر {get_user_mention(target)} پاک شد.",
        parse_mode=ParseMode.HTML
    )

@admin_only
async def persian_warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مشاهده اخطارها"""
    target = await get_target_user(update)
    if not target:
        target = update.effective_user
    
    chat_id = update.effective_chat.id
    warn_count = store.get_warns(chat_id, target.id)
    
    is_admin = await is_group_admin(update, target.id)
    status_emoji = "👑" if target.id == config.OWNER_ID else "🛡" if is_admin else "👤"
    
    text = (
        f"{status_emoji} **اطلاعات اخطارهای کاربر**\n\n"
        f"👤 کاربر: {get_user_mention(target)}\n"
        f"🆔 آیدی: `{target.id}`\n"
        f"📊 تعداد اخطارها: **{warn_count}** از {config.WARN_LIMIT}\n"
    )
    
    if warn_count == 0:
        text += "\n✅ این کاربر اخطاری ندارد."
    elif warn_count < config.WARN_LIMIT:
        remaining = config.WARN_LIMIT - warn_count
        text += f"\n⚠️ تا سکوت خودکار {remaining} اخطار دیگر باقی است."
    else:
        text += "\n🚫 این کاربر به دلیل اخطار زیاد سکوت شده است."
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ==================== سیستم اخراج ====================

@admin_only
async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اخراج کاربر"""
    target = await get_target_user(update)
    
    if not target:
        await update.message.reply_text(
            "❗ روی پیام کاربر ریپلی بزنید یا بنویسید `اخراج @username`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if target.id == update.effective_user.id:
        await update.message.reply_text("🙃 نمی‌تونی خودتو اخراج کنی!")
        return
    
    if target.id == config.OWNER_ID:
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
    """افزودن فیلتر"""
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
    """حذف فیلتر"""
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

@admin_only
async def filters_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لیست فیلترها"""
    chat_id = update.effective_chat.id
    filters = store.get_filters(chat_id)
    
    if not filters:
        await update.message.reply_text("📭 هیچ فیلتری تعریف نشده.")
        return
    
    text = "📋 **لیست فیلترها:**\n\n"
    for word, reply in filters.items():
        text += f"• `{word}` → {reply[:30]}...\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ==================== سیستم قفل پیشرفته ====================

@admin_only
async def advanced_lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قفل پیشرفته"""
    chat_id = update.effective_chat.id
    text = update.message.text
    
    if len(text.split()) < 2:
        await update.message.reply_text(
            "❗ **نحوه استفاده:**\n"
            "`قفل عکس` - قفل عکس\n"
            "`قفل ویدیو` - قفل ویدیو\n"
            "`قفل صدا` - قفل صدا\n"
            "`قفل استیکر` - قفل استیکر\n"
            "`قفل ایموجی` - قفل ایموجی\n"
            "`قفل متن` - قفل متن\n"
            "`قفل لینک` - قفل لینک\n"
            "`قفل منشن` - قفل منشن\n"
            "`قفل همه` - قفل همه\n"
            "`قفل حذف نوع` - حذف قفل",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    action = text.split(maxsplit=1)[1].strip()
    lock_types = ["عکس", "ویدیو", "صدا", "استیکر", "ایموجی", "متن", "لینک", "منشن", "همه"]
    
    if action.startswith("حذف"):
        lock_name = action.split(maxsplit=1)[1] if len(action.split()) > 1 else ""
        if lock_name in lock_types:
            store.set_lock(chat_id, lock_name, False)
            await update.message.reply_text(f"🔓 **قفل {lock_name} برداشته شد.**")
        else:
            await update.message.reply_text(f"❌ نوع قفل '{lock_name}' نامعتبر است.")
        return
    
    if action in lock_types:
        store.set_lock(chat_id, action, True)
        await update.message.reply_text(f"🔒 **قفل {action} فعال شد.**")
    else:
        await update.message.reply_text(
            f"❌ نوع قفل '{action}' نامعتبر است.\n"
            f"انواع مجاز: {', '.join(lock_types)}",
            parse_mode=ParseMode.MARKDOWN
        )

# ==================== سیستم مدیریت ادمین ====================

@admin_only
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """افزودن مدیر با پنل"""
    target = await get_target_user(update)
    
    if not target:
        await update.message.reply_text(
            "❗ روی پیام کاربری که می‌خواهید مدیر کنید ریپلی بزنید و بنویسید `مدیر`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if target.id == config.OWNER_ID:
        await update.message.reply_text("👑 کاربر مورد نظر مالک ربات است.")
        return
    
    keyboard = [
        [InlineKeyboardButton("👤 مدیریت کاربران", callback_data=f"admin_perm_users_{target.id}")],
        [InlineKeyboardButton("📝 مدیریت پیام‌ها", callback_data=f"admin_perm_messages_{target.id}")],
        [InlineKeyboardButton("🔒 مدیریت قفل‌ها", callback_data=f"admin_perm_locks_{target.id}")],
        [InlineKeyboardButton("⚠️ مدیریت اخطارها", callback_data=f"admin_perm_warns_{target.id}")],
        [InlineKeyboardButton("📊 مشاهده آمار", callback_data=f"admin_perm_stats_{target.id}")],
        [InlineKeyboardButton("🎮 مدیریت بازی‌ها", callback_data=f"admin_perm_games_{target.id}")],
        [InlineKeyboardButton("✅ همه قابلیت‌ها", callback_data=f"admin_perm_all_{target.id}")],
        [InlineKeyboardButton("❌ لغو", callback_data="close")]
    ]
    
    chat_id = str(update.effective_chat.id)
    if chat_id not in store.data["custom_admins"]:
        store.data["custom_admins"][chat_id] = {}
    
    await update.message.reply_text(
        f"👤 **افزودن مدیر: {target.full_name}**\n\n"
        f"قابلیت‌های مدیری که می‌خواهید به این کاربر بدهید را انتخاب کنید:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@admin_only
async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف مدیر"""
    target = await get_target_user(update)
    
    if not target:
        await update.message.reply_text(
            "❗ روی پیام کاربری که می‌خواهید مدیر را از او بردارید ریپلی بزنید و بنویسید `حذف مدیر`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    chat_id = str(update.effective_chat.id)
    
    if chat_id in store.data["custom_admins"] and target.id in store.data["custom_admins"][chat_id]:
        del store.data["custom_admins"][chat_id][target.id]
        store._save()
        
        await update.message.reply_text(
            f"✅ **قابلیت‌های مدیری کاربر {get_user_mention(target)} حذف شد.**",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            f"❌ کاربر {get_user_mention(target)} مدیر نیست.",
            parse_mode=ParseMode.HTML
        )

# ==================== سیستم عضویت اجباری ====================

@admin_only
async def force_join_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فعال کردن عضویت اجباری"""
    chat_id = str(update.effective_chat.id)
    
    if "force_join" not in store.data:
        store.data["force_join"] = {}
    
    store.data["force_join"][chat_id] = {
        "enabled": True,
        "channels": store.data["force_join"].get(chat_id, {}).get("channels", [])
    }
    store._save()
    
    await update.message.reply_text("✅ **عضویت اجباری فعال شد.**")

@admin_only
async def force_join_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """غیرفعال کردن عضویت اجباری"""
    chat_id = str(update.effective_chat.id)
    
    if "force_join" in store.data and chat_id in store.data["force_join"]:
        store.data["force_join"][chat_id]["enabled"] = False
        store._save()
        await update.message.reply_text("❌ **عضویت اجباری غیرفعال شد.**")
    else:
        await update.message.reply_text("⚠️ عضویت اجباری فعال نیست.")

@admin_only
async def force_join_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """افزودن کانال به لیست عضویت اجباری"""
    if not context.args:
        await update.message.reply_text(
            "❗ **نحوه استفاده:**\n"
            "`عضویت اجباری افزودن @channel`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    chat_id = str(update.effective_chat.id)
    channel_input = context.args[0]
    
    if channel_input.startswith("@"):
        channel_input = channel_input[1:]
    
    try:
        channel = await context.bot.get_chat(channel_input)
        channel_id = channel.id
        channel_name = channel.title
    except:
        await update.message.reply_text("❌ کانال یا گروه پیدا نشد.")
        return
    
    if "force_join" not in store.data:
        store.data["force_join"] = {}
    
    if chat_id not in store.data["force_join"]:
        store.data["force_join"][chat_id] = {
            "enabled": False,
            "channels": []
        }
    
    if channel_id in store.data["force_join"][chat_id]["channels"]:
        await update.message.reply_text("⚠️ این کانال قبلاً اضافه شده است.")
        return
    
    store.data["force_join"][chat_id]["channels"].append(channel_id)
    store._save()
    
    await update.message.reply_text(
        f"✅ **کانال {channel_name}** به لیست عضویت اجباری اضافه شد.",
        parse_mode=ParseMode.MARKDOWN
    )

@admin_only
async def force_join_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف کانال از لیست عضویت اجباری"""
    if not context.args:
        await update.message.reply_text(
            "❗ **نحوه استفاده:**\n"
            "`عضویت اجباری حذف @channel`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    chat_id = str(update.effective_chat.id)
    channel_input = context.args[0]
    
    if channel_input.startswith("@"):
        channel_input = channel_input[1:]
    
    try:
        channel = await context.bot.get_chat(channel_input)
        channel_id = channel.id
    except:
        try:
            channel_id = int(channel_input)
        except:
            await update.message.reply_text("❌ کانال پیدا نشد.")
            return
    
    if "force_join" not in store.data or chat_id not in store.data["force_join"]:
        await update.message.reply_text("⚠️ عضویت اجباری فعال نیست.")
        return
    
    if channel_id not in store.data["force_join"][chat_id]["channels"]:
        await update.message.reply_text("⚠️ این کانال در لیست نیست.")
        return
    
    store.data["force_join"][chat_id]["channels"].remove(channel_id)
    store._save()
    
    await update.message.reply_text(f"✅ کانال با آیدی `{channel_id}` از لیست حذف شد.", parse_mode=ParseMode.MARKDOWN)

# ==================== بازی‌ها ====================

async def basketball_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازی بسکتبال"""
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
    
    keyboard = [[
        InlineKeyboardButton("🔄 دوباره پرتاب", callback_data="game_basketball"),
        InlineKeyboardButton("🎲 بازی دیگر", callback_data="games_menu")
    ]]
    
    await update.message.reply_text(
        f"🏀 **بازی بسکتبال**\n\n"
        f"👤 {user.full_name} پرتاب کرد!\n\n"
        f"{result}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def football_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازی فوتبال"""
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
    
    keyboard = [[
        InlineKeyboardButton("⚽ پنالتی جدید", callback_data="game_football"),
        InlineKeyboardButton("🎲 بازی دیگر", callback_data="games_menu")
    ]]
    
    await update.message.reply_text(
        f"⚽ **بازی فوتبال - پنالتی**\n\n"
        f"👤 {user.full_name} ضربه زد!\n\n"
        f"{result}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def dice_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازی تاس"""
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
    
    keyboard = [[
        InlineKeyboardButton("🎲 پرتاب دوباره", callback_data="game_dice"),
        InlineKeyboardButton("🎲 بازی دیگر", callback_data="games_menu")
    ]]
    
    await update.message.reply_text(
        f"🎲 **بازی تاس**\n\n"
        f"👤 {user.full_name} پرتاب کرد!\n\n"
        f"{dice_emojis[dice-1]} **عدد {dice}**\n\n"
        f"{messages[dice]}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def lottery_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازی لاتری"""
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
    
    keyboard = [[
        InlineKeyboardButton("🎰 دوباره امتحان", callback_data="game_lottery"),
        InlineKeyboardButton("🎲 بازی دیگر", callback_data="games_menu")
    ]]
    
    await update.message.reply_text(
        f"🎰 **بازی لاتری**\n\n"
        f"👤 {user.full_name}\n\n"
        f"{result}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def lucky_number_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازی عدد شانسی"""
    user = update.effective_user
    
    if not context.user_data.get('lucky_number'):
        context.user_data['lucky_number'] = random.randint(1, 100)
        context.user_data['attempts'] = 0
        context.user_data['max_attempts'] = 7
    
    target = context.user_data['lucky_number']
    attempts = context.user_data['attempts']
    max_attempts = context.user_data['max_attempts']
    
    if context.args and context.args[0].isdigit():
        guess = int(context.args[0])
        attempts += 1
        context.user_data['attempts'] = attempts
        
        if guess == target:
            msg = f"🎉 **تبریک! عدد {target} رو در {attempts} تلاش حدس زدی!** 🏆"
            context.user_data['lucky_number'] = random.randint(1, 100)
            context.user_data['attempts'] = 0
        elif guess < target:
            msg = f"📈 عدد {guess} **کوچک‌تر** از عدد مورد نظر است.\nتلاش‌های باقی‌مانده: {max_attempts - attempts}"
        else:
            msg = f"📉 عدد {guess} **بزرگ‌تر** از عدد مورد نظر است.\nتلاش‌های باقی‌مانده: {max_attempts - attempts}"
        
        if attempts >= max_attempts and guess != target:
            msg = f"😔 **باختی!** عدد مورد نظر {target} بود.\n\nبرای بازی جدید دوباره `عدد شانسی` رو بفرست."
            context.user_data['lucky_number'] = random.randint(1, 100)
            context.user_data['attempts'] = 0
    else:
        msg = (
            f"🔢 **بازی عدد شانسی**\n\n"
            f"یک عدد بین ۱ تا ۱۰۰ حدس بزن.\n"
            f"شما {max_attempts} شانس داری.\n\n"
            f"📝 مثال: `عدد شانسی ۵۰`"
        )
    
    keyboard = [[
        InlineKeyboardButton("🔄 بازی جدید", callback_data="game_lucky"),
        InlineKeyboardButton("🎲 بازی دیگر", callback_data="games_menu")
    ]]
    
    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def bowling_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازی بولینگ"""
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
    
    keyboard = [[
        InlineKeyboardButton("🎳 پرتاب دوباره", callback_data="game_bowling"),
        InlineKeyboardButton("🎲 بازی دیگر", callback_data="games_menu")
    ]]
    
    await update.message.reply_text(
        f"🎳 **بازی بولینگ**\n\n"
        f"👤 {user.full_name} پرتاب کرد!\n\n"
        f"📊 پین‌های افتاده: **{pins}** از ۱۰\n"
        f"{emoji}\n\n"
        f"{messages[pins]}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی بازی‌ها"""
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
        "🎮 **منوی بازی‌ها**\n\n"
        "یک بازی رو انتخاب کن! 😊",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== سیستم نظرسنجی رندوم ====================

# دیتابیس نظرسنجی‌های رندوم
poll_data = {}

@admin_only
async def random_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت نظرسنجی رندوم"""
    chat_id = str(update.effective_chat.id)
    text = update.message.text
    
    if chat_id not in poll_data:
        poll_data[chat_id] = {"enabled": False, "questions": []}
    
    if len(text.split()) < 2:
        status = "فعال" if poll_data[chat_id]["enabled"] else "غیرفعال"
        await update.message.reply_text(
            f"📊 **وضعیت نظرسنجی رندوم:** {status}\n\n"
            f"برای فعال کردن: `نظرسنجی رندوم فعال`\n"
            f"برای غیرفعال کردن: `نظرسنجی رندوم غیرفعال`\n"
            f"برای افزودن سوال: `نظرسنجی رندوم سوال متن؟`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    action = text.split(maxsplit=2)[1] if len(text.split()) > 2 else text.split(maxsplit=1)[1]
    
    if action == "فعال":
        poll_data[chat_id]["enabled"] = True
        await update.message.reply_text("✅ **نظرسنجی رندوم فعال شد.**")
    
    elif action == "غیرفعال":
        poll_data[chat_id]["enabled"] = False
        await update.message.reply_text("❌ **نظرسنجی رندوم غیرفعال شد.**")
    
    elif action == "سوال" and len(text.split()) > 2:
        question = text.split(maxsplit=2)[2]
        poll_data[chat_id]["questions"].append(question)
        await update.message.reply_text(f"✅ **سوال اضافه شد:**\n{question}")
    
    else:
        await update.message.reply_text(
            f"❌ دستور '{action}' نامعتبر است.\n"
            "استفاده: `نظرسنجی رندوم فعال/غیرفعال/سوال`",
            parse_mode=ParseMode.MARKDOWN
        )

# ==================== سیستم گزارش ====================

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """گزارش تخلف"""
    target = await get_target_user(update)
    reporter = update.effective_user
    chat = update.effective_chat
    
    _, reason = await get_target_user_with_args(update)
    
    if not reason:
        reason = "بدون دلیل"
    
    report_text = (
        f"🚨 **گزارش تخلف جدید**\n\n"
        f"👤 گزارش‌دهنده: {get_user_mention(reporter)}\n"
        f"👤 متخلف: {get_user_mention(target) if target else 'نامشخص'}\n"
        f"📝 دلیل: {reason}\n"
        f"🆔 آیدی متخلف: `{target.id if target else 'نامشخص'}`\n"
        f"📅 زمان: {datetime.now().strftime('%Y/%m/%d %H:%M')}\n"
        f"🔗 گروه: {chat.title}"
    )
    
    keyboard = [[
        InlineKeyboardButton("⛔ بن", callback_data=f"report_ban_{target.id if target else 0}"),
        InlineKeyboardButton("🔇 سکوت", callback_data=f"report_mute_{target.id if target else 0}"),
        InlineKeyboardButton("⚠️ اخطار", callback_data=f"report_warn_{target.id if target else 0}"),
        InlineKeyboardButton("❌ بستن", callback_data="report_close")
    ]]
    
    admins = []
    try:
        async for member in chat.get_administrators():
            if not member.user.is_bot:
                admins.append(member.user.id)
    except:
        pass
    
    for admin_id in admins:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=report_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except:
            pass
    
    await update.message.reply_text(
        "✅ **گزارش شما ثبت شد.**\nادمین‌ها در اسرع وقت بررسی می‌کنند.",
        parse_mode=ParseMode.MARKDOWN
    )

# ==================== سیستم تیکت ====================

tickets = {}

async def ticket_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """سیستم تیکت"""
    user = update.effective_user
    chat = update.effective_chat
    
    text = update.message.text
    if len(text.split()) < 2:
        await update.message.reply_text(
            "❗ **نحوه استفاده:**\n"
            "`تیکت متن مشکل خود را بنویسید`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    ticket_text = " ".join(text.split()[1:])
    ticket_id = len(tickets) + 1
    
    tickets[ticket_id] = {
        "id": ticket_id,
        "user_id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "text": ticket_text,
        "chat_id": chat.id,
        "status": "open",
        "created_at": datetime.now().strftime('%Y/%m/%d %H:%M'),
        "answers": []
    }
    
    keyboard = [[
        InlineKeyboardButton("📝 پاسخ", callback_data=f"ticket_answer_{ticket_id}"),
        InlineKeyboardButton("❌ بستن", callback_data=f"ticket_close_{ticket_id}")
    ]]
    
    admins = []
    try:
        async for member in chat.get_administrators():
            if not member.user.is_bot:
                admins.append(member.user.id)
    except:
        pass
    
    ticket_msg = (
        f"🎫 **تیکت جدید #{ticket_id}**\n\n"
        f"👤 کاربر: {get_user_mention(user)}\n"
        f"🆔 آیدی: `{user.id}`\n"
        f"📝 متن: {ticket_text}\n"
        f"📅 زمان: {tickets[ticket_id]['created_at']}\n"
        f"📊 وضعیت: 🟢 باز"
    )
    
    for admin_id in admins:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=ticket_msg,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except:
            pass
    
    await update.message.reply_text(
        f"✅ **تیکت شما با شماره #{ticket_id} ثبت شد.**\n"
        f"ادمین‌ها به زودی پاسخ می‌دهند.",
        parse_mode=ParseMode.MARKDOWN
    )

# ==================== دکمه‌های شیشه‌ای (Callback) ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    # ===== دکمه‌های عمومی =====
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
    
    # ===== دکمه‌های مدیریت اخطار =====
    elif data.startswith("view_warns_"):
        target_id = int(data.split("_")[2])
        if user_id != config.OWNER_ID and not await is_group_admin(update, user_id):
            await query.message.reply_text("⛔ فقط ادمین‌ها.")
            return
        
        warn_count = store.get_warns(chat_id, target_id)
        try:
            member = await update.effective_chat.get_member(target_id)
            target_user = member.user
        except:
            target_user = User(id=target_id, first_name="کاربر", is_bot=False)
        
        await query.message.reply_text(
            f"📊 کاربر {get_user_mention(target_user)} دارای **{warn_count}** اخطار است.",
            parse_mode=ParseMode.HTML
        )
    
    elif data.startswith("clear_warns_"):
        target_id = int(data.split("_")[2])
        if user_id != config.OWNER_ID and not await is_group_admin(update, user_id):
            await query.message.reply_text("⛔ فقط ادمین‌ها.")
            return
        
        old_count = store.get_warns(chat_id, target_id)
        if old_count == 0:
            await query.message.reply_text("✅ این کاربر اخطاری ندارد.")
            return
        
        store.clear_warns(chat_id, target_id)
        await query.message.reply_text(f"✅ **{old_count} اخطار** کاربر پاک شد.", parse_mode=ParseMode.MARKDOWN)
        await query.message.edit_reply_markup(reply_markup=None)
    
    # ===== دکمه‌های بن و سکوت =====
    elif data.startswith("unban_"):
        target_id = int(data.split("_")[1])
        if user_id != config.OWNER_ID and not await is_group_admin(update, user_id):
            await query.message.reply_text("⛔ فقط ادمین‌ها.")
            return
        
        try:
            await update.effective_chat.unban_member(target_id)
            await query.message.reply_text(f"✅ کاربر با آیدی `{target_id}` آنبن شد.", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await query.message.reply_text(f"❌ خطا: {str(e)}")
    
    elif data.startswith("unmute_"):
        target_id = int(data.split("_")[1])
        if user_id != config.OWNER_ID and not await is_group_admin(update, user_id):
            await query.message.reply_text("⛔ فقط ادمین‌ها.")
            return
        
        try:
            await update.effective_chat.restrict_member(
                target_id,
                ChatPermissions(
                    can_send_messages=True,
                    can_send_media=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                    can_send_polls=True,
                    can_change_info=True,
                    can_invite_users=True,
                    can_pin_messages=True
                )
            )
            await query.message.reply_text(f"🔊 میوت کاربر با آیدی `{target_id}` برداشته شد.", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await query.message.reply_text(f"❌ خطا: {str(e)}")
    
    # ===== دکمه‌های بازی‌ها =====
    elif data.startswith("game_"):
        game = data.replace("game_", "")
        
        # شبیه‌سازی دستور بازی
        class FakeUpdate:
            def __init__(self, original_update, message):
                self.effective_user = original_update.effective_user
                self.effective_chat = original_update.effective_chat
                self.message = message
        
        fake_message = type('obj', (object,), {
            'reply_text': query.message.reply_text,
            'text': game
        })()
        
        fake_update = FakeUpdate(update, fake_message)
        
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
    
    # ===== دکمه‌های مدیریت ادمین =====
    elif data.startswith("admin_perm_"):
        parts = data.split("_")
        perm = parts[2]
        target_id = int(parts[3])
        
        if user_id != config.OWNER_ID and not await is_group_admin(update, user_id):
            await query.message.reply_text("⛔ فقط ادمین‌ها.")
            return
        
        chat_id_str = str(update.effective_chat.id)
        if chat_id_str not in store.data["custom_admins"]:
            store.data["custom_admins"][chat_id_str] = {}
        
        if target_id not in store.data["custom_admins"][chat_id_str]:
            store.data["custom_admins"][chat_id_str][target_id] = []
        
        if perm == "all":
            store.data["custom_admins"][chat_id_str][target_id] = ["users", "messages", "locks", "warns", "stats", "games"]
            await query.message.reply_text(f"✅ **همه قابلیت‌ها** به کاربر داده شد.")
        else:
            if perm not in store.data["custom_admins"][chat_id_str][target_id]:
                store.data["custom_admins"][chat_id_str][target_id].append(perm)
                await query.message.reply_text(f"✅ قابلیت **{perm}** اضافه شد.")
            else:
                await query.message.reply_text(f"⚠️ این قابلیت قبلاً اضافه شده است.")
        
        store._save()
        await query.message.edit_reply_markup(reply_markup=None)
    
    # ===== دکمه‌های گزارش =====
    elif data.startswith("report_"):
        action = data.split("_")[1]
        target_id = int(data.split("_")[2]) if len(data.split("_")) > 2 else 0
        
        if user_id != config.OWNER_ID and not await is_group_admin(update, user_id):
            await query.message.reply_text("⛔ فقط ادمین‌ها.")
            return
        
        if action == "close":
            await query.message.delete()
            return
        
        if target_id == 0:
            await query.message.reply_text("❌ کاربر نامشخص است.")
            return
        
        try:
            if action == "ban":
                await update.effective_chat.ban_member(target_id)
                await query.message.reply_text(f"✅ کاربر با آیدی `{target_id}` بن شد.")
            elif action == "mute":
                await update.effective_chat.restrict_member(
                    target_id,
                    ChatPermissions(can_send_messages=False)
                )
                await query.message.reply_text(f"✅ کاربر با آیدی `{target_id}` سکوت شد.")
            elif action == "warn":
                chat_id_int = update.effective_chat.id
                store.add_warn(chat_id_int, target_id)
                await query.message.reply_text(f"✅ به کاربر با آیدی `{target_id}` اخطار داده شد.")
            elif action == "view":
                warn_count = store.get_warns(update.effective_chat.id, target_id)
                await query.message.reply_text(f"📊 کاربر با آیدی `{target_id}` دارای {warn_count} اخطار است.")
        except Exception as e:
            await query.message.reply_text(f"❌ خطا: {str(e)}")
    
    # ===== دکمه‌های تیکت =====
    elif data.startswith("ticket_"):
        action = data.split("_")[1]
        ticket_id = int(data.split("_")[2])
        
        if ticket_id not in tickets:
            await query.message.reply_text("❌ تیکت پیدا نشد.")
            return
        
        if user_id != config.OWNER_ID and not await is_group_admin(update, user_id):
            await query.message.reply_text("⛔ فقط ادمین‌ها.")
            return
        
        if action == "close":
            tickets[ticket_id]["status"] = "closed"
            await query.message.reply_text(f"✅ تیکت #{ticket_id} بسته شد.")
            await query.message.edit_reply_markup(reply_markup=None)
        
        elif action == "answer":
            await query.message.reply_text(
                f"📝 **پاسخ به تیکت #{ticket_id}**\n\n"
                f"متن پاسخ را به صورت `/answer {ticket_id} متن` بفرستید.",
                parse_mode=ParseMode.MARKDOWN
            )

# ==================== فیلتر پیام‌ها ====================

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پیام‌های دریافتی"""
    if not update.message or not update.message.text:
        return
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text
    
    # ===== بررسی قوانین =====
    if text == "قوانین" or text == "قوانین گروه":
        await ghavanin_command(update, context)
        return
    
    # ===== بررسی آنتی‌اسپم =====
    if not await check_antispam(update):
        return
    
    # ===== بررسی تاخیر =====
    if not await check_delay(update):
        return
    
    # ===== بررسی فیلترها =====
    filters = store.get_filters(chat_id)
    for word, reply in filters.items():
        if word in text.lower():
            await update.message.reply_text(reply)
            break

# ==================== آنتی‌اسپم ====================

async def check_antispam(update: Update) -> bool:
    """بررسی آنتی‌اسپم"""
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

# ==================== تاخیر ====================

async def check_delay(update: Update) -> bool:
    """بررسی تاخیر بین پیام‌ها"""
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
            await update.message.reply_text(
                f"⏳ **لطفاً ۱ ثانیه صبر کنید.**",
                parse_mode=ParseMode.MARKDOWN
            )
            return False
    
    last_message_time[key] = now
    return True

# ==================== رویدادهای گروه ====================

async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پیام خوش‌آمدگویی و بررسی عضویت اجباری"""
    if not update.message or not update.message.new_chat_members:
        return
    
    chat_id = str(update.effective_chat.id)
    
    # ===== بررسی عضویت اجباری =====
    if "force_join" in store.data and chat_id in store.data["force_join"]:
        config_fj = store.data["force_join"][chat_id]
        if config_fj.get("enabled", False):
            channels = config_fj.get("channels", [])
            
            for member in update.message.new_chat_members:
                if member.is_bot:
                    continue
                
                not_member = []
                for channel_id in channels:
                    try:
                        chat_member = await context.bot.get_chat_member(channel_id, member.id)
                        if chat_member.status == "left":
                            not_member.append(channel_id)
                    except:
                        not_member.append(channel_id)
                
                if not_member:
                    try:
                        await update.effective_chat.ban_member(member.id)
                        await update.effective_chat.unban_member(member.id)
                        
                        await update.message.reply_text(
                            f"⛔ **کاربر {get_user_mention(member)} از گروه اخراج شد.**\n"
                            f"دلیل: عضویت در کانال‌های اجباری الزامی است.",
                            parse_mode=ParseMode.HTML
                        )
                    except:
                        pass
                    return
    
    # ===== پیام خوش‌آمدگویی =====
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
    """پیام خداحافظی"""
    if not update.message or not update.message.left_chat_member:
        return
    
    member = update.message.left_chat_member
    goodbye_text = store.data["goodbye"].get(str(update.effective_chat.id))
    
    if goodbye_text:
        text = goodbye_text.replace("{user}", f"[{member.full_name}](tg://user?id={member.id})")
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ==================== دستورات مالک ====================

@owner_only
async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظیم پیام خوش‌آمدگویی"""
    if not context.args:
        await update.message.reply_text(
            "❗ **نحوه استفاده:**\n"
            "`setwelcome متن`\n"
            "از {user} برای نام کاربر استفاده کنید.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = " ".join(context.args)
    chat_id = str(update.effective_chat.id)
    store.data["welcome"][chat_id] = text
    store._save()
    
    await update.message.reply_text(f"✅ **پیام خوش‌آمدگویی تنظیم شد.**")

@owner_only
async def set_goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظیم پیام خداحافظی"""
    if not context.args:
        await update.message.reply_text(
            "❗ **نحوه استفاده:**\n"
            "`setgoodbye متن`\n"
            "از {user} برای نام کاربر استفاده کنید.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = " ".join(context.args)
    chat_id = str(update.effective_chat.id)
    store.data["goodbye"][chat_id] = text
    store._save()
    
    await update.message.reply_text(f"✅ **پیام خداحافظی تنظیم شد.**")

# ==================== تابع اصلی ====================

def main():
    """تابع اصلی اجرای ربات"""
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # ===== دستورات عمومی =====
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # ===== دستورات فارسی =====
    application.add_handler(MessageHandler(
        filters.Regex(r'^آمار(\s|$)') | filters.Regex(r'^آمار$'),
        ammar_command
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^آیدی(\s|$)') | filters.Regex(r'^آیدی$'),
        id_command
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^قوانین(\s|$)') | filters.Regex(r'^قوانین$'),
        ghavanin_command
    ))
    
    # ===== سیستم قود =====
    application.add_handler(MessageHandler(
        filters.Regex(r'^قود(\s|$)') | filters.Regex(r'^قود$'),
        good_command
    ))
    
    # ===== سیستم ذخیره =====
    application.add_handler(MessageHandler(
        filters.Regex(r'^ذخیره(\s|$)') | filters.Regex(r'^ذخیره$'),
        save_command
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^دریافت(\s|$)') | filters.Regex(r'^دریافت$'),
        get_command
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^لیست ذخیره(\s|$)') | filters.Regex(r'^لیست ذخیره$'),
        saved_list
    ))
    
    # ===== سیستم تگ =====
    application.add_handler(MessageHandler(
        filters.Regex(r'^تگ(\s|$)') | filters.Regex(r'^تگ$'),
        tag_command
    ))
    
    # ===== سیستم آمار =====
    application.add_handler(MessageHandler(
        filters.Regex(r'^آمار(\s|$)') | filters.Regex(r'^آمار$'),
        stats_command
    ))
    
    # ===== سیستم فیلتر =====
    application.add_handler(MessageHandler(
        filters.Regex(r'^فیلتر(\s|$)') | filters.Regex(r'^فیلتر$'),
        filter_add
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^حذف فیلتر(\s|$)') | filters.Regex(r'^حذف فیلتر$'),
        filter_remove
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^لیست فیلتر(\s|$)') | filters.Regex(r'^لیست فیلتر$'),
        filters_list
    ))
    
    # ===== سیستم قفل =====
    application.add_handler(MessageHandler(
        filters.Regex(r'^قفل(\s|$)') | filters.Regex(r'^قفل$'),
        advanced_lock
    ))
    
    # ===== مدیریت ادمین =====
    application.add_handler(MessageHandler(
        filters.Regex(r'^مدیر(\s|$)') | filters.Regex(r'^مدیر$'),
        add_admin
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^حذف مدیر(\s|$)') | filters.Regex(r'^حذف مدیر$'),
        remove_admin
    ))
    
    # ===== عضویت اجباری =====
    application.add_handler(MessageHandler(
        filters.Regex(r'^عضویت اجباری روشن(\s|$)') | filters.Regex(r'^عضویت اجباری روشن$'),
        force_join_on
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^عضویت اجباری خاموش(\s|$)') | filters.Regex(r'^عضویت اجباری خاموش$'),
        force_join_off
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^عضویت اجباری افزودن(\s|$)') | filters.Regex(r'^عضویت اجباری افزودن$'),
        force_join_add
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^عضویت اجباری حذف(\s|$)') | filters.Regex(r'^عضویت اجباری حذف$'),
        force_join_remove
    ))
    
    # ===== بازی‌ها =====
    application.add_handler(MessageHandler(
        filters.Regex(r'^بسکتبال(\s|$)') | filters.Regex(r'^بسکتبال$'),
        basketball_game
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^فوتبال(\s|$)') | filters.Regex(r'^فوتبال$'),
        football_game
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^تاس(\s|$)') | filters.Regex(r'^تاس$'),
        dice_game
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^لاتری(\s|$)') | filters.Regex(r'^لاتری$'),
        lottery_game
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^عدد شانسی(\s|$)') | filters.Regex(r'^عدد شانسی$'),
        lucky_number_game
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^بولینگ(\s|$)') | filters.Regex(r'^بولینگ$'),
        bowling_game
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^بازی‌ها(\s|$)') | filters.Regex(r'^بازی‌ها$'),
        games_menu
    ))
    
    # ===== نظرسنجی رندوم =====
    application.add_handler(MessageHandler(
        filters.Regex(r'^نظرسنجی رندوم(\s|$)') | filters.Regex(r'^نظرسنجی رندوم$'),
        random_poll
    ))
    
    # ===== گزارش و تیکت =====
    application.add_handler(MessageHandler(
        filters.Regex(r'^گزارش(\s|$)') | filters.Regex(r'^گزارش$'),
        report_command
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^تیکت(\s|$)') | filters.Regex(r'^تیکت$'),
        ticket_command
    ))
    
    # ===== دستورات مدیریتی =====
    application.add_handler(MessageHandler(
        filters.Regex(r'^بن(\s|$)') | filters.Regex(r'^بن$'),
        persian_ban
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^(آن بن|رفع بن)(\s|$)') | filters.Regex(r'^(آن بن|رفع بن)$'),
        persian_unban
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^سکوت(\s|$)') | filters.Regex(r'^سکوت$'),
        persian_mute
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^رفع سکوت(\s|$)') | filters.Regex(r'^رفع سکوت$'),
        persian_unmute
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^اخطار(\s|$)') | filters.Regex(r'^اخطار$'),
        persian_warn
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^(پاک کردن اخطار|پاک کردن اخطارها)(\s|$)') | 
        filters.Regex(r'^(پاک کردن اخطار|پاک کردن اخطارها)$'),
        persian_unwarn
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^تعداد اخطار(\s|$)') | filters.Regex(r'^تعداد اخطار$'),
        persian_warns
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^اخراج(\s|$)') | filters.Regex(r'^اخراج$'),
        kick_command
    ))
    
    # ===== دکمه‌های شیشه‌ای =====
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # ===== رویدادهای گروه =====
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        handle_new_member
    ))
    application.add_handler(MessageHandler(
        filters.StatusUpdate.LEFT_CHAT_MEMBER,
        handle_left_member
    ))
    
    # ===== فیلتر پیام‌ها =====
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_messages
    ))
    
    # ===== دستورات مالک =====
    application.add_handler(CommandHandler("setwelcome", set_welcome))
    application.add_handler(CommandHandler("setgoodbye", set_goodbye))
    
    # ===== شروع ربات =====
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()