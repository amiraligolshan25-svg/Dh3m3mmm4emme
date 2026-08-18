# ربات شبیه‌سازی جنگ جهانی واقعی - نسخه کامل
# worldwar.py

from ast import Return
from telegram.ext.filters import UpdateFilter
import json
import os
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
import time

load_dotenv()
# ----------------- تنظیمات -----------------
BOT_TOKEN = "8216900340:AAF-92j1rrF0dDFWBJZQSDBC6v_8Uz0OewI"
OWNER_ID = 8027186808
DATA_FILE = "world_war_data.json"

# ==================== داده‌های اولیه کشورها ====================
DEFAULT_COUNTRIES = {
    "germany": {
        "name": "آلمان نازی",
        "leader": "آدولف هیتلر",
        "power": 95,
        "army": 3200000,
        "economy_mode": "war",
        "industry": 92,
        "manpower": 28000000,
        "money": 8500000,
        "war_credit": 120000,
        "nuclear": False,
        "occupied_by": None,
        "at_war_with": [],
        "allies": ["italy", "japan"],
        "sanctions": [],
        "blockades": [],
        "factories": [],
        "owner_name": "هیچکس",
        "taken_by": None,
        "last_factory_collect": 0,
        "resources": {"oil": 18000, "steel": 22000, "coal": 85000, "food": 42000, "rubber": 3200, "aluminum": 1800, "uranium": 120},
        "stockpile": {"oil": 45000, "steel": 38000, "coal": 120000, "food": 65000, "rubber": 8000, "aluminum": 4500, "uranium": 280},
        "production": {"tanks": 1200, "planes": 1800, "ships": 8, "guns": 45000, "ammo": 120000},
        "equipment": {"tanks": 8500, "fighters": 4200, "ships": 95, "missiles": 180, "nukes": 0}
    },
    "usa": {
        "name": "ایالات متحده آمریکا",
        "leader": "فرانکلین روزولت",
        "power": 98,
        "army": 2800000,
        "economy_mode": "war",
        "industry": 100,
        "manpower": 65000000,
        "money": 25000000,
        "war_credit": 450000,
        "nuclear": True,
        "occupied_by": None,
        "at_war_with": [],
        "allies": ["uk", "soviet"],
        "sanctions": [],
        "blockades": [],
        "factories": [],
        "owner_name": "هیچکس",
        "taken_by": None,
        "last_factory_collect": 0,
        "resources": {"oil": 185000, "steel": 85000, "coal": 550000, "food": 180000, "rubber": 12000, "aluminum": 9500, "uranium": 850},
        "stockpile": {"oil": 320000, "steel": 150000, "coal": 700000, "food": 250000, "rubber": 28000, "aluminum": 22000, "uranium": 1600},
        "production": {"tanks": 2800, "planes": 6500, "ships": 35, "guns": 98000, "ammo": 320000},
        "equipment": {"tanks": 15000, "fighters": 12000, "ships": 280, "missiles": 320, "nukes": 3}
    },
    "soviet": {
        "name": "اتحاد جماهیر شوروی",
        "leader": "ژوزف استالین",
        "power": 88,
        "army": 4500000,
        "economy_mode": "war",
        "industry": 78,
        "manpower": 95000000,
        "money": 6200000,
        "war_credit": 95000,
        "nuclear": False,
        "occupied_by": None,
        "at_war_with": [],
        "allies": [],
        "sanctions": [],
        "blockades": [],
        "factories": [],
        "owner_name": "هیچکس",
        "taken_by": None,
        "last_factory_collect": 0,
        "resources": {"oil": 95000, "steel": 42000, "coal": 180000, "food": 78000, "rubber": 1800, "aluminum": 3200, "uranium": 420},
        "stockpile": {"oil": 140000, "steel": 65000, "coal": 250000, "food": 95000, "rubber": 3500, "aluminum": 5800, "uranium": 780},
        "production": {"tanks": 2200, "planes": 3100, "ships": 6, "guns": 72000, "ammo": 210000},
        "equipment": {"tanks": 18000, "fighters": 7500, "ships": 45, "missiles": 90, "nukes": 0}
    },
    "uk": {
        "name": "بریتانیا",
        "leader": "وینستون چرچیل",
        "power": 82,
        "army": 1800000,
        "economy_mode": "war",
        "industry": 72,
        "manpower": 22000000,
        "money": 9800000,
        "war_credit": 180000,
        "nuclear": False,
        "occupied_by": None,
        "at_war_with": [],
        "allies": ["usa"],
        "sanctions": [],
        "blockades": [],
        "factories": [],
        "owner_name": "هیچکس",
        "taken_by": None,
        "last_factory_collect": 0,
        "resources": {"oil": 12000, "steel": 18000, "coal": 210000, "food": 28000, "rubber": 4500, "aluminum": 2100, "uranium": 90},
        "stockpile": {"oil": 35000, "steel": 28000, "coal": 280000, "food": 42000, "rubber": 9000, "aluminum": 4800, "uranium": 160},
        "production": {"tanks": 650, "planes": 2200, "ships": 18, "guns": 38000, "ammo": 95000},
        "equipment": {"tanks": 4200, "fighters": 5100, "ships": 210, "missiles": 140, "nukes": 0}
    },
    "japan": {
        "name": "امپراتوری ژاپن",
        "leader": "هیروهیتو",
        "power": 78,
        "army": 2500000,
        "economy_mode": "war",
        "industry": 68,
        "manpower": 32000000,
        "money": 5100000,
        "war_credit": 78000,
        "nuclear": False,
        "occupied_by": None,
        "at_war_with": [],
        "allies": ["germany", "italy"],
        "sanctions": [],
        "blockades": [],
        "factories": [],
        "owner_name": "هیچکس",
        "taken_by": None,
        "last_factory_collect": 0,
        "resources": {"oil": 8500, "steel": 9500, "coal": 42000, "food": 38000, "rubber": 2800, "aluminum": 1100, "uranium": 45},
        "stockpile": {"oil": 18000, "steel": 15000, "coal": 55000, "food": 48000, "rubber": 5500, "aluminum": 2400, "uranium": 80},
        "production": {"tanks": 280, "planes": 1600, "ships": 12, "guns": 22000, "ammo": 65000},
        "equipment": {"tanks": 2800, "fighters": 3800, "ships": 160, "missiles": 70, "nukes": 0}
    },
    "italy": {
        "name": "ایتالیا",
        "leader": "بنیتو موسولینی",
        "power": 55,
        "army": 1500000,
        "economy_mode": "war",
        "industry": 48,
        "manpower": 18000000,
        "money": 3200000,
        "war_credit": 42000,
        "nuclear": False,
        "occupied_by": None,
        "at_war_with": [],
        "allies": ["germany", "japan"],
        "sanctions": [],
        "blockades": [],
        "factories": [],
        "owner_name": "هیچکس",
        "taken_by": None,
        "last_factory_collect": 0,
        "resources": {"oil": 4500, "steel": 6200, "coal": 18000, "food": 22000, "rubber": 900, "aluminum": 650, "uranium": 20},
        "stockpile": {"oil": 9000, "steel": 11000, "coal": 28000, "food": 30000, "rubber": 1800, "aluminum": 1200, "uranium": 35},
        "production": {"tanks": 180, "planes": 650, "ships": 5, "guns": 14000, "ammo": 38000},
        "equipment": {"tanks": 1600, "fighters": 1400, "ships": 55, "missiles": 25, "nukes": 0}
    },
    "iran": {
        "name": "ایران",
        "leader": "محمدرضا پهلوی",
        "power": 28,
        "army": 125000,
        "economy_mode": "peace",
        "industry": 24,
        "manpower": 9000000,
        "money": 1800000,
        "war_credit": 25000,
        "nuclear": False,
        "occupied_by": None,
        "at_war_with": [],
        "allies": [],
        "sanctions": [],
        "blockades": [],
        "factories": [],
        "owner_name": "هیچکس",
        "taken_by": None,
        "last_factory_collect": 0,
        "resources": {"oil": 52000, "steel": 1400, "coal": 900, "food": 19000, "rubber": 220, "aluminum": 180, "uranium": 15},
        "stockpile": {"oil": 78000, "steel": 3200, "coal": 1600, "food": 27000, "rubber": 500, "aluminum": 380, "uranium": 40},
        "production": {"tanks": 8, "planes": 12, "ships": 0, "guns": 1500, "ammo": 9000},
        "equipment": {"tanks": 180, "fighters": 95, "ships": 6, "missiles": 5, "nukes": 0}
    },
    "indonesia": {
        "name": "اندونزی",
        "leader": "سوکارنو",
        "power": 42,
        "army": 450000,
        "economy_mode": "peace",
        "industry": 38,
        "manpower": 48000000,
        "money": 2800000,
        "war_credit": 35000,
        "nuclear": False,
        "occupied_by": None,
        "at_war_with": [],
        "allies": [],
        "sanctions": [],
        "blockades": [],
        "factories": [],
        "owner_name": "هیچکس",
        "taken_by": None,
        "last_factory_collect": 0,
        "resources": {"oil": 28000, "steel": 3200, "coal": 9500, "food": 42000, "rubber": 8500, "aluminum": 900, "uranium": 25},
        "stockpile": {"oil": 45000, "steel": 5800, "coal": 14000, "food": 55000, "rubber": 12000, "aluminum": 1600, "uranium": 45},
        "production": {"tanks": 45, "planes": 80, "ships": 4, "guns": 6500, "ammo": 28000},
        "equipment": {"tanks": 650, "fighters": 320, "ships": 28, "missiles": 15, "nukes": 0}
    },
    "north_korea": {
        "name": "کره شمالی",
        "leader": "کیم ایل‌سونگ",
        "power": 48,
        "army": 950000,
        "economy_mode": "war",
        "industry": 35,
        "manpower": 12000000,
        "money": 900000,
        "war_credit": 18000,
        "nuclear": False,
        "occupied_by": None,
        "at_war_with": [],
        "allies": [],
        "sanctions": [],
        "blockades": [],
        "factories": [],
        "owner_name": "هیچکس",
        "taken_by": None,
        "last_factory_collect": 0,
        "resources": {"oil": 1800, "steel": 2800, "coal": 22000, "food": 9500, "rubber": 150, "aluminum": 400, "uranium": 180},
        "stockpile": {"oil": 3200, "steel": 4500, "coal": 35000, "food": 12000, "rubber": 280, "aluminum": 650, "uranium": 320},
        "production": {"tanks": 90, "planes": 60, "ships": 2, "guns": 12000, "ammo": 45000},
        "equipment": {"tanks": 2200, "fighters": 480, "ships": 18, "missiles": 85, "nukes": 0}
    },
    "afghanistan": {
        "name": "افغانستان",
        "leader": "محمد ظاهر شاه",
        "power": 18,
        "army": 85000,
        "economy_mode": "peace",
        "industry": 12,
        "manpower": 7500000,
        "money": 450000,
        "war_credit": 8000,
        "nuclear": False,
        "occupied_by": None,
        "at_war_with": [],
        "allies": [],
        "sanctions": [],
        "blockades": [],
        "factories": [],
        "owner_name": "هیچکس",
        "taken_by": None,
        "last_factory_collect": 0,
        "resources": {"oil": 400, "steel": 350, "coal": 1200, "food": 8500, "rubber": 40, "aluminum": 60, "uranium": 15},
        "stockpile": {"oil": 800, "steel": 600, "coal": 2000, "food": 11000, "rubber": 80, "aluminum": 100, "uranium": 25},
        "production": {"tanks": 2, "planes": 5, "ships": 0, "guns": 1800, "ammo": 6000},
        "equipment": {"tanks": 85, "fighters": 35, "ships": 0, "missiles": 2, "nukes": 0}
    },
    "china": {
        "name": "چین",
        "leader": "چیانگ کای‌شک / مائو",
        "power": 72,
        "army": 4200000,
        "economy_mode": "war",
        "industry": 55,
        "manpower": 280000000,
        "money": 4800000,
        "war_credit": 65000,
        "nuclear": False,
        "occupied_by": None,
        "at_war_with": [],
        "allies": [],
        "sanctions": [],
        "blockades": [],
        "factories": [],
        "owner_name": "هیچکس",
        "taken_by": None,
        "last_factory_collect": 0,
        "resources": {"oil": 18000, "steel": 28000, "coal": 180000, "food": 160000, "rubber": 1200, "aluminum": 4500, "uranium": 220},
        "stockpile": {"oil": 32000, "steel": 45000, "coal": 250000, "food": 210000, "rubber": 2200, "aluminum": 7800, "uranium": 380},
        "production": {"tanks": 450, "planes": 380, "ships": 6, "guns": 55000, "ammo": 180000},
        "equipment": {"tanks": 4800, "fighters": 2100, "ships": 45, "missiles": 40, "nukes": 0}
    },
    "india": {
        "name": "هند",
        "leader": "جواهر لعل نهرو",
        "power": 58,
        "army": 1800000,
        "economy_mode": "peace",
        "industry": 48,
        "manpower": 220000000,
        "money": 5200000,
        "war_credit": 72000,
        "nuclear": False,
        "occupied_by": None,
        "at_war_with": [],
        "allies": [],
        "sanctions": [],
        "blockades": [],
        "factories": [],
        "owner_name": "هیچکس",
        "taken_by": None,
        "last_factory_collect": 0,
        "resources": {"oil": 8500, "steel": 12000, "coal": 65000, "food": 95000, "rubber": 2800, "aluminum": 2200, "uranium": 95},
        "stockpile": {"oil": 15000, "steel": 22000, "coal": 95000, "food": 130000, "rubber": 4500, "aluminum": 3800, "uranium": 160},
        "production": {"tanks": 180, "planes": 220, "ships": 5, "guns": 28000, "ammo": 95000},
        "equipment": {"tanks": 2100, "fighters": 850, "ships": 32, "missiles": 25, "nukes": 0}
    },
    "israel": {
        "name": "اسرائیل",
        "leader": "دیوید بن‌گوریون",
        "power": 52,
        "army": 180000,
        "economy_mode": "war",
        "industry": 58,
        "manpower": 1800000,
        "money": 2100000,
        "war_credit": 480000000000,
        "nuclear": True,
        "occupied_by": None,
        "at_war_with": [],
        "allies": [],
        "sanctions": [],
        "blockades": [],
        "factories": [],
        "owner_name": "هیچکس",
        "taken_by": None,
        "last_factory_collect": 0,
        "resources": {"oil": 1200, "steel": 1800, "coal": 800, "food": 6500, "rubber": 180, "aluminum": 450, "uranium": 35},
        "stockpile": {"oil": 2800, "steel": 3200, "coal": 1500, "food": 9500, "rubber": 350, "aluminum": 800, "uranium": 60},
        "production": {"tanks": 85, "planes": 120, "ships": 2, "guns": 8500, "ammo": 32000},
        "equipment": {"tanks": 950, "fighters": 420, "ships": 12, "missiles": 55, "nukes": 100}
    },
    "saudi": {
        "name": "عربستان سعودی",
        "leader": "عبدالعزیز آل سعود",
        "power": 35,
        "army": 95000,
        "economy_mode": "peace",
        "industry": 28,
        "manpower": 4500000,
        "money": 8500000,
        "war_credit": 95000,
        "nuclear": False,
        "occupied_by": None,
        "at_war_with": [],
        "allies": [],
        "sanctions": [],
        "blockades": [],
        "factories": [],
        "owner_name": "هیچکس",
        "taken_by": None,
        "last_factory_collect": 0,
        "resources": {"oil": 145000, "steel": 800, "coal": 300, "food": 4800, "rubber": 50, "aluminum": 120, "uranium": 10},
        "stockpile": {"oil": 280000, "steel": 1500, "coal": 600, "food": 7500, "rubber": 100, "aluminum": 250, "uranium": 20},
        "production": {"tanks": 15, "planes": 25, "ships": 1, "guns": 2200, "ammo": 9000},
        "equipment": {"tanks": 280, "fighters": 95, "ships": 8, "missiles": 12, "nukes": 0}
    },
    "australia": {
        "name": "استرالیا",
        "leader": "جان کرتین",
        "power": 55,
        "army": 650000,
        "economy_mode": "war",
        "industry": 52,
        "manpower": 5500000,
        "money": 3800000,
        "war_credit": 62000,
        "nuclear": False,
        "occupied_by": None,
        "at_war_with": [],
        "allies": ["uk", "usa"],
        "sanctions": [],
        "blockades": [],
        "factories": [],
        "owner_name": "هیچکس",
        "taken_by": None,
        "last_factory_collect": 0,
        "resources": {"oil": 6500, "steel": 8500, "coal": 48000, "food": 38000, "rubber": 400, "aluminum": 1800, "uranium": 280},
        "stockpile": {"oil": 12000, "steel": 15000, "coal": 75000, "food": 52000, "rubber": 800, "aluminum": 3200, "uranium": 450},
        "production": {"tanks": 95, "planes": 280, "ships": 6, "guns": 14000, "ammo": 48000},
        "equipment": {"tanks": 1100, "fighters": 950, "ships": 48, "missiles": 20, "nukes": 0}
    }
}

