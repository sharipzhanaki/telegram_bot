from datetime import datetime
from telebot.types import Message

from loader import bot
from states.search_states import BestDealStates
from keyboards.inline.cities import cities_keyboard
from keyboards.reply.common import yes_no_keyboard, remove_keyboard
from utils.api.locations_api import search_cities
from utils.api.hotels_api import search_hotels_bestdeal
from utils.api.photos_api import get_hotel_photos
from database.models import save_history


@bot.message_handler(commands=["bestdeal"])
def command_bestdeal(message: Message) -> None:
    bot.set_state(message.from_user.id, BestDealStates.city, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data.clear()
    bot.reply_to(message, "Введите город, в котором искать лучшие предложения.")


@bot.message_handler(state=BestDealStates.city)
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
    bot.set_state(message.from_user.id, BestDealStates.cities, message.chat.id)
    bot.send_message(message.chat.id, "Уточните пожалуйста город:", reply_markup=cities_keyboard(cities))


@bot.message_handler(state=BestDealStates.adults)
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
    bot.set_state(message.from_user.id, BestDealStates.count_hotels, message.chat.id)
    bot.send_message(message.chat.id, "Сколько отелей показать (1–10)?")


@bot.message_handler(state=BestDealStates.count_hotels)
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
    bot.set_state(message.from_user.id, BestDealStates.photo, message.chat.id)
    bot.send_message(message.chat.id, "Вывести фотографий отелей?", reply_markup=yes_no_keyboard())


@bot.message_handler(state=BestDealStates.photo)
def handle_photo_need(message: Message) -> None:
    answer = message.text.strip().lower()
    with_photos = answer in ("да", "yes", "д", "y")
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["with_photos"] = with_photos
    if with_photos:
        bot.set_state(message.from_user.id, BestDealStates.count_photo, message.chat.id)
        bot.send_message(
            message.chat.id,
            "Сколько фотографий на каждый отель (1-5)?",
            reply_markup=remove_keyboard(),
        )
    else:
        bot.set_state(message.from_user.id, BestDealStates.start_date, message.chat.id)
        bot.send_message(
            message.chat.id,
            "Введите дату заезда в формате YYYY-MM-DD:",
            reply_markup=remove_keyboard(),
        )


@bot.message_handler(state=BestDealStates.count_photo)
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
    bot.set_state(message.from_user.id, BestDealStates.start_date, message.chat.id)
    bot.send_message(message.chat.id, "Введите дату заезда в формате YYYY-MM-DD:")


@bot.message_handler(state=BestDealStates.start_date)
def handle_start_date(message: Message) -> None:
    text = message.text.strip()
    try:
        check_in = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        bot.reply_to(message, "Неверный формат. Используйте YYYY-MM-DD.")
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["check_in"] = check_in
    bot.set_state(message.from_user.id, BestDealStates.end_date, message.chat.id)
    bot.send_message(message.chat.id, "Введите дату выезда в формате YYYY-MM-DD:")


@bot.message_handler(state=BestDealStates.end_date)
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
    bot.set_state(message.from_user.id, BestDealStates.min_price, message.chat.id)
    bot.send_message(message.chat.id, "Введите минимальную цену за ночь (целое число):")


@bot.message_handler(state=BestDealStates.min_price)
def handle_min_price(message: Message) -> None:
    text = message.text.strip()
    if not text.isdigit():
        bot.reply_to(message, "Введите минимальную цену целым числом.")
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["price_min"] = int(text)
    bot.set_state(message.from_user.id, BestDealStates.max_price, message.chat.id)
    bot.send_message(message.chat.id, "Введите максимальную цену за ночь (целое число):")


@bot.message_handler(state=BestDealStates.max_price)
def handle_max_price(message: Message) -> None:
    text = message.text.strip()
    if not text.isdigit():
        bot.reply_to(message, "Введите максимальную цену целым числом.")
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        price_min = data.get("price_min", 0)
        price_max = int(text)
        if price_max <= price_min:
            bot.reply_to(message, "Максимальная цена должна быть больше минимальной.")
            return
        data["price_max"] = int(text)
    bot.set_state(message.from_user.id, BestDealStates.max_distance, message.chat.id)
    bot.send_message(
        message.chat.id,
        "Введите максимальное расстояние до центра (км). Если не важно, введите 0."
    )


@bot.message_handler(state=BestDealStates.max_distance)
def handle_max_price(message: Message) -> None:
    text = message.text.strip()
    try:
        max_dist = float(text.replace(",", "."))
    except ValueError:
        bot.reply_to(message, "Введите число (можно с точкой или запятой).")
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["max_distance"] = max_dist
        _bestdeal_search_and_send(message, data)


def _bestdeal_search_and_send(message: Message, data: dict) -> None:
    destination_id = data.get("destination_id")
    city_name = data.get("city_name")
    check_in = data.get("check_in")
    check_out = data.get("check_out")
    hotels_count = data.get("hotels_count", 5)
    with_photos = data.get("with_photos", False)
    photos_count = data.get("photos_count", 0)
    price_min = data.get("price_min") or 0
    price_max = data.get("price_max") or 0
    max_distance = data.get("max_distance")
    if not destination_id:
        bot.send_message(message.chat.id, "Город не выбран. Начните поиск заново (/bestdeal).")
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    hotels = search_hotels_bestdeal(
        region_id=destination_id,
        check_in=check_in,
        check_out=check_out,
        adults=1,
        results_size=hotels_count,
        price_min=price_min,
        price_max=price_max,
    )
    if max_distance and max_distance > 0:
        filtered = []
        for h in hotels:
            dist_str = h.get("distance_center") or ""
            try:
                val = float(dist_str.split()[0].replace(",", "."))
            except Exception:
                val = None
            if val is None or val  <= max_distance:
                filtered.append(h)
        hotels = filtered
    if not hotels:
        bot.send_message(message.chat.id, "Отели не найдены по заданным параметрам.")
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    params_for_history = {
        "city_name": city_name,
        "dates_str": f"{check_in} - {check_out}",
        "mode": "bestdeal",
        "hotels_count": hotels_count,
        "with_photos": with_photos,
        "price_min": price_min,
        "price_max": price_max,
        "max_distance": max_distance,
    }
    save_history(user_id=message.from_user.id, command="bestdeal", params=params_for_history, hotels=hotels)
    for hotel in hotels:
        price_total = hotel.get("price_total") or hotel.get("price")
        price_per_night = hotel.get("price_per_night")
        currency = hotel.get("currency") or "USD"

        lines = [
            f"Название: {hotel.get('name')}",
            f"Адрес: {hotel.get('address')}",
        ]

        if price_per_night is not None:
            lines.append(f"Цена за ночь: {price_per_night:.2f} {currency}")
        if price_total is not None:
            lines.append(f"Итого за период: {price_total:.2f} {currency}")

        lines.append(f"Оценка гостей: {hotel.get('guest_rating')}")
        lines.append(f"Расстояние до центра: {hotel.get('distance_center')}")
        lines.append(f"Даты: {check_in} - {check_out}")

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
