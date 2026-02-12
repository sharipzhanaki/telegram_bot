from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict


def cities_keyboard(cities: List[Dict[str, str]]) -> InlineKeyboardMarkup:
    """Клавиатура для выбора города."""
    markup = InlineKeyboardMarkup()
    for city in cities:
        destination_id = city["destination_id"]
        text = city["caption"]
        markup.add(
            InlineKeyboardButton(
                text=text,
                callback_data=f"city:{destination_id}",
            )
        )
    return markup
