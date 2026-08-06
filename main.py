# =============== main.py ===============
# نصب کتابخانه‌ها: pip install telethon asyncio pillow googletrans==4.0.0-rc1 gTTS requests psutil flask

from telethon import TelegramClient, events
from telethon.tl.functions.users import GetFullUserRequest
import asyncio
import random
import re
import datetime
import os
import time
import requests
from PIL import Image
from gtts import gTTS
from googletrans import Translator
import psutil
from flask import Flask
import threading

# =============== اطلاعات اکانت از متغیرهای محیطی ===============
api_id = int(os.environ.get('API_ID', 0))
api_hash = os.environ.get('API_HASH', '')
session_str = os.environ.get('SESSION_STRING', None)

if not api_id or not api_hash or not session_str:
    print("❌ لطفاً متغیرهای محیطی API_ID, API_HASH, SESSION_STRING را تنظیم کنید")
    exit(1)

client = TelegramClient(session_str, api_id, api_hash)
translator = Translator()

# =============== متغیرهای جهانی ===============
spam_tasks = {}
text_format = None
time_enabled = False
last_time_message = None
auto_clean_enabled = False
reminder_enabled = False
auto_translate_lang = None
reminders = []
startup_time = time.time()

# =============== Flask برای جلوگیری از خوابیدن ===============
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 ربات فعال است!"

@app.route('/ping')
def ping():
    return "🏓 Pong!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# =============== توابع کمکی ===============
def number_to_font(num):
    font_nums = {'0': '𝟘', '1': '𝟙', '2': '𝟚', '3': '𝟛', '4': '𝟜',
                 '5': '𝟝', '6': '𝟞', '7': '𝟟', '8': '𝟠', '9': '𝟡'}
    return ''.join(font_nums.get(c, c) for c in str(num))

def format_text(text, format_type):
    formats = {
        'bold': f"**{text}**",
        'italic': f"__{text}__",
        'mono': f"`{text}`",
        'underline': f"--{text}--",
        'strikethrough': f"~~{text}~~"
    }
    return formats.get(format_type, text)

def get_uptime():
    uptime_seconds = int(time.time() - startup_time)
    hours = uptime_seconds // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# =============== ۱. اسپم ===============
@client.on(events.NewMessage(pattern=r'\.spam (.+)'))
async def start_spam(event):
    global spam_tasks
    text = event.pattern_match.group(1)
    chat_id = event.chat_id
    
    if chat_id in spam_tasks:
        spam_tasks[chat_id].cancel()
    
    async def spam_loop():
        while True:
            await client.send_message(chat_id, text)
            await asyncio.sleep(3)
    
    task = asyncio.create_task(spam_loop())
    spam_tasks[chat_id] = task
    await event.reply(f"✅ اسپم شروع شد: {text}")

@client.on(events.NewMessage(pattern=r'\.stopspam'))
async def stop_spam(event):
    global spam_tasks
    chat_id = event.chat_id
    
    if chat_id in spam_tasks:
        spam_tasks[chat_id].cancel()
        del spam_tasks[chat_id]
        await event.reply("⏹ اسپم متوقف شد")
    else:
        await event.reply("❌ اسپمی در حال اجرا نیست")

# =============== ۲. زمان ===============
@client.on(events.NewMessage(pattern=r'\.time (on|off)'))
async def toggle_time(event):
    global time_enabled, last_time_message
    status = event.pattern_match.group(1)
    
    if status == 'on':
        time_enabled = True
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M:%S")
        formatted_time = number_to_font(time_str)
        last_time_message = await client.send_message('me', f"⏰ {formatted_time}")
        await event.reply("✅ نمایش زمان فعال شد")
        
        async def update_time():
            global last_time_message
            while time_enabled:
                await asyncio.sleep(1)
                now = datetime.datetime.now()
                time_str = now.strftime("%H:%M:%S")
                formatted_time = number_to_font(time_str)
                if last_time_message:
                    await last_time_message.edit(f"⏰ {formatted_time}")
        
        asyncio.create_task(update_time())
        
    elif status == 'off':
        time_enabled = False
        if last_time_message:
            await last_time_message.delete()
            last_time_message = None
        await event.reply("❌ نمایش زمان غیرفعال شد")

