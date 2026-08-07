import os
import sys
import logging
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# دریافت توکن از متغیر محیطی
TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    logging.error("متغیر محیطی BOT_TOKEN تنظیم نشده است!")
    sys.exit(1)

# تنظیم logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاسخ به دستور /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"سلام {user.first_name}! 👋\n"
        "به ربات تلگرام خوش آمدی!\n\n"
        "📌 دستورات موجود:\n"
        "/start - شروع مجدد\n"
        "/help - راهنما\n"
        "/about - درباره ربات"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاسخ به دستور /help"""
    await update.message.reply_text(
        "📋 راهنمای ربات:\n\n"
        "🔹 /start - شروع کار با ربات\n"
        "🔹 /help - نمایش این پیام\n"
        "🔹 /about - اطلاعات بیشتر درباره ربات\n\n"
        "💡 هر پیامی بفرستید، ربات اکو می‌کند!"
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاسخ به دستور /about"""
    await update.message.reply_text(
        "🤖 درباره ربات:\n\n"
        "این ربات با پایتون و کتابخانه python-telegram-bot ساخته شده است.\n"
        "🛠 نسخه: 1.0.0\n"
        "📅 تاریخ ایجاد: 2024\n"
        "🚀 میزبانی شده روی Railway"
    )
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اکو کردن پیام‌های کاربر"""
    user_message = update.message.text
    user_name = update.effective_user.first_name
    
    # پاسخ‌های مختلف بر اساس محتوای پیام
    if "سلام" in user_message or "hi" in user_message.lower():
        await update.message.reply_text(f"سلام {user_name}! 😊 چطور می‌توانم کمک کنم؟")
    elif "خوب" in user_message or "great" in user_message.lower():
        await update.message.reply_text("عالیه! خوشحالم که حالت خوبه 😊")
    else:
        await update.message.reply_text(f"📩 شما گفتید: {user_message}")
        
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /ping - بررسی وضعیت ربات"""
    start_time = time.time()
    
    # ارسال پیام
    await update.message.reply_text("🏓 پینگ...")
    
    # محاسبه زمان پاسخ
    end_time = time.time()
    ping_time = round((end_time - start_time) * 1000)  # تبدیل به میلی‌ثانیه
    
    # ویرایش پیام و نمایش پینگ
    await update.message.reply_text(f"🏓 پینگ: {ping_time}ms")
    

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت خطاها"""
    logger.error(f"خطا در به‌روزرسانی {update}: {context.error}")

def main():
    """تابع اصلی برای اجرای ربات"""
    logger.info("🚀 ربات در حال راه‌اندازی...")
    
    try:
        # ایجاد اپلیکیشن
        app = Application.builder().token(TOKEN).build()

        # اضافه کردن هندلرها
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("ping", ping))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("about", about_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        
        # اضافه کردن هندلر خطا
        app.add_error_handler(error_handler)

        # شروع ربات با پولینگ
        logger.info("✅ ربات با موفقیت راه‌اندازی شد و در حال اجراست!")
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True  # پاک کردن پیام‌های قدیمی
        )
        
    except Exception as e:
        logger.error(f"❌ خطا در اجرای ربات: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
