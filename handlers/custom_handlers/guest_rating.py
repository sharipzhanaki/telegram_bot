from datetime import datetime
from telebot.types import Message

from loader import bot
from states.search_states import GuestRatingStates
from keyboards.inline.cities import cities_keyboard
from keyboards.reply.common import yes_no_keyboard, remove_keyboard
from keyboards.calendar.calendar_kb import create_calendar
from utils.api.locations_api import search_cities
from utils.api.hotels_api import search_hotels_guest_rating
from utils.misc.hotel_card import format_hotel_card
from database.models import save_history


@bot.message_handler(commands=["guest_rating"])
def command_guest_rating(message: Message) -> None:
    bot.set_state(message.from_user.id, GuestRatingStates.city, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data.clear()
    bot.reply_to(message, "Введите город, в котором искать популярные отели.")


@bot.message_handler(state=GuestRatingStates.city)
def handle_city(message: Message) -> None:
    city_query = message.text.strip()
    if not city_query:
        bot.reply_to(message, "Введите название города.")
        return
    cities = search_cities(city_query)
    if not cities:
        bot.reply_to(message, "Город не найден. Попробуйте другое название.")
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["cities_map"] = {c["destination_id"]: c["caption"] for c in cities}
    bot.set_state(message.from_user.id, GuestRatingStates.cities, message.chat.id)
    bot.send_message(message.chat.id, "Уточните пожалуйста город:", reply_markup=cities_keyboard(cities))


@bot.message_handler(state=GuestRatingStates.adults)
def handle_adults(message: Message) -> None:
    text = message.text.strip()
    if not text.isdigit():
        bot.reply_to(message, "Введите число 1 или 2.")
        return
    adults = int(text)
    if adults not in (1, 2):
        bot.reply_to(message, "Пока поддерживаются только 1 или 2 взрослых.")
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["adults"] = adults
    bot.set_state(message.from_user.id, GuestRatingStates.count_hotels, message.chat.id)
    bot.send_message(message.chat.id, "Сколько отелей показать (1–10)?")


@bot.message_handler(state=GuestRatingStates.count_hotels)
def handle_count_hotels(message: Message) -> None:
    text = message.text.strip()
    if not text.isdigit():
        bot.reply_to(message, "Введите число от 1 до 10.")
        return
    count = int(text)
    if not (1 <= count <= 10):
        bot.reply_to(message, "Количество отелей должно быть от 1 до 10.")
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["hotels_count"] = count
    bot.set_state(message.from_user.id, GuestRatingStates.min_price, message.chat.id)
    bot.send_message(
        message.chat.id,
        "Введите минимальную цену за ночь (целое число, 0 если не важно):",
        reply_markup=remove_keyboard(),
    )


@bot.message_handler(state=GuestRatingStates.min_price)
def handle_min_price(message: Message) -> None:
    text = message.text.strip()
    if not text.isdigit():
        bot.reply_to(message, "Введите минимальную цену целым числом (0 если не важно).")
        return
    price_min = int(text)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["price_min"] = price_min if price_min > 0 else None
    bot.set_state(message.from_user.id, GuestRatingStates.max_price, message.chat.id)
    bot.send_message(
        message.chat.id,
        "Введите максимальную цену за ночь (целое число, 0 если не важно):",
    )


@bot.message_handler(state=GuestRatingStates.max_price)
def handle_max_price(message: Message) -> None:
    text = message.text.strip()
    if not text.isdigit():
        bot.reply_to(message, "Введите максимальную цену целым числом (0 если не важно).")
        return
    price_max = int(text)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        price_min = data.get("price_min")
        if price_max != 0 and price_min is not None and price_max <= price_min:
            bot.reply_to(
                message,
                "Максимальная цена должна быть больше минимальной или 0 (не ограничивать).",
            )
            return
        data["price_max"] = price_max if price_max > 0 else None
    bot.set_state(message.from_user.id, GuestRatingStates.photo, message.chat.id)
    bot.send_message(
        message.chat.id,
        "Вывести фотографии отелей?",
        reply_markup=yes_no_keyboard(),
    )


@bot.message_handler(state=GuestRatingStates.photo)
def handle_photo_need(message: Message) -> None:
    answer = message.text.strip().lower()
    with_photos = answer in ("да", "yes", "д", "y")
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["with_photos"] = with_photos
    if with_photos:
        bot.set_state(message.from_user.id, GuestRatingStates.count_photo, message.chat.id)
        bot.send_message(
            message.chat.id,
            "Сколько фотографий на каждый отель (1-5)?",
            reply_markup=remove_keyboard(),
        )
    else:
        bot.set_state(message.from_user.id, GuestRatingStates.start_date, message.chat.id)
        today = datetime.today().date()
        bot.send_message(
            message.chat.id,
            "Выберите дату заезда:",
            reply_markup=create_calendar(today.year, today.month),
        )


@bot.message_handler(state=GuestRatingStates.count_photo)
def handle_count_photo(message: Message) -> None:
    text = message.text.strip()
    if not text.isdigit():
        bot.reply_to(message, "Введите число от 1 до 5.")
        return
    count = int(text)
    if not (1 <= count <= 5):
        bot.reply_to(message, "Количество фотографий должно быть от 1 до 5.")
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["photos_count"] = count
    bot.set_state(message.from_user.id, GuestRatingStates.start_date, message.chat.id)
    today = datetime.today().date()
    bot.send_message(
        message.chat.id,
        "Выберите дату заезда:",
        reply_markup=create_calendar(today.year, today.month),
    )


def _guest_search_and_send(message: Message, data: dict) -> None:
    destination_id = data.get("destination_id")
    city_name = data.get("city_name")
    check_in = data.get("check_in")
    check_out = data.get("check_out")
    hotels_count = data.get("hotels_count", 5)
    with_photos = data.get("with_photos", False)
    photos_count = data.get("photos_count", 0)
    price_min = data.get("price_min")
    price_max = data.get("price_max")
    adults = data.get("adults", 1)
    if not destination_id:
        bot.send_message(message.chat.id, "Город не выбран. Начните поиск заново (/guest_rating).")
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    hotels = search_hotels_guest_rating(
        region_id=destination_id,
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        results_size=50,
        min_price_per_night=price_min,
        max_price_per_night=price_max,
    )
    hotels = hotels[:hotels_count]
    if not hotels:
        bot.send_message(message.chat.id, "Отели не найдены по заданным параметрам.")
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    params_for_history = {
        "city_name": city_name,
        "dates_str": f"{check_in} - {check_out}",
        "mode": "guest_rating",
        "hotels_count": hotels_count,
        "with_photos": with_photos,
        "price_min": price_min,
        "price_max": price_max,
        "adults": adults,
    }
    save_history(
        user_id=message.from_user.id, 
        command="guest_rating", 
        params=params_for_history, 
        hotels=hotels
    )
    nights = (check_out - check_in).days or 1

    for hotel in hotels:
        text = format_hotel_card(
            hotel,
            nights=nights,
            adults=adults,
            check_in=check_in,
            check_out=check_out,
        )
        bot.send_message(message.chat.id, text, parse_mode="HTML")

        if with_photos and photos_count > 0:
            photo_urls = hotel.get("photo_urls") or []
            for url in photo_urls[:photos_count]:
                bot.send_photo(message.chat.id, photo=url)

    bot.delete_state(message.from_user.id, message.chat.id)
