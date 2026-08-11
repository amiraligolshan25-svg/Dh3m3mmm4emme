import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
import os

load_dotenv()
# ----------------- تنظیمات -----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")

# وضعیت کاربران (در حافظه)
user_data = {}

# اطلاعات پایه کشورها (واقع‌گرایانه بر اساس ۱۹۳۹-۱۹۴۵)
COUNTRIES = {
    "germany": {
        "name": "آلمان نازی",
        "leader": "آدولف هیتلر",
        "power": 95,
        "army": 3200000,
        "navy": 45,
        "airforce": 4200,
        "industry": 90,
        "nuclear": False,
        "allies": ["italy", "japan"],
        "enemies": ["soviet", "uk", "usa", "france"]
    },
    "soviet": {
        "name": "اتحاد جماهیر شوروی",
        "leader": "ژوزف استالین",
        "power": 88,
        "army": 4500000,
        "navy": 30,
        "airforce": 3800,
        "industry": 75,
        "nuclear": False,
        "allies": [],
        "enemies": ["germany"]
    },
    "usa": {
        "name": "ایالات متحده آمریکا",
        "leader": "فرانکلین روزولت",
        "power": 98,
        "army": 2800000,
        "navy": 120,
        "airforce": 5500,
        "industry": 100,
        "nuclear": True,          # از اوت ۱۹۴۵
        "allies": ["uk", "soviet"],
        "enemies": ["germany", "japan"]
    },
    "uk": {
        "name": "بریتانیا",
        "leader": "وینستون چرچیل",
        "power": 82,
        "army": 1800000,
        "navy": 95,
        "airforce": 3100,
        "industry": 70,
        "nuclear": False,
        "allies": ["usa"],
        "enemies": ["germany", "italy", "japan"]
    },
    "japan": {
        "name": "امپراتوری ژاپن",
        "leader": "هیهی‌تو",
        "power": 78,
        "army": 2500000,
        "navy": 80,
        "airforce": 2800,
        "industry": 65,
        "nuclear": False,
        "allies": ["germany", "italy"],
        "enemies": ["usa", "uk", "china"]
    },
    "italy": {
        "name": "ایتالیا",
        "leader": "بنیتو موسولینی",
        "power": 55,
        "army": 1500000,
        "navy": 40,
        "airforce": 1800,
        "industry": 45,
        "nuclear": False,
        "allies": ["germany", "japan"],
        "enemies": ["uk", "usa"]
    },
    "iran": {
        "name": "ایران",
        "leader": "رضاشاه / محمدرضا پهلوی",
        "power": 25,
        "army": 120000,
        "navy": 5,
        "airforce": 150,
        "industry": 20,
        "nuclear": False,
        "allies": [],
        "enemies": []
    }
}

# ----------------- توابع -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌍 ربات شبیه‌سازی جنگ جهانی واقعی\n\n"
        "دستورات اصلی:\n"
        "/country_set [کشور] - انتخاب کشور\n"
        "/country_info - اطلاعات کشور خودت\n"
        "/status - وضعیت کلی\n"
        "/missile [کشور] - حمله موشکی\n"
        "/atom [کشور] - حمله اتمی\n"
        "/nuclear [کشور] - حمله هسته‌ای\n"
        "/help - راهنما"
    )

async def country_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("مثال: /country_set germany")
        return

    country = context.args[0].lower()
    if country not in COUNTRIES:
        await update.message.reply_text("کشور معتبر نیست. کشورهای موجود:\n" + ", ".join(COUNTRIES.keys()))
        return

    user_data[user_id] = {"country": country}
    name = COUNTRIES[country]["name"]
    await update.message.reply_text(f"✅ کشور شما روی **{name}** تنظیم شد.")

async def country_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        await update.message.reply_text("اول کشور خودت را انتخاب کن: /country_set [کشور]")
        return

    c = COUNTRIES[user_data[user_id]["country"]]
    text = (
        f"🏳️ **{c['name']}**\n"
        f"رهبر: {c['leader']}\n"
        f"قدرت کلی: {c['power']}/100\n"
        f"ارتش: {c['army']:,} نفر\n"
        f"نیروی دریایی: {c['navy']} کشتی اصلی\n"
        f"نیروی هوایی: {c['airforce']} هواپیما\n"
        f"صنعت: {c['industry']}/100\n"
        f"سلاح هسته‌ای: {'دارد' if c['nuclear'] else 'ندارد'}\n"
        f"متحدان: {', '.join(c['allies']) or 'هیچ'}\n"
        f"دشمنان: {', '.join(c['enemies']) or 'هیچ'}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def missile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_attack(update, context, "missile")

async def atom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_attack(update, context, "atom")

async def nuclear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_attack(update, context, "nuclear")

async def handle_attack(update: Update, context: ContextTypes.DEFAULT_TYPE, attack_type: str):
    user_id = update.effective_user.id
    if user_id not in user_data:
        await update.message.reply_text("اول کشور خودت را انتخاب کن.")
        return
    if not context.args:
        await update.message.reply_text(f"مثال: /{attack_type} germany")
        return

    target = context.args[0].lower()
    if target not in COUNTRIES:
        await update.message.reply_text("کشور هدف معتبر نیست.")
        return

    my_country = user_data[user_id]["country"]
    my_data = COUNTRIES[my_country]
    target_data = COUNTRIES[target]

    if attack_type in ["atom", "nuclear"] and not my_data["nuclear"]:
        await update.message.reply_text(
            f"❌ کشور **{my_data['name']}** سلاح هسته‌ای عملیاتی ندارد.\n"
            "در دوره جنگ جهانی دوم فقط آمریکا (از اوت ۱۹۴۵) این توانایی را داشت."
        )
        return

    # شبیه‌سازی ساده و واقع‌گرایانه
    if attack_type == "missile":
        result = f"🚀 حمله موشکی از {my_data['name']} به {target_data['name']} انجام شد.\nآسیب متوسط به زیرساخت‌ها وارد شد."
    elif attack_type == "atom":
        result = (
            f"☢️ بمب اتمی روی {target_data['name']} پرتاب شد!\n"
            f"تلفات بسیار سنگین. شهر هدف تقریباً نابود شد.\n"
            f"پیامدهای سیاسی و نظامی بسیار سنگین خواهد بود."
        )
    else:
        result = (
            f"💥 حمله هسته‌ای تمام‌عیار به {target_data['name']}!\n"
            f"فاجعه انسانی و نابودی گسترده. این اقدام می‌تواند جنگ را به سطح جدیدی ببرد."
        )

    await update.message.reply_text(result)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "دستورات موجود:\n"
        "/start\n"
        "/country_set [کشور]\n"
        "/country_info\n"
        "/missile [کشور]\n"
        "/atom [کشور]\n"
        "/nuclear [کشور]\n"
        "/help"
    )

# ----------------- اجرای ربات -----------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("country_set", country_set))
    app.add_handler(CommandHandler("country_info", country_info))
    app.add_handler(CommandHandler("missile", missile))
    app.add_handler(CommandHandler("atom", atom))
    app.add_handler(CommandHandler("nuclear", nuclear))
    app.add_handler(CommandHandler("help", help_command))

    print("ربات در حال اجرا است...")
    app.run_polling()

if __name__ == "__main__":
    main()