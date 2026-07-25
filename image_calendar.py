"""
Renders a monthly calendar as a PNG image using Pillow, with a dot marker
under any day that has one or more saved events.
"""

import calendar
import io
from PIL import Image, ImageDraw, ImageFont

from bot.database import days_with_events_in_month

WIDTH, HEIGHT = 700, 650
MARGIN = 20
HEADER_H = 80
CELL_W = (WIDTH - 2 * MARGIN) // 7
CELL_H = (HEIGHT - HEADER_H - 2 * MARGIN) // 7

BG = (255, 255, 255)
GRID = (220, 220, 220)
TEXT = (30, 30, 30)
MUTED = (190, 190, 190)
ACCENT = (0, 122, 255)
HEADER_BG = (0, 122, 255)
HEADER_TEXT = (255, 255, 255)


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def generate_month_image(year: int, month: int, user_id: int) -> io.BytesIO:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    # Header banner
    draw.rectangle([0, 0, WIDTH, HEADER_H], fill=HEADER_BG)
    title = f"{calendar.month_name[month]} {year}"
    title_font = _font(32, bold=True)
    tw = draw.textlength(title, font=title_font)
    draw.text(((WIDTH - tw) / 2, 22), title, font=title_font, fill=HEADER_TEXT)

    weekday_font = _font(18, bold=True)
    day_font = _font(20)
    dot_font = _font(12)

    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    y = HEADER_H + MARGIN
    for i, wd in enumerate(weekdays):
        x = MARGIN + i * CELL_W
        w = draw.textlength(wd, font=weekday_font)
        draw.text((x + (CELL_W - w) / 2, y), wd, font=weekday_font, fill=TEXT)

    marked_days = days_with_events_in_month(user_id, year, month)

    grid_top = y + 35
    weeks = calendar.monthcalendar(year, month)
    for row_i, week in enumerate(weeks):
        for col_i, day in enumerate(week):
            x0 = MARGIN + col_i * CELL_W
            y0 = grid_top + row_i * CELL_H
            x1, y1 = x0 + CELL_W, y0 + CELL_H
            draw.rectangle([x0, y0, x1, y1], outline=GRID)

            if day == 0:
                continue

            day_str = str(day)
            color = TEXT
            draw.text((x0 + 8, y0 + 6), day_str, font=day_font, fill=color)

            if day in marked_days:
                cx = x0 + CELL_W - 16
                cy = y0 + 16
                r = 5
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACCENT)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    buf.name = f"calendar_{year}_{month:02d}.png"
    return buf
