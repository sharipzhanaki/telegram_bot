import html
import json
from datetime import datetime
from telebot.types import Message

from loader import bot
from database.models import get_user_history
from utils.misc.hotel_card import format_hotel_card


def _parse_nights(dates_str: str) -> int:
    """Возвращает число ночей из строки вида '2026-03-25 - 2026-03-30'."""
    try:
        parts = dates_str.split(" - ")
        d1 = datetime.strptime(parts[0].strip(), "%Y-%m-%d").date()
        d2 = datetime.strptime(parts[1].strip(), "%Y-%m-%d").date()
        return max((d2 - d1).days, 1)
    except Exception:
        return 0


@bot.message_handler(commands=["history"])
def command_history(message: Message) -> None:
    history = get_user_history(user_id=message.from_user.id, limit=5)
    if not history:
        bot.reply_to(message, "История запросов пуста.")
        return
    for record in history:
        try:
            params = json.loads(record.request_params)
            hotels = json.loads(record.hotels_json)
        except Exception:
            params = {}
            hotels = []
        city = params.get("city_name")
        dates = params.get("dates_str")
        nights = _parse_nights(dates) if dates else 0

        header_lines = [
            f"<b>Дата поиска:</b> {record.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"<b>Команда:</b> /{record.command}",
        ]
        if city:
            header_lines.append(f"<b>Город:</b> {html.escape(city)}")
        if dates:
            header_lines.append(f"<b>Даты:</b> {html.escape(dates)}")

        if not hotels:
            header_lines.append("Отели не найдены.")
            bot.send_message(message.chat.id, "\n".join(header_lines), parse_mode="HTML")
            continue

        bot.send_message(message.chat.id, "\n".join(header_lines), parse_mode="HTML")
        for hotel in hotels[:3]:
            text = format_hotel_card(hotel, nights=nights, adults=params.get("adults", 1))
            bot.send_message(message.chat.id, text, parse_mode="HTML")
