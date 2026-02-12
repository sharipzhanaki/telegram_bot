import json
from telebot.types import Message

from loader import bot
from database.models import get_user_history


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
        lines = [
            f"Дата поиска: {record.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"Команда: /{record.command}",
        ]
        city = params.get("city_name")
        dates = params.get("dates_str")
        if city:
            lines.append(f"Город: {city}")
        if dates:
            lines.append(f"Даты: {dates}")
        if not hotels:
            lines.append("Отели не найдены.")
            bot.send_message(message.chat.id, "\n".join(lines))
            continue
        for hotel in hotels[:3]:
            lines.append("")
            lines.append(f"Название: {hotel.get('name')}")
            lines.append(f"Адрес: {hotel.get('address')}")
            lines.append(f"Цена: {hotel.get('price')}")
            if hotel.get("booking_url"):
                lines.append(f"Бронирование: {hotel.get('booking_url')}")
            if hotel.get("lat") and hotel.get("lng"):
                lines.append(f"Координаты: {hotel['lat']}, {hotel['lng']}")
        bot.send_message(message.chat.id, "\n".join(lines))