# =============== ۳. بازی‌ها ===============
@client.on(events.NewMessage(pattern=r'\.dice (\d+)'))
async def dice_game(event):
    target = int(event.pattern_match.group(1))
    if target < 1 or target > 6:
        await event.reply("❌ عدد باید بین ۱ تا ۶ باشد")
        return
    
    chat_id = event.chat_id
    await event.reply(f"🎲 شروع تاس‌اندازی تا عدد {target}...")
    
    while True:
        result = random.randint(1, 6)
        if result == target:
            await client.send_message(chat_id, f"✅ عدد {target} آمد! {number_to_font(target)}")
            break
        else:
            await client.send_message(chat_id, f"🎲 {number_to_font(result)}")
            await asyncio.sleep(3)

@client.on(events.NewMessage(pattern=r'\.football'))
async def football_game(event):
    chat_id = event.chat_id
    await event.reply("⚽ شروع بازی فوتبال...")
    
    while True:
        result = random.choice(['گل شد! ⚽✅', 'گل نشد ❌', 'گل نشد ❌', 'گل نشد ❌'])
        await client.send_message(chat_id, f"⚽ {result}")
        if 'گل شد' in result:
            break
        await asyncio.sleep(3)

@client.on(events.NewMessage(pattern=r'\.basket'))
async def basketball_game(event):
    chat_id = event.chat_id
    await event.reply("🏀 شروع بازی بسکتبال...")
    
    while True:
        result = random.choice(['گل شد! 🏀✅', 'گل نشد ❌', 'گل نشد ❌', 'گل نشد ❌'])
        await client.send_message(chat_id, f"🏀 {result}")
        if 'گل شد' in result:
            break
        await asyncio.sleep(3)

# =============== ۴. فرمت‌دهی ===============
@client.on(events.NewMessage)
async def auto_format(event):
    global text_format
    
    if event.out or not event.is_private:
        return
    
    if event.text.startswith('.type'):
        parts = event.text.split()
        if len(parts) > 1:
            format_type = parts[1].lower()
            if format_type in ['bold', 'italic', 'mono', 'underline', 'strikethrough']:
                text_format = format_type
                await event.reply(f"✅ فرمت به {format_type} تغییر یافت")
            else:
                await event.reply("❌ فرمت نامعتبر. گزینه‌ها: bold, italic, mono, underline, strikethrough")
        return
    
    if text_format and event.text and not event.text.startswith('.'):
        formatted = format_text(event.text, text_format)
        await event.edit(formatted)

# =============== ۵. پاک‌کننده ===============
@client.on(events.NewMessage(pattern=r'\.clean (\d+)'))
async def clean_messages(event):
    count = int(event.pattern_match.group(1))
    if count > 500:
        await event.reply("❌ حداکثر ۵۰۰ پیام قابل پاک‌سازی است")
        return
    
    chat_id = event.chat_id
    deleted = 0
    async for msg in client.iter_messages(chat_id, limit=count):
        await msg.delete()
        deleted += 1
        await asyncio.sleep(0.1)
    
    await event.reply(f"🧹 {deleted} پیام پاک شد")

# =============== ۶. پاک‌کننده خودکار ===============
@client.on(events.NewMessage(pattern=r'\.autoclean (on|off)'))
async def auto_clean(event):
    global auto_clean_enabled
    status = event.pattern_match.group(1)
    
    if status == 'on':
        auto_clean_enabled = True
        await event.reply("✅ پاک‌کننده خودکار فعال شد (ساعت ۱۲ شب)")
        
        async def auto_clean_loop():
            global auto_clean_enabled
            while auto_clean_enabled:
                now = datetime.datetime.now()
                if now.hour == 0 and now.minute == 0:
                    chat_id = event.chat_id
                    yesterday = now - datetime.timedelta(days=1)
                    async for msg in client.iter_messages(chat_id, offset_date=yesterday):
                        await msg.delete()
                        await asyncio.sleep(0.1)
                    await client.send_message(chat_id, "🧹 پیام‌های روز قبل پاک شدند")
                await asyncio.sleep(60)
        
        asyncio.create_task(auto_clean_loop())
    
    elif status == 'off':
        auto_clean_enabled = False
        await event.reply("❌ پاک‌کننده خودکار غیرفعال شد")

