import calendar as _cal
from datetime import date

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

MONTHS_RU = (
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
)
DAYS_SHORT = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")


def create_calendar(year: int, month: int, *, min_date: date = None) -> InlineKeyboardMarkup:
    """Build an inline calendar keyboard for the given year/month.

    Dates before min_date are shown as non-clickable (·N).
    Today is shown as [N]. Future dates are clickable.

    Callback data:
        cal:nav:YEAR:MONTH   — navigate to another month
        cal:day:YEAR:MONTH:DAY — a date was selected
        cal:ignore           — non-interactive cell
    """
    if min_date is None:
        min_date = date.today()

    kb = InlineKeyboardMarkup(row_width=7)
    today = date.today()

    # ── Navigation row ──────────────────────────────────────────────────────
    prev_month = month - 1 or 12
    prev_year = year - (1 if month == 1 else 0)
    first_of_prev = date(prev_year, prev_month, 1)

    next_month = month % 12 + 1
    next_year = year + (1 if month == 12 else 0)

    # Hide "previous" button if that month is entirely in the past
    if first_of_prev >= min_date.replace(day=1):
        prev_btn = InlineKeyboardButton("◀", callback_data=f"cal:nav:{prev_year}:{prev_month}")
    else:
        prev_btn = InlineKeyboardButton(" ", callback_data="cal:ignore")

    header_btn = InlineKeyboardButton(
        f"{MONTHS_RU[month - 1]} {year}", callback_data="cal:ignore"
    )
    next_btn = InlineKeyboardButton("▶", callback_data=f"cal:nav:{next_year}:{next_month}")

    kb.row(prev_btn, header_btn, next_btn)

    # ── Day-name header ──────────────────────────────────────────────────────
    kb.row(*[InlineKeyboardButton(d, callback_data="cal:ignore") for d in DAYS_SHORT])

    # ── Weeks ────────────────────────────────────────────────────────────────
    for week in _cal.monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="cal:ignore"))
            else:
                d = date(year, month, day)
                if d < min_date:
                    row.append(InlineKeyboardButton(f"·{day}", callback_data="cal:ignore"))
                elif d == today:
                    row.append(InlineKeyboardButton(f"[{day}]", callback_data=f"cal:day:{year}:{month}:{day}"))
                else:
                    row.append(InlineKeyboardButton(str(day), callback_data=f"cal:day:{year}:{month}:{day}"))
        kb.row(*row)

    return kb