MARKET_PRICES = {
    "tank": 8500,
    "fighter": 12500,
    "ship": 98000,
    "missile": 48000,
    "nuke": 2800000,
    "oil": 22,
    "steel": 48,
    "coal": 14,
    "food": 9,
    "rubber": 65,
    "aluminum": 85,
    "uranium": 3800
}

FACTORY_COST = {
    "steel": 48000,
    "tank": 92000,
    "aircraft": 115000,
    "shipyard": 195000,
    "oil": 68000,
    "uranium": 220000
}

# ==================== مدیریت داده ====================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("users", {}), data.get("countries", DEFAULT_COUNTRIES)
    return {}, DEFAULT_COUNTRIES.copy()

def save_data(users, countries):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"users": users, "countries": countries}, f, ensure_ascii=False, indent=2)

user_data, COUNTRIES = load_data()

def update_and_save():
    save_data(user_data, COUNTRIES)

# ==================== توابع کمکی ====================
def get_user_country(user_id):
    uid = str(user_id)
    if uid not in user_data:
        return None
    return user_data[uid]["country"]

def is_at_war(c1, c2):
    return c2 in COUNTRIES[c1].get("at_war_with", [])

# ==================== دستورات اصلی ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🌍 **ربات شبیه‌سازی جنگ جهانی واقعی**\n\n"
        "دستورات اصلی:\n"
        "/country_set [کشور] - انتخاب کشور\n"
        "/country_info - اطلاعات کشور\n"
        "/status - وضعیت کلی\n"
        "/economy - اقتصاد و منابع\n"
        "/army - ارتش و تجهیزات\n"
        "/market - قیمت‌های بازار\n"
        "/buy [وسیله] [تعداد]\n"
        "/sell [منبع] [مقدار]\n"
        "/build_factory [نوع]\n"
        "/spy [کشور]\n"
        "/lend_lease [کشور] [وسیله] [تعداد]\n"
        "/declare_war [کشور]\n"
        "/peace [کشور]\n"
        "/land_attack [کشور]\n"
        "/air_attack [کشور]\n"
        "/naval_attack [کشور]\n"
        "/missile [کشور]\n"
        "/nuclear [کشور]\n"
        "/occupy [کشور]\n"
        "/sanction [کشور]\n"
        "/blockade [کشور]\n"
        "/help"
    )
    await update.message.reply_text(text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)
  