# =============== ۷. تبدیل متن به صدا ===============
@client.on(events.NewMessage(pattern=r'\.voice (.+)'))
async def text_to_voice(event):
    text = event.pattern_match.group(1)
    try:
        tts = gTTS(text=text, lang='fa', slow=False)
        tts.save('voice.mp3')
        await client.send_file(event.chat_id, 'voice.mp3', voice_note=True)
        os.remove('voice.mp3')
    except Exception as e:
        await event.reply(f"❌ خطا: {str(e)}")

# =============== ۸. یادآوری ===============
@client.on(events.NewMessage(pattern=r'\.reminder (on|off)'))
async def reminder_toggle(event):
    global reminder_enabled
    status = event.pattern_match.group(1)
    reminder_enabled = (status == 'on')
    await event.reply(f"{'✅' if reminder_enabled else '❌'} یادآوری {'فعال' if reminder_enabled else 'غیرفعال'} شد")

@client.on(events.NewMessage(pattern=r'\.reminder if online (.+) \[(\d+/\d+/\d+)\] \[(\d+:\d+)\]'))
async def reminder_online(event):
    if not reminder_enabled:
        await event.reply("❌ یادآوری غیرفعال است. ابتدا با .reminder on فعال کنید")
        return
    
    text = event.pattern_match.group(1)
    date = event.pattern_match.group(2)
    time_str = event.pattern_match.group(3)
    
    try:
        day, month, year = map(int, date.split('/'))
        hour, minute = map(int, time_str.split(':'))
        target_date = datetime.datetime(2000 + year, month, day, hour, minute)
        
        if target_date < datetime.datetime.now():
            await event.reply("❌ تاریخ یا زمان گذشته است")
            return
        
        reminders.append({
            'chat_id': event.chat_id,
            'text': text,
            'date': target_date,
            'user_id': event.sender_id
        })
        
        await event.reply(f"✅ یادآوری در تاریخ {date} ساعت {time_str} تنظیم شد")
        
        async def check_reminders():
            while True:
                now = datetime.datetime.now()
                for rem in reminders[:]:
                    if rem['date'] <= now:
                        try:
                            await client.send_message(rem['user_id'], f"⏰ {rem['text']}")
                            reminders.remove(rem)
                        except:
                            pass
                await asyncio.sleep(60)
        
        asyncio.create_task(check_reminders())
        
    except Exception as e:
        await event.reply(f"❌ فرمت تاریخ یا زمان نامعتبر: {str(e)}")

# =============== ۹. زمان‌بندی ===============
@client.on(events.NewMessage(pattern=r'\.schedule (\d+/\d+/\d+) (\d+:\d+) (.+)'))
async def schedule_message(event):
    date_str = event.pattern_match.group(1)
    time_str = event.pattern_match.group(2)
    text = event.pattern_match.group(3)
    
    try:
        day, month, year = map(int, date_str.split('/'))
        hour, minute = map(int, time_str.split(':'))
        target_date = datetime.datetime(2000 + year, month, day, hour, minute)
        
        if target_date < datetime.datetime.now():
            await event.reply("❌ تاریخ یا زمان گذشته است")
            return
        
        delay = (target_date - datetime.datetime.now()).total_seconds()
        await asyncio.sleep(delay)
        await client.send_message(event.chat_id, f"⏰ پیام زمان‌بندی شده:\n{text}")
        await event.reply("✅ پیام در زمان مقرر ارسال شد")
        
    except Exception as e:
        await event.reply(f"❌ خطا: {str(e)}")

