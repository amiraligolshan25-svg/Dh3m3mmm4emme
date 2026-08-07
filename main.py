from telegram.ext import Application

from modules import ban
from modules import promote
from modules import demote
from modules import ping
from modules import pin
from modules import unpin
from modules import mute
from modules import clear
from dotenv import load_dotenv

import os

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("TOKEN not set in .env file")

def main():
    application = (Application.builder().token(TOKEN).build())

    ban.register(application)
    mute.register(application)
    clear.register(application)
    demote.register(application)
    pin.register(application)
    unpin.register(application)
    promote.register(application)
    ping.register(application)
    