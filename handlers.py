import logging
from datetime import date, datetime

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from bot.calendar_keyboard import build_calendar, parse_callback, shift_month
from bot import database as db
from bot.image_calendar import generate_month_image
from bot.ics_export import build_ics

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "*InstantCalendar_Bot*\n\n"
    "/calendar - open the interactive calendar to browse months and pick a date\n"
    "/addevent Title | YYYY-MM-DD | HH:MM | note - add an event directly "
    "(time and note are optional)\n"
    "/myevents [YYYY-MM] - list your events (defaults to current month)\n"
    "/delete <id> - delete an event by its id (shown in /myevents)\n"
    "/image [YYYY-MM] - get a visual calendar image for a month, with dots on days that have events\n"
    "/export - download all your events as a .ics file (importable into Google/Apple/Outlook calendars)\n"
    "/help - show this message"
)


# ---------- basic commands ----------

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to InstantCalendar_Bot!\n\n" + HELP_TEXT, parse_mode="Markdown"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


# ---------- interactive calendar ----------

async def calendar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = date.today()
    user_id = update.effective_user.id
    markup = build_calendar(today.year, today.month, user_id)
    await update.message.reply_text(
        "Tap a date to select it (days marked with * have saved events):",
        reply_markup=markup,
    )


async def calendar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    action, year, month, day = parse_callback(query.data)

    if action == "IGNORE":
        return

    if action in ("PREV", "NEXT"):
        delta = -1 if action == "PREV" else 1
        year, month = shift_month(year, month, delta)
        markup = build_calendar(year, month, user_id)
        await query.edit_message_reply_markup(reply_markup=markup)
        return

    if action == "DAY":
        selected = date(year, month, day).isoformat()
        context.user_data["pending_event_date"] = selected
        existing = db.get_events_for_day(user_id, selected)

        lines = [f"Selected *{selected}*."]
        if existing:
            lines.append("\nExisting events that day:")
            for e in existing:
                t = f" {e['event_time']}" if e["event_time"] else ""
                lines.append(f"  • #{e['id']}{t} — {e['title']}")
        lines.append(
            "\nTo add an event for this date, reply with:\n"
            "`Title | HH:MM | note`\n(time and note are optional, e.g. just `Dentist appointment`)"
        )
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")


# ---------- adding events ----------

def _parse_event_text(text: str, event_date: str):
    parts = [p.strip() for p in text.split("|")]
    title = parts[0]
    event_time = None
    note = None
    if len(parts) > 1 and parts[1]:
        try:
            datetime.strptime(parts[1], "%H:%M")
            event_time = parts[1]
        except ValueError:
            raise ValueError("Time must be in HH:MM 24-hour format, e.g. 14:30")
    if len(parts) > 2 and parts[2]:
        note = parts[2]
    if not title:
        raise ValueError("Event title cannot be empty")
    return title, event_time, note


async def pending_date_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles free-text replies after a date was picked via /calendar."""
    pending = context.user_data.get("pending_event_date")
    if not pending:
        return  # not in the middle of adding an event via calendar; ignore

    user_id = update.effective_user.id
    try:
        title, event_time, note = _parse_event_text(update.message.text, pending)
    except ValueError as exc:
        await update.message.reply_text(f"Couldn't parse that: {exc}\nTry again, e.g. `Team sync | 10:00`", parse_mode="Markdown")
        return

    event_id = db.add_event(user_id, title, pending, event_time, note)
    context.user_data.pop("pending_event_date", None)
    await update.message.reply_text(f"Saved event #{event_id}: *{title}* on {pending}" + (f" at {event_time}" if event_time else ""), parse_mode="Markdown")


async def addevent_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/addevent Title | YYYY-MM-DD | HH:MM | note"""
    raw = " ".join(context.args)
    if not raw or "|" not in raw:
        await update.message.reply_text(
            "Usage:\n`/addevent Title | YYYY-MM-DD | HH:MM | note`\n"
            "Time and note are optional.\nExample:\n`/addevent Dentist | 2026-08-03 | 09:30`",
            parse_mode="Markdown",
        )
        return

    parts = [p.strip() for p in raw.split("|")]
    title = parts[0]
    if len(parts) < 2 or not parts[1]:
        await update.message.reply_text("You must include a date in YYYY-MM-DD format.")
        return

    try:
        event_date = datetime.strptime(parts[1], "%Y-%m-%d").date().isoformat()
    except ValueError:
        await update.message.reply_text("Date must be in YYYY-MM-DD format, e.g. 2026-08-03")
        return

    event_time = None
    if len(parts) > 2 and parts[2]:
        try:
            datetime.strptime(parts[2], "%H:%M")
            event_time = parts[2]
        except ValueError:
            await update.message.reply_text("Time must be in HH:MM 24-hour format, e.g. 14:30")
            return

    note = parts[3] if len(parts) > 3 and parts[3] else None

    if not title:
        await update.message.reply_text("Event title cannot be empty.")
        return

    user_id = update.effective_user.id
    event_id = db.add_event(user_id, title, event_date, event_time, note)
    await update.message.reply_text(
        f"Saved event #{event_id}: *{title}* on {event_date}" + (f" at {event_time}" if event_time else ""),
        parse_mode="Markdown",
    )


# ---------- listing / deleting ----------

async def myevents_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = date.today()

    if context.args:
        try:
            year, month = map(int, context.args[0].split("-"))
        except ValueError:
            await update.message.reply_text("Usage: /myevents [YYYY-MM]")
            return
    else:
        year, month = today.year, today.month

    events = db.get_events_for_month(user_id, year, month)
    if not events:
        await update.message.reply_text(f"No events found for {year}-{month:02d}.")
        return

    lines = [f"*Events for {year}-{month:02d}:*"]
    for e in events:
        t = f" {e['event_time']}" if e["event_time"] else ""
        note = f" — _{e['note']}_" if e["note"] else ""
        lines.append(f"#{e['id']} • {e['event_date']}{t} — {e['title']}{note}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /delete <event_id> (see the id in /myevents)")
        return
    try:
        event_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Event id must be a number.")
        return

    user_id = update.effective_user.id
    ok = db.delete_event(event_id, user_id)
    if ok:
        await update.message.reply_text(f"Deleted event #{event_id}.")
    else:
        await update.message.reply_text("No event with that id found (or it isn't yours).")


# ---------- image calendar ----------

async def image_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = date.today()
    if context.args:
        try:
            year, month = map(int, context.args[0].split("-"))
        except ValueError:
            await update.message.reply_text("Usage: /image [YYYY-MM]")
            return
    else:
        year, month = today.year, today.month

    user_id = update.effective_user.id
    buf = generate_month_image(year, month, user_id)
    await update.message.reply_photo(photo=buf, caption=f"{year}-{month:02d}")


# ---------- ics export ----------

async def export_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    events = db.get_all_events(user_id)
    if not events:
        await update.message.reply_text("You don't have any events saved yet.")
        return
    buf = build_ics(events, calendar_name=f"InstantCalendar-{user_id}")
    await update.message.reply_document(document=buf, filename="instantcalendar_events.ics")
