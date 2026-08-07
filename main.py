import os
import importlib.util
from dotenv import load_dotenv
from telegram.ext import Application

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

def load_module(name):
    path = os.path.join("modules", f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module

def main():
    application = (Application.builder().token(TOKEN).build())
    ban = load_module("ban")
    mute = load_module("mute")
    clear = load_module("clear")
    pin = load_module("pin")
    unpin = load_module("unpin")
    ping = load_module("ping")
    promote = load_module("promote")
    demote = load_module("demote")

    ban.register(application)
    mute.register(application)
    clear.register(application)
    pin.register(application)
    unpin.register(application)
    ping.register(application)
    promote.register(application)
    demote.register(application)

    application.run_polling()

if __name__ == "__main__":
    main()
