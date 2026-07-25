import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", "instantcalendar.db")

if not BOT_TOKEN:
    # We don't raise here so that tools like `python -m py_compile` still work
    # without a token set. main.py checks this before starting the bot.
    pass
