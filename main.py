import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# توکن ربات خود را اینجا قرار دهید
TOKEN = "8975300940:AAH6mhn22Vu65FkYoJCyOIgJWU93VN1SO7g"

# تنظیم logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاسخ به دستور /start"""
    user_first_name = update.effective_user.first_name
    await update.message.reply_text(f"سلام {user_first_name}! 👋\nبه ربات خوش آمدی!")

def main():
    # ایجاد اپلیکیشن
    app = Application.builder().token(TOKEN).build()

    # اضافه کردن هندلر برای دستور /start
    app.add_handler(CommandHandler("start", start))

    # شروع ربات
    print("ربات در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