# =============== ۱۰. ترجمه ===============
@client.on(events.NewMessage(pattern=r'\.translate (fa|eng|ab) (.+)'))
async def translate_text(event):
    target_lang = event.pattern_match.group(1)
    text = event.pattern_match.group(2)
    
    lang_map = {'fa': 'fa', 'eng': 'en', 'ab': 'ar'}
    try:
        translated = translator.translate(text, dest=lang_map[target_lang])
        await event.reply(f"🌐 ترجمه ({target_lang}):\n{translated.text}")
    except Exception as e:
        await event.reply(f"❌ خطا: {str(e)}")

# =============== ۱۱. ترجمه خودکار ===============
@client.on(events.NewMessage(pattern=r'\.autotranslate (fa|eng|ab)'))
async def auto_translate_toggle(event):
    global auto_translate_lang
    lang = event.pattern_match.group(1)
    auto_translate_lang = lang
    await event.reply(f"✅ ترجمه خودکار به {lang} فعال شد (در این چت)")

@client.on(events.NewMessage)
async def auto_translate_handler(event):
    global auto_translate_lang
    if auto_translate_lang and event.chat_id and not event.out:
        try:
            lang_map = {'fa': 'fa', 'eng': 'en', 'ab': 'ar'}
            detected = translator.detect(event.text)
            if detected.lang != lang_map[auto_translate_lang]:
                translated = translator.translate(event.text, dest=lang_map[auto_translate_lang])
                await event.reply(f"🌐 ترجمه ({auto_translate_lang}):\n{translated.text}")
        except:
            pass

# =============== ۱۲. آمار گروه ===============
@client.on(events.NewMessage(pattern=r'\.groupstats'))
async def group_stats(event):
    chat_id = event.chat_id
    stats = {}
    
    async for msg in client.iter_messages(chat_id, limit=1000):
        if msg.sender_id:
            stats[msg.sender_id] = stats.get(msg.sender_id, 0) + 1
    
    sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)[:10]
    
    result = "📊 **۱۰ نفر برتر گروه:**\n\n"
    for idx, (user_id, count) in enumerate(sorted_stats, 1):
        try:
            user = await client.get_entity(user_id)
            name = user.first_name or user.username or str(user_id)
            result += f"{idx}. {name}: {count} پیام\n"
        except:
            result += f"{idx}. {user_id}: {count} پیام\n"
    
    await event.reply(result)

# =============== ۱۳. ذخیره ===============
@client.on(events.NewMessage(pattern=r'\.save'))
async def save_message(event):
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        if reply_msg.text:
            await client.send_message('me', f"📌 ذخیره شد:\n{reply_msg.text}")
            await event.reply("✅ پیام در Saved Messages ذخیره شد")
        elif reply_msg.media:
            file = await reply_msg.download_media()
            await client.send_file('me', file)
            os.remove(file)
            await event.reply("✅ فایل در Saved Messages ذخیره شد")
    else:
        await event.reply("❌ روی یک پیام ریپلی کنید")

# =============== ۱۴. اطلاعات کاربر ===============
@client.on(events.NewMessage(pattern=r'\.info'))
async def user_info(event):
    if event.is_reply:
        user = await event.get_reply_message()
        user_id = user.sender_id
    else:
        user_id = event.sender_id
    
    try:
        full_user = await client(GetFullUserRequest(user_id))
        user = full_user.user
        
        info = f"""
📋 **اطلاعات کاربر:**

👤 نام: {user.first_name or 'نامشخص'}
🏷 نام کاربری: @{user.username or 'ندارد'}
🆔 آیدی عددی: {user.id}
📱 شماره: {user.phone or 'نامشخص'}
📝 بیو: {full_user.about or 'ندارد'}
🖼 عکس پروفایل: {'دارد' if user.photo else 'ندارد'}
        """
        await event.reply(info)
    except Exception as e:
        await event.reply(f"❌ خطا: {str(e)}")

