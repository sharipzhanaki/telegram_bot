from datetime import datetime
from telebot.types import Message

from loader import bot
from states.search_states import GuestRatingStates
from keyboards.inline.cities import cities_keyboard
from keyboards.reply.common import yes_no_keyboard, remove_keyboard
from utils.api.locations_api import search_cities
from utils.api.hotels_api import search_hotels_guest_rating
from utils.api.photos_api import get_hotel_photos
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
    bot.set_state(message.from_user.id, GuestRatingStates.photo, message.chat.id)
    bot.send_message(message.chat.id, "Вывести фотографий отелей?", reply_markup=yes_no_keyboard())


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
        bot.send_message(
            message.chat.id,
            "Введите дату заезда в формате YYYY-MM-DD:",
            reply_markup=remove_keyboard(),
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
    bot.send_message(message.chat.id, "Введите дату заезда в формате YYYY-MM-DD:")


@bot.message_handler(state=GuestRatingStates.start_date)
def handle_start_date(message: Message) -> None:
    text = message.text.strip()
    try:
        check_in = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        bot.reply_to(message, "Неверный формат. Используйте YYYY-MM-DD.")
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["check_in"] = check_in
    bot.set_state(message.from_user.id, GuestRatingStates.end_date, message.chat.id)
    bot.send_message(message.chat.id, "Введите дату выезда в формате YYYY-MM-DD:")


@bot.message_handler(state=GuestRatingStates.end_date)
def handle_end_date(message: Message) -> None:
    text = message.text.strip()
    try:
        check_out = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        bot.reply_to(message, "Неверный формат. Используйте YYYY-MM-DD.")
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        check_in = data.get("check_in")
        if check_in and check_out <= check_in:
            bot.reply_to(message, "Дата выезда должна быть позже даты заезда.")
            return
        data["check_out"] = check_out
        _guest_search_and_send(message, data)


def _guest_search_and_send(message: Message, data: dict) -> None:
    destination_id = data.get("destination_id")
    city_name = data.get("city_name")
    check_in = data.get("check_in")
    check_out = data.get("check_out")
    hotels_count = data.get("hotels_count", 5)
    with_photos = data.get("with_photos", False)
    photos_count = data.get("photos_count", 0)
    if not destination_id:
        bot.send_message(message.chat.id, "Город не выбран. Начните поиск заново (/guest_rating).")
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    hotels = search_hotels_guest_rating(
        region_id=destination_id,
        check_in=check_in,
        check_out=check_out,
        adults=1,
        results_size=hotels_count,
    )
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
    }
    save_history(user_id=message.from_user.id, command="guest_rating", params=params_for_history, hotels=hotels)
    for hotel in hotels:
        price_total = hotel.get("price_total")
        price_per_night = hotel.get("price_per_night")
        currency = hotel.get("currency") or "USD"

        price_lines = []
        if price_per_night is not None:
            price_lines.append(f"Цена за ночь: {price_per_night} {currency}")
        if price_total is not None:
            nights = (check_out - check_in).days or 1
            price_lines.append(f"Всего за {nights} ночей: {price_total} {currency}")

        lines = [
            f"Название: {hotel.get('name')}",
            f"Адрес: {hotel.get('address')}",
            *price_lines,
            f"Оценка гостей: {hotel.get('guest_rating')}",
            f"Расстояние до центра: {hotel.get('distance_center')}",
            f"Даты: {check_in} - {check_out}",
        ]
        if hotel.get("booking_url"):
            lines.append(f"Ссылка для бронирования: {hotel.get('booking_url')}")
        if hotel.get("lat") and hotel.get("lng"):
            lines.append(f"Координаты: {hotel['lat']}, {hotel['lng']}")
        bot.send_message(message.chat.id, "\n".join(lines))

        if with_photos and hotel.get("id") and photos_count > 0:
            photos = get_hotel_photos(str(hotel["id"]), limit=photos_count)
            for url in photos:
                bot.send_photo(message.chat.id, photo=url)
    bot.delete_state(message.from_user.id, message.chat.id)
