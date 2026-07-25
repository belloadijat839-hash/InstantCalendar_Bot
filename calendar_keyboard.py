"""
Builds an interactive inline-keyboard calendar (date picker) and parses
the callback data it produces. This is the "tap a date" UI for /calendar.

Callback data format (kept short - Telegram limits callback_data to 64 bytes):
    "cal|ACTION|YEAR|MONTH|DAY"

ACTION is one of: IGNORE, DAY, PREV, NEXT
"""

import calendar
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.database import days_with_events_in_month

CALLBACK_PREFIX = "cal"


def build_calendar(year: int, month: int, user_id: int) -> InlineKeyboardMarkup:
    markup = []

    # Header row: month/year label (not clickable) between prev/next arrows
    month_name = calendar.month_name[month]
    header = [
        InlineKeyboardButton("<", callback_data=f"{CALLBACK_PREFIX}|PREV|{year}|{month}|0"),
        InlineKeyboardButton(f"{month_name} {year}", callback_data=f"{CALLBACK_PREFIX}|IGNORE|{year}|{month}|0"),
        InlineKeyboardButton(">", callback_data=f"{CALLBACK_PREFIX}|NEXT|{year}|{month}|0"),
    ]
    markup.append(header)

    # Weekday header
    markup.append(
        [InlineKeyboardButton(day, callback_data=f"{CALLBACK_PREFIX}|IGNORE|{year}|{month}|0")
         for day in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]]
    )

    marked_days = days_with_events_in_month(user_id, year, month)

    for week in calendar.monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data=f"{CALLBACK_PREFIX}|IGNORE|{year}|{month}|0"))
            else:
                label = f"{day}*" if day in marked_days else str(day)
                row.append(
                    InlineKeyboardButton(label, callback_data=f"{CALLBACK_PREFIX}|DAY|{year}|{month}|{day}")
                )
        markup.append(row)

    return InlineKeyboardMarkup(markup)


def parse_callback(data: str):
    """Returns (action, year, month, day) parsed from callback_data."""
    _, action, year, month, day = data.split("|")
    return action, int(year), int(month), int(day)


def shift_month(year: int, month: int, delta: int):
    """Move `delta` months forward/backward, handling year rollover."""
    m = month - 1 + delta
    year += m // 12
    month = m % 12 + 1
    return year, month