# =============== ۱۵. پنل ===============
@client.on(events.NewMessage(pattern=r'\.panel'))
async def panel(event):
    panel_text = """
🎛 **پنل کاربری**

🔹 **ربات:** UserBot پیشرفته
🔹 **وضعیت:** فعال ✅
🔹 **تعداد قابلیت‌ها:** ۲۰+

📋 **دستورات سریع:**
• `.help` - مشاهده همه دستورات
• `.spam` - ارسال خودکار پیام
• `.time` - نمایش زمان
• `.dice` - تاس‌اندازی
• `.clean` - پاک‌سازی پیام‌ها
• `.save` - ذخیره در Saved Messages
• `.weather` - آب و هوا
• `.translate` - ترجمه

📊 **آمار امروز:**
• تعداد چت‌ها: {len(await client.get_dialogs())}
    """
    await event.reply(panel_text)

# =============== ۱۶. آب و هوا ===============
@client.on(events.NewMessage(pattern=r'\.weather (.+)'))
async def get_weather(event):
    city = event.pattern_match.group(1)
    api_key = "YOUR_OPENWEATHER_API_KEY"  # از openweathermap.org بگیرید
    
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=fa"
        response = requests.get(url).json()
        
        if response.get('cod') == 200:
            temp = response['main']['temp']
            feels_like = response['main']['feels_like']
            humidity = response['main']['humidity']
            desc = response['weather'][0]['description']
            wind = response['wind']['speed']
            
            weather_text = f"""
🌤 **آب و هوای {city}:**

🌡 دما: {temp}°C
🤔 احساس دما: {feels_like}°C
💧 رطوبت: {humidity}%
📝 وضعیت: {desc}
💨 سرعت باد: {wind} m/s
            """
            await event.reply(weather_text)
        else:
            await event.reply("❌ شهر پیدا نشد")
    except Exception as e:
        await event.reply(f"❌ خطا: {str(e)}")

# =============== ۱۷. تبدیل عکس به استیکر ===============
@client.on(events.NewMessage(pattern=r'\.photo to sticker'))
async def photo_to_sticker(event):
    if event.is_reply and event.reply_to_msg.photo:
        try:
            file = await event.reply_to_msg.download_media()
            img = Image.open(file)
            img = img.resize((512, 512))
            img.save('sticker.webp', 'WEBP')
            await client.send_file(event.chat_id, 'sticker.webp', force_document=False)
            os.remove(file)
            os.remove('sticker.webp')
            await event.reply("✅ عکس به استیکر تبدیل شد")
        except Exception as e:
            await event.reply(f"❌ خطا: {str(e)}")
    else:
        await event.reply("❌ روی یک عکس ریپلی کنید")

# =============== ۱۸. تبدیل عکس به گیف ===============
@client.on(events.NewMessage(pattern=r'\.photo to gif'))
async def photo_to_gif(event):
    if event.is_reply and event.reply_to_msg.photo:
        try:
            await event.reply("⚠️ این قابلیت نیاز به نصب کتابخانه Pillow و imageio دارد")
        except Exception as e:
            await event.reply(f"❌ خطا: {str(e)}")
    else:
        await event.reply("❌ روی یک عکس ریپلی کنید")

# =============== ۱۹. تبدیل ویدئو به استیکر ===============
@client.on(events.NewMessage(pattern=r'\.video to sticker'))
async def video_to_sticker(event):
    if event.is_reply and event.reply_to_msg.video:
        try:
            await event.reply("⚠️ این قابلیت نیاز به نصب کتابخانه moviepy دارد")
        except Exception as e:
            await event.reply(f"❌ خطا: {str(e)}")
    else:
        await event.reply("❌ روی یک ویدئو ریپلی کنید")

# =============== ۲۰. تبدیل ویدئو به گیف ===============
@client.on(events.NewMessage(pattern=r'\.video to gif'))
async def video_to_gif(event):
    if event.is_reply and event.reply_to_msg.video:
        try:
            await event.reply("⚠️ این قابلیت نیاز به نصب کتابخانه moviepy دارد")
        except Exception as e:
            await event.reply(f"❌ خطا: {str(e)}")
    else:
        await event.reply("❌ روی یک ویدئو ریپلی کنید")

