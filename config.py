import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

# تنظیمات پیش‌فرض
WARN_LIMIT = 3
MUTE_DURATION = 3600  # ۱ ساعت
ADMIN_COMMANDS = ["ban", "unban", "kick", "mute", "unmute", "warn", 
                  "unwarn", "warns", "purge", "lock", "unlock", 
                  "filter", "filters", "stop", "setwelcome", 
                  "setgoodbye", "addword", "removeword"]