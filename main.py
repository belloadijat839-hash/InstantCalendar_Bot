import logging
import sys

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from bot.config import BOT_TOKEN
from bot.database import init_db
from bot import handlers as h

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set. Set it as an environment variable (see .env.example).")
        sys.exit(1)

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", h.start_cmd))
    app.add_handler(CommandHandler("help", h.help_cmd))
    app.add_handler(CommandHandler("calendar", h.calendar_cmd))
    app.add_handler(CommandHandler("addevent", h.addevent_cmd))
    app.add_handler(CommandHandler("myevents", h.myevents_cmd))
    app.add_handler(CommandHandler("delete", h.delete_cmd))
    app.add_handler(CommandHandler("image", h.image_cmd))
    app.add_handler(CommandHandler("export", h.export_cmd))

    app.add_handler(CallbackQueryHandler(h.calendar_callback, pattern=r"^cal\|"))

    # Free-text replies used only for the "pick date -> type event details" flow
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, h.pending_date_text_handler))

    logger.info("InstantCalendar_Bot starting (polling mode)...")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