# =============== ۲۱. پینگ ===============
@client.on(events.NewMessage(pattern=r'\.ping'))
async def ping_command(event):
    start_time = datetime.datetime.now()
    msg = await event.reply("🏓 در حال بررسی...")
    end_time = datetime.datetime.now()
    
    ping_time = (end_time - start_time).microseconds / 1000
    
    if ping_time < 100:
        ping_status = "🟢 عالی"
    elif ping_time < 300:
        ping_status = "🟡 خوب"
    elif ping_time < 500:
        ping_status = "🟠 متوسط"
    else:
        ping_status = "🔴 ضعیف"
    
    try:
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        ram_usage = memory.percent
    except:
        cpu_usage = "N/A"
        ram_usage = "N/A"
    
    await msg.edit(
        f"🏓 **پینگ:**\n\n"
        f"⏱ زمان پاسخ: `{ping_time:.2f}` ms\n"
        f"📊 وضعیت: {ping_status}\n"
        f"📶 اتصال: {'✅ متصل' if client.is_connected() else '❌ قطع'}\n"
        f"💻 مصرف CPU: `{cpu_usage}%`\n"
        f"🧠 مصرف RAM: `{ram_usage}%`\n"
        f"🔄 آپ‌تایم: `{get_uptime()}`\n"
        f"🤖 ربات: {'فعال ✅' if client.is_connected() else 'خاموش ❌'}"
    )

# =============== ۲۲. راهنما ===============
@client.on(events.NewMessage(pattern=r'\.help'))
async def help_command(event):
    help_text = """
📋 **راهنمای کامل ربات:**

**🔹 مدیریت پیام:**
• `.spam متن` - هر ۳ ثانیه متن را می‌فرستد
• `.stopspam` - متوقف کردن اسپم
• `.clean تعداد` - پاک کردن پیام‌ها (حداکثر ۵۰۰)
• `.autoclean on/off` - پاک‌سازی خودکار ساعت ۱۲ شب

**🔹 ابزارها:**
• `.ping` - بررسی وضعیت ربات و پینگ
• `.time on/off` - نمایش زمان با فونت اعداد
• `.voice متن` - تبدیل متن به صدا
• `.translate lang متن` - ترجمه متن (fa/eng/ab)
• `.autotranslate lang` - ترجمه خودکار در چت
• `.weather شهر` - نمایش آب و هوا

**🔹 بازی‌ها:**
• `.dice عدد(1-6)` - تاس‌اندازی تا عدد مورد نظر
• `.football` - بازی فوتبال تا گل شدن
• `.basket` - بازی بسکتبال تا گل شدن

**🔹 یادآوری و زمان‌بندی:**
• `.reminder on/off` - فعال/غیرفعال کردن یادآوری
• `.reminder if online متن [تاریخ] [ساعت]` - یادآوری در زمان مشخص
• `.schedule تاریخ ساعت متن` - ارسال پیام در زمان مشخص

**🔹 اطلاعات و آمار:**
• `.groupstats` - نمایش ۱۰ نفر برتر گروه
• `.info` - اطلاعات کامل کاربر (ریپلی کنید)
• `.panel` - پنل کاربری

**🔹 تبدیل‌ها:**
• `.save` - ذخیره پیام/فایل در Saved Messages
• `.photo to sticker` - تبدیل عکس به استیکر
• `.photo to gif` - تبدیل عکس به گیف
• `.video to sticker` - تبدیل ویدئو به استیکر
• `.video to gif` - تبدیل ویدئو به گیف

**🔹 فرمت‌دهی:**
• `.type bold|italic|mono|underline|strikethrough` - فرمت خودکار پیام‌ها

📌 **نکته:** برای دستورات `.info` و `.save` و تبدیل‌ها، روی پیام مورد نظر ریپلی کنید.
    """
    await event.reply(help_text)

# =============== شروع ربات و Flask ===============
async def main():
    await client.start()
    print("✅ ربات روشن شد!")
    print("📋 برای راهنما دستور .help را بفرستید")
    await client.run_until_disconnected()

if __name__ == '__main__':
    # اجرای Flask در یک ترد جداگانه
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    # اجرای ربات
    asyncio.run(main())