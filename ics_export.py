"""
Builds a minimal but valid .ics (iCalendar) file from a list of event rows,
without pulling in an extra dependency.
"""

import io
from datetime import datetime


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def build_ics(events, calendar_name: str = "InstantCalendar") -> io.BytesIO:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//InstantCalendar_Bot//EN",
        f"X-WR-CALNAME:{_escape(calendar_name)}",
        "CALSCALE:GREGORIAN",
    ]

    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    for e in events:
        date_part = e["event_date"].replace("-", "")
        if e["event_time"]:
            time_part = e["event_time"].replace(":", "") + "00"
            dtstart = f"DTSTART:{date_part}T{time_part}"
        else:
            dtstart = f"DTSTART;VALUE=DATE:{date_part}"

        lines += [
            "BEGIN:VEVENT",
            f"UID:instantcalendar-{e['id']}@telegram-bot",
            f"DTSTAMP:{now_stamp}",
            dtstart,
            f"SUMMARY:{_escape(e['title'])}",
        ]
        if e["note"]:
            lines.append(f"DESCRIPTION:{_escape(e['note'])}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")

    content = "\r\n".join(lines) + "\r\n"
    buf = io.BytesIO(content.encode("utf-8"))
    buf.name = "instantcalendar_events.ics"
    return buf