async def get_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
  uid = str(update.effective_user.id)
  uuid = update.effective_user.id 
  test = uuid - OWNER_ID
  if test == 0:
    uuuid = update.effective_user.id
  else :
    return
  if not context.args:
    await update.message.reply_text("مثال: /owner [country]")
    return
  target = context.args[0]
  if not target in COUNTRIES:
    await update.message.reply_text("کشور نامعتبر.")
    return
  oname = COUNTRIES[target]["owner_name"]
  name = COUNTRIES[target]["name"]
  await update.message.reply_text(f"مالک کشور {name} کاربر {oname} است")
  
async def country_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    name = update.effective_user.full_name

    # اگر قبلاً کشور انتخاب کرده، اجازه تغییر نده
    if uid in user_data and "country" in user_data[uid]:
        current = user_data[uid]["country"]
        await update.message.reply_text(
            f"❌ شما قبلاً کشور **{COUNTRIES[current]['name']}** را انتخاب کرده‌اید.\n"
            f"امکان تغییر کشور وجود ندارد."
        )
        return

    if not context.args:
        taken = [c for c, data in COUNTRIES.items() if data.get("taken_by")]
        available = [c for c in COUNTRIES.keys() if c not in taken]
        await update.message.reply_text(
            "مثال: /country_set germany\n\n"
            f"کشورهای آزاد: {', '.join(available) if available else 'هیچ کشوری آزاد نیست'}"
        )
        return

    country = context.args[0].lower().strip()
    if country not in COUNTRIES:
        await update.message.reply_text("❌ کشور معتبر نیست.")
        return

    # چک کن کسی این کشور را نگرفته باشد
    
    if COUNTRIES[country].get("taken_by"):
        await update.message.reply_text(
            f"❌ کشور **{COUNTRIES[country]['name']}** قبلاً توسط شخص دیگری انتخاب شده است.\n"
            f"نام مالک آن:{COUNTRIES[country]['owner_name']}"
        )
        return

    # ثبت کشور
    user_data[uid] = {"country": country}
    COUNTRIES[country]["taken_by"] = uid
    COUNTRIES[country]["owner_name"] = name
    update_and_save()
    
    await update.message.reply_text(
        f"✅ کشور شما با موفقیت روی **{COUNTRIES[country]['name']}** تنظیم شد.\n"
        f"دیگر امکان تغییر کشور وجود ندارد."
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ریست کامل تمام اطلاعات ربات (مراقب باش!)"""
    # فقط کسی که بخواهد می‌تواند استفاده کند (می‌توانی بعداً محدود به ادمین کنی)
    global user_data, COUNTRIES
    uid = int(update.effective_user.id)
    test = OWNER_ID - uid
    if test == 0:
      uuid = int(update.effective_user.id)
    else:
      await update.message.reply_text("شما مالک ربات نیستید!")
      return
    if not context.args:
      await update.message.reply_text("مثال: /reset all \n /reset country [country] \n /reset occupy \n /reset war \n /reset sanctions \n /reset blockades")
      return
    target = context.args[0]

    if target == "occupy":
      for c in COUNTRIES.values():
        c["occupied_by"] = None
    elif target == "war":
      for c in COUNTRIES.values():
        c["at_war_with"] = []
    elif target == "all":
      COUNTRIES = DEFAULT_COUNTRIES.copy()
      for c in COUNTRIES.values():
        c["taken_by"] = None
        c["occupied_by"] = None
        c["at_war_with"] = []
        c["sanctions"] = []
        c["blockades"] = []
    elif target == "sanctions":
      for c in COUNTRIES.values():
        c["sanctions"] = []
    elif target == "blockades":
      for c in COUNTRIES.values():
        c["sanctions"] = []
    elif target == "country":
      target = context.args[1]
      if not target in COUNTRIES:
        await update.message.reply_text("کشور نامعتبر")
        return
      COUNTRIES[target] = DEFAULT_COUNTRIES[target].copy()
      targetname = DEFAULT_COUNTRIES[target]["name"]
      await update.message.reply_text(f"کل اطلاعات کشور {targetname} ریست شد!")
    update_and_save()  
  
async def country_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    country = get_user_country(uid)
    if not country:
        await update.message.reply_text("اول کشور خودت را انتخاب کن.")
        return
    c = COUNTRIES[country]
    text = (
        f"🏳️ **{c['name']}**\n"
        f"رهبر: {c['leader']}\n"
        f"قدرت: {c['power']}/100\n"
        f"ارتش: {c['army']:,}\n"
        f"صنعت: {c['industry']}/100\n"
        f"پول: {c['money']:,}\n"
        f"War Credit: {c['war_credit']:,}\n"
        f"هسته‌ای: {'دارد' if c['nuclear'] else 'ندارد'}\n"
        f"اشغال‌شده توسط: {c.get('occupied_by') or 'هیچ‌کس'}\n"
        f"در حال جنگ با: {', '.join(c.get('at_war_with', [])) or 'هیچ‌کس'}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await country_info(update, context)

async def economy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    country = get_user_country(uid)
    if not country:
        await update.message.reply_text("اول کشور خودت را انتخاب کن.")
        return
    c = COUNTRIES[country]
    res = c["resources"]
    stock = c["stockpile"]
    text = (
        f"📊 **اقتصاد {c['name']}**\n"
        f"حالت: {'اقتصاد جنگی' if c['economy_mode']=='war' else 'صلح‌آمیز'}\n"
        f"صنعت: {c['industry']}/100 | نیروی کار: {c['manpower']:,}\n"
        f"پول: {c['money']:,} | War Credit: {c['war_credit']:,}\n\n"
        f"**تولید ماهانه منابع:**\n"
        f"نفت: {res['oil']:,} | فولاد: {res['steel']:,} | زغال: {res['coal']:,}\n"
        f"غذا: {res['food']:,} | لاستیک: {res['rubber']:,} | آلومینیوم: {res['aluminum']:,} | اورانیوم: {res['uranium']:,}\n\n"
        f"**ذخیره:**\n"
        f"نفت: {stock['oil']:,} | فولاد: {stock['steel']:,} | زغال: {stock['coal']:,}\n"
        f"غذا: {stock['food']:,} | اورانیوم: {stock['uranium']:,}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def army(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    country = get_user_country(uid)
    if not country:
        await update.message.reply_text("اول کشور خودت را انتخاب کن.")
        return
    c = COUNTRIES[country]
    e = c["equipment"]
    p = c["production"]
    text = (
        f"⚔️ **ارتش {c['name']}**\n"
        f"نیروی انسانی: {c['army']:,}\n\n"
        f"**تجهیزات فعلی:**\n"
        f"تانک: {e['tanks']:,} | جنگنده: {e['fighters']:,}\n"
        f"ناو: {e['ships']:,} | موشک: {e['missiles']:,} | هسته‌ای: {e['nukes']}\n\n"
        f"**تولید ماهانه:**\n"
        f"تانک: {p['tanks']} | هواپیما: {p['planes']} | کشتی: {p['ships']}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🛒 **قیمت‌های بازار (War Credit):**\n\n"
    for item, price in MARKET_PRICES.items():
        text += f"• {item}: {price:,}\n"
    text += "\n/buy [وسیله] [تعداد]\n/sell [منبع] [مقدار]"
    await update.message.reply_text(text)

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    country = get_user_country(uid)
    if not country:
        await update.message.reply_text("اول کشور خودت را انتخاب کن.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("مثال: /buy tank 50")
        return
    item = context.args[0].lower()
    try:
        amount = int(context.args[1])
    except:
        await update.message.reply_text("تعداد باید عدد باشد.")
        return
    if item not in ["tank", "fighter", "ship", "missile", "nuke"]:
        await update.message.reply_text("وسیله معتبر نیست.")
        return
    if item == "nuke" and not COUNTRIES[country]["nuclear"]:
        await update.message.reply_text("کشور شما فناوری هسته‌ای ندارد.")
        return
    cost = MARKET_PRICES[item] * amount
    if COUNTRIES[country]["war_credit"] < cost:
        await update.message.reply_text(f"War Credit کافی نیست. نیاز: {cost:,}")
        return
    COUNTRIES[country]["war_credit"] -= cost
    key = "nukes" if item == "nuke" else item + "s" if item != "ship" else "ships"
    if item == "fighter":
        key = "fighters"
    elif item == "tank":
        key = "tanks"
    elif item == "missile":
        key = "missiles"
    COUNTRIES[country]["equipment"][key] = COUNTRIES[country]["equipment"].get(key, 0) + amount
    update_and_save()
    await update.message.reply_text(f"✅ {amount} عدد {item} خریداری شد. هزینه: {cost:,} War Credit")

async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    country = get_user_country(uid)
    if not country:
        await update.message.reply_text("اول کشور خودت را انتخاب کن.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("مثال: /sell oil 5000")
        return
    resource = context.args[0].lower()
    try:
        amount = int(context.args[1])
    except:
        await update.message.reply_text("مقدار باید عدد باشد.")
        return
    if resource not in MARKET_PRICES or resource in ["tank", "fighter", "ship", "missile", "nuke"]:
        await update.message.reply_text("منبع معتبر نیست.")
        return
    if COUNTRIES[country]["stockpile"].get(resource, 0) < amount:
        await update.message.reply_text("ذخیره کافی نداری.")
        return
    income = MARKET_PRICES[resource] * amount
    COUNTRIES[country]["stockpile"][resource] -= amount
    COUNTRIES[country]["war_credit"] += income
    update_and_save()
    await update.message.reply_text(f"✅ {amount:,} واحد {resource} فروخته شد. درآمد: {income:,} War Credit")

async def build_factory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    country = get_user_country(uid)
    
    if not country:
        await update.message.reply_text("❌ اول باید کشور خودت را انتخاب کنی.")
        return

    if not context.args:
        text = "🏭 کارخانه‌های قابل ساخت:\n\n"
        await update.message.reply_text(text)
        return

    ftype = context.args[0].lower().strip()
    
    if ftype not in FACTORY_COST:
        await update.message.reply_text("❌ نوع کارخانه معتبر نیست.")
        return

    cost = FACTORY_COST[ftype]
    c = COUNTRIES[country]

    if c["war_credit"] < cost:
        await update.message.reply_text(f"❌ War Credit کافی نیست.\nهزینه: {cost:,}")
        return

    # کم کردن پول
    c["war_credit"] -= cost
    c["industry"] = min(100, c["industry"] + 5)

    # افزایش تولید
    if ftype == "tank":
        c["production"]["tanks"] += 200
    elif ftype == "aircraft":
        c["production"]["planes"] += 250
    elif ftype == "shipyard":
        c["production"]["ships"] += 4
    elif ftype == "steel":
        c["resources"]["steel"] += 3000
    elif ftype == "oil":
        c["resources"]["oil"] += 5000
    elif ftype == "uranium":
        c["resources"]["uranium"] += 80

    # ذخیره در لیست کارخانه‌ها
    if "factories" not in c:
        c["factories"] = []
    
    c["factories"].append({
        "type": ftype,
        "built_at": time.time()
    })

    update_and_save()

    await update.message.reply_text(
        f"🏭 کارخانه **{ftype}** با موفقیت ساخته شد!\n"
        f"هزینه: {cost:,} War Credit\n"
        f"تعداد کل کارخانه‌های شما: {len(c['factories'])}"
    )

async def spy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    country = get_user_country(uid)
    if not country:
        await update.message.reply_text("اول کشور خودت را انتخاب کن.")
        return
    if not context.args:
        await update.message.reply_text("مثال: /spy germany")
        return
    target = context.args[0].lower()
    if target not in COUNTRIES or target == country:
        await update.message.reply_text("هدف نامعتبر است.")
        return
    cost = 18000
    if COUNTRIES[country]["war_credit"] < cost:
        await update.message.reply_text(f"نیاز به {cost:,} War Credit داری.")
        return
    COUNTRIES[country]["war_credit"] -= cost
    t = COUNTRIES[target]
    text = (
        f"🕵️ گزارش جاسوسی از **{t['name']}**:\n"
        f"قدرت تقریبی: {t['power']-4} تا {t['power']+6}\n"
        f"تانک تقریبی: {int(t['equipment']['tanks']*0.85):,} ~ {int(t['equipment']['tanks']*1.15):,}\n"
        f"جنگنده: حدود {int(t['equipment']['fighters']*0.9):,}\n"
        f"ناو: حدود {t['equipment']['ships']}\n"
        f"ذخیره نفت تقریبی: {int(t['stockpile']['oil']*0.75):,}\n"
        f"در حال جنگ با: {', '.join(t.get('at_war_with', [])) or 'هیچ‌کس'}"
    )
    update_and_save()
    await update.message.reply_text(text, parse_mode="Markdown")

async def lend_lease(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    country = get_user_country(uid)
    if not country:
        await update.message.reply_text("اول کشور خودت را انتخاب کن.")
        return
    if len(context.args) < 3:
        await update.message.reply_text("مثال: /lend_lease soviet tank 300")
        return
    target = context.args[0].lower()
    item = context.args[1].lower()
    try:
        amount = int(context.args[2])
    except:
        await update.message.reply_text("تعداد باید عدد باشد.")
        return
    if target not in COUNTRIES or item not in ["tank", "fighter", "ship", "missile"]:
        await update.message.reply_text("ورودی نامعتبر.")
        return
    key = {"tank": "tanks", "fighter": "fighters", "ship": "ships", "missile": "missiles"}[item]
    if COUNTRIES[country]["equipment"].get(key, 0) < amount:
        await update.message.reply_text("تجهیزات کافی نداری.")
        return
    COUNTRIES[country]["equipment"][key] -= amount
    COUNTRIES[target]["equipment"][key] = COUNTRIES[target]["equipment"].get(key, 0) + amount
    update_and_save()
    await update.message.reply_text(f"✅ {amount} عدد {item} به {COUNTRIES[target]['name']} ارسال شد.")

async def declare_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    country = get_user_country(uid)
    if not country:
        await update.message.reply_text("اول کشور خودت را انتخاب کن.")
        return
    if not context.args:
        await update.message.reply_text("مثال: /declare_war soviet")
        return
    target = context.args[0].lower()
    if target not in COUNTRIES or target == country:
        await update.message.reply_text("هدف نامعتبر.")
        return
    if target not in COUNTRIES[country]["at_war_with"]:
        COUNTRIES[country]["at_war_with"].append(target)
    if country not in COUNTRIES[target]["at_war_with"]:
        COUNTRIES[target]["at_war_with"].append(country)
    update_and_save()
    await update.message.reply_text(f"⚔️ جنگ بین {COUNTRIES[country]['name']} و {COUNTRIES[target]['name']} اعلام شد!")

async def factory_collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    country = get_user_country(uid)

    if not country:
        await update.message.reply_text("❌ اول باید کشور خودت را انتخاب کنی.")
        return

    c = COUNTRIES[country]

    if c.get("occupied_by"):
        await update.message.reply_text("❌ کشور شما اشغال شده و نمی‌توانید تولیدات کارخانه را جمع کنید.")
        return

    factories = c.get("factories", [])
    if not factories:
        await update.message.reply_text(
            "❌ شما هنوز هیچ کارخانه‌ای نساخته‌اید.\n"
            "با دستور /build_factory کارخانه بسازید."
        )
        return

    now = time.time()
    last_factory_collect = c.get("last_factory_collect", 0)
    cooldown = 60 * 8

    remaining = int(cooldown - (now - last_factory_collect))
    if remaining > 0:
        minutes = remaining // 60
        seconds = remaining % 60
        await update.message.reply_text(
            f"⏳ هنوز زود است!\n"
            f"باید {minutes} دقیقه و {seconds} ثانیه صبر کنی."
        )
        return

    # شمارش تعداد هر نوع کارخانه
    factory_count = {}
    for f in factories:
        ftype = f["type"]
        factory_count[ftype] = factory_count.get(ftype, 0) + 1

    # محاسبه تولیدات
    gained_equipment = {"tanks": 0, "fighters": 0, "ships": 0}
    gained_resources = {"steel": 0, "oil": 0, "uranium": 0}
    text_lines = []

    for ftype, count in factory_count.items():
        if ftype == "tank":
            amount = count * 35
            gained_equipment["tanks"] += amount
            text_lines.append(f"• تانک: +{amount}")
        elif ftype == "aircraft":
            amount = count * 40
            gained_equipment["fighters"] += amount
            text_lines.append(f"• جنگنده: +{amount}")
        elif ftype == "shipyard":
            amount = count * 1
            gained_equipment["ships"] += amount
            text_lines.append(f"• ناو: +{amount}")
        elif ftype == "steel":
            amount = count * 1800
            gained_resources["steel"] += amount
            text_lines.append(f"• فولاد: +{amount:,}")
        elif ftype == "oil":
            amount = count * 2200
            gained_resources["oil"] += amount
            text_lines.append(f"• نفت: +{amount:,}")
        elif ftype == "uranium":
            amount = count * 25
            gained_resources["uranium"] += amount
            text_lines.append(f"• اورانیوم: +{amount}")

    # اضافه کردن به موجودی
    for item, amount in gained_equipment.items():
        if amount > 0:
            c["equipment"][item] = c["equipment"].get(item, 0) + amount

    for res, amount in gained_resources.items():
        if amount > 0:
            c["stockpile"][res] = c["stockpile"].get(res, 0) + amount

    c["last_factory_collect"] = now
    update_and_save()

    text = f"🏭 **تولیدات کارخانه‌های {c['name']} جمع‌آوری شد:**\n\n"
    text += "\n".join(text_lines)
    text += "\n\nمی‌توانی ۸ دقیقه دیگر دوباره جمع کنی."

    await update.message.reply_text(text, parse_mode="Markdown")

async def peace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    country = get_user_country(uid)
    if not country:
        await update.message.reply_text("اول کشور خودت را انتخاب کن.")
        return
    if not context.args:
        await update.message.reply_text("مثال: /peace germany")
        return
    target = context.args[0].lower()
    if target in COUNTRIES[country].get("at_war_with", []):
        COUNTRIES[country]["at_war_with"].remove(target)
    if country in COUNTRIES[target].get("at_war_with", []):
        COUNTRIES[target]["at_war_with"].remove(country)
    update_and_save()
    await update.message.reply_text(f"🕊️ پیمان صلح بین {COUNTRIES[country]['name']} و {COUNTRIES[target]['name']} برقرار شد.")

async def land_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await do_attack(update, context, "land")

async def air_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await do_attack(update, context, "air")

async def naval_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await do_attack(update, context, "naval")

async def missile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await do_attack(update, context, "missile")

async def nuclear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await do_attack(update, context, "nuclear")

async def do_attack(update: Update, context: ContextTypes.DEFAULT_TYPE, attack_type: str):
    uid = str(update.effective_user.id)
    country = get_user_country(uid)
    if not country:
        await update.message.reply_text("اول کشور خودت را انتخاب کن.")
        return
    if not context.args:
        await update.message.reply_text(f"مثال: /{attack_type}_attack germany" if attack_type in ["land","air","naval"] else f"/{attack_type} germany")
        return
    target = context.args[0].lower()
    if target not in COUNTRIES or target == country:
        await update.message.reply_text("هدف نامعتبر.")
        return

    my = COUNTRIES[country]
    enemy = COUNTRIES[target]

    if attack_type == "nuclear":
        if not my["nuclear"] or my["equipment"]["nukes"] < 1:
            await update.message.reply_text("سلاح هسته‌ای در اختیار نداری.")
            return
        my["equipment"]["nukes"] -= 1
        enemy["army"] = int(enemy["army"] * 0.55)
        enemy["industry"] = max(10, enemy["industry"] - 25)
        enemy["stockpile"]["oil"] = int(enemy["stockpile"]["oil"] * 0.4)
        result = f"☢️ حمله هسته‌ای به {enemy['name']} انجام شد!\nتلفات فاجعه‌بار و نابودی گسترده صنعتی."
    elif attack_type == "missile":
        if my["equipment"]["missiles"] < 1:
            await update.message.reply_text("موشک کافی نداری.")
            return
        used = min(15, my["equipment"]["missiles"])
        my["equipment"]["missiles"] -= used
        enemy["industry"] = max(10, enemy["industry"] - used // 2)
        enemy["army"] = int(enemy["army"] * 0.97)
        result = f"🚀 {used} موشک به {enemy['name']} شلیک شد. آسیب به صنعت و نیروها."
    elif attack_type == "land":
        my_power = my["equipment"]["tanks"] * 2 + my["army"] // 1000
        enemy_power = enemy["equipment"]["tanks"] * 2 + enemy["army"] // 1000
        if my_power > enemy_power * 1.1:
            loss_my = random.randint(2, 6)
            loss_en = random.randint(50, 90)
            result = (
                f"⚔️پیروزی زمینی مقابل {enemy['name']}!\n\n"
                f"تلفات شما: {loss_my}"
                f"تلفات دشمن: {loss_en}"
            )
            my["army"] = int(my["army"] * (1 - loss_my/100))
            enemy["army"] = int(enemy["army"] * (1 - loss_en/100))
            my["equipment"]["tanks"] = int(my["equipment"]["tanks"] * 0.92)
            enemy["equipment"]["tanks"] = int(enemy["equipment"]["tanks"] * 0.75)
        else:
            loss_my = random.randint(15, 30)
            loss_en = random.randint(8, 18)
            result = f"⚔️حمله ناموفق به {enemy['name']} \nتلفات شما: {loss_my} \n تلفات دوژمن: {loss_en}"
            my["army"] = int(my["army"] * (1 - loss_my/100))
            enemy["army"] = int(enemy["army"] * (1 - loss_en/100))
    elif attack_type == "air":
        if my["equipment"]["fighters"] < 50:
            await update.message.reply_text("جنگنده کافی نداری.")
            return
        used = min(200, my["equipment"]["fighters"] // 5)
        my["equipment"]["fighters"] -= used // 4
        enemy["industry"] = max(10, enemy["industry"] - 8)
        enemy["stockpile"]["oil"] = int(enemy["stockpile"]["oil"] * 0.92)
        result = f"✈️ حمله هوایی با {used} جنگنده به {enemy['name']} انجام شد. آسیب به صنعت و منابع."
    elif attack_type == "naval":
        if my["equipment"]["ships"] < 5:
            await update.message.reply_text("ناو کافی نداری.")
            return
        my["equipment"]["ships"] = max(0, my["equipment"]["ships"] - random.randint(1, 4))
        enemy["stockpile"]["oil"] = int(enemy["stockpile"]["oil"] * 0.88)
        enemy["war_credit"] = int(enemy["war_credit"] * 0.95)
        result = f"⚓ حمله دریایی به {enemy['name']} انجام شد. خطوط تأمین آسیب دید."

    update_and_save()
    await update.message.reply_text(result)

async def occupy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    country = get_user_country(uid)
    if not country:
        await update.message.reply_text("اول کشور خودت را انتخاب کن.")
        return
    if not context.args:
        await update.message.reply_text("مثال: /occupy italy")
        return
    target = context.args[0].lower()
    if target not in COUNTRIES:
        await update.message.reply_text("کشور معتبر نیست.")
        return
    if COUNTRIES[target]["army"] > COUNTRIES[country]["army"] * 0.35:
        await update.message.reply_text("هنوز قدرت نظامی دشمن برای تصرف کافی پایین نیامده.")
        return
    COUNTRIES[target]["occupied_by"] = country
    COUNTRIES[target]["army"] = int(COUNTRIES[target]["army"] * 0.3)
    # غنیمت
    COUNTRIES[country]["war_credit"] += COUNTRIES[target]["war_credit"] // 3
    COUNTRIES[target]["war_credit"] = COUNTRIES[target]["war_credit"] // 3
    update_and_save()
    await update.message.reply_text(f"🏴 کشور {COUNTRIES[target]['name']} توسط شما تصرف شد!")

async def convertmoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
  uid = str(update.effective_user.id)
  country = get_user_country(uid)

  if not country:
    await update.message.reply_text("اول کشور خودت را انتخاب کن.")
    return
  if not context.args:
    await update.message.reply_text("مثال: /convert 100")
    return
  value = int(context.args[0])
  if COUNTRIES[country]["money"] < value:
    await update.message.reply_text("پول کافی نداری")
    return
  print(COUNTRIES[country]["money"])
  COUNTRIES[country]["money"] -= value
  valuee = value / 100
  COUNTRIES[country]["war_credit"] += valuee
  await update.message.reply_text(f"تو مقدار {value} پول رو به {valuee} war_credit کردی")
  update_and_save()

async def buy_soldier(update: Update, context: ContextTypes.DEFAULT_TYPE):
  uid = str(update.effective_user.id)
  country = get_user_country(uid)
  if not country:
    await update.message.reply_text("اول کشور خودت را انتخاب کن.")
    return
  if not context.args:
    await update.message.reply_text("مثال: /buysoldier 123")
    return
  amount = int(context.args[0])
  price = 100

  need = amount * price

  if COUNTRIES[country]["money"] < need:
    await update.message.reply_text("پول کافی نداری")
    return
  COUNTRIES[country]["money"] -= need
  COUNTRIES[country]["army"] += need
  await update.message.reply_text(f"تو مقدار {amount} سرباز رو به قیمت {need} خریدی")
  update_and_save()
async def sanction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    country = get_user_country(uid)
    if not country:
        await update.message.reply_text("اول کشور خودت را انتخاب کن.")
        return
    if not context.args:
        await update.message.reply_text("مثال: /sanction japan")
        return
    target = context.args[0].lower()
    if target not in COUNTRIES:
        await update.message.reply_text("کشور معتبر نیست.")
        return
    if target not in COUNTRIES[country]["sanctions"]:
        COUNTRIES[country]["sanctions"].append(target)
    update_and_save()
    await update.message.reply_text(f"🚫 تحریم علیه {COUNTRIES[target]['name']} اعمال شد.")

async def blockade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    country = get_user_country(uid)
    if not country:
        await update.message.reply_text("اول کشور خودت را انتخاب کن.")
        return
    if not context.args:
        await update.message.reply_text("مثال: /blockade japan")
        return
    target = context.args[0].lower()
    if COUNTRIES[country]["equipment"]["ships"] < 15:
        await update.message.reply_text("حداقل ۱۵ ناو برای محاصره نیاز است.")
        return
    if target not in COUNTRIES[country]["blockades"]:
        COUNTRIES[country]["blockades"].append(target)
    update_and_save()
    await update.message.reply_text(f"⚓ محاصره دریایی علیه {COUNTRIES[target]['name']} آغاز شد.")
async def factories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    country = get_user_country(uid)

    if not country:
        await update.message.reply_text("❌ اول باید کشور خودت را انتخاب کنی.")
        return

    c = COUNTRIES[country]
    factory_list = c.get("factories", [])

    if not factory_list:
        await update.message.reply_text(
            f"🏭 کشور **{c['name']}** هنوز هیچ کارخانه‌ای نساخته است.\n"
            f"با دستور /build_factory می‌توانی کارخانه بسازی."
        )
        return

    # شمارش تعداد هر نوع کارخانه
    count = {}
    for f in factory_list:
        ftype = f["type"]
        count[ftype] = count.get(ftype, 0) + 1

    text = f"🏭 **کارخانه‌های {c['name']}**\n\n"
    text += f"تعداد کل: {len(factory_list)}\n\n"

    for ftype, amount in count.items():
        text += f"• {ftype}: {amount} عدد\n"

    await update.message.reply_text(text, parse_mode="Markdown")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("country_set", country_set))
    app.add_handler(CommandHandler("country_info", country_info))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("economy", economy))
    app.add_handler(CommandHandler("army", army))
    app.add_handler(CommandHandler("market", market))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("sell", sell))
    app.add_handler(CommandHandler("build_factory", build_factory))
    app.add_handler(CommandHandler("convert", convertmoney))
    app.add_handler(CommandHandler("spy", spy))
    app.add_handler(CommandHandler("lend_lease", lend_lease))
    app.add_handler(CommandHandler("declare_war", declare_war))
    app.add_handler(CommandHandler("peace", peace))
    app.add_handler(CommandHandler("land_attack", land_attack))
    app.add_handler(CommandHandler("air_attack", air_attack))
    app.add_handler(CommandHandler("naval_attack", naval_attack))
    app.add_handler(CommandHandler("missile", missile))
    app.add_handler(CommandHandler("nuclear", nuclear))
    app.add_handler(CommandHandler("occupy", occupy))
    app.add_handler(CommandHandler("sanction", sanction))
    app.add_handler(CommandHandler("blockade", blockade))
    app.add_handler(CommandHandler("factories", factories))
    app.add_handler(CommandHandler("factory_collect", factory_collect))  # برای املای اشتباه هم کار کند
    app.add_handler(CommandHandler("buy_soldier", buy_soldier))
    # app.add_handler(CommandHandler("sea_business", business))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("owner", get_owner))
  
    print("ربات جنگ جهانی با موفقیت اجرا شد...")
    app.run_polling()

if __name__ == "__main__":
    main()
