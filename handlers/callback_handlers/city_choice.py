from telebot.types import CallbackQuery

from loader import bot
from states.search_states import LowPriceStates, GuestRatingStates, BestDealStates


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("city:"),
    state=LowPriceStates.cities,
)
def lowprice_city_choice(call: CallbackQuery) -> None:
    _handle_city_choice(call, LowPriceStates, "lowprice")


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("city:"),
    state=GuestRatingStates.cities,
)
def guest_rating_city_choice(call: CallbackQuery) -> None:
    _handle_city_choice(call, GuestRatingStates, "guest_rating")


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("city:"),
    state=BestDealStates.cities,
)
def bestdeal_city_choice(call: CallbackQuery) -> None:
    _handle_city_choice(call, BestDealStates, "bestdeal")


def _handle_city_choice(call: CallbackQuery, states_cls, command_name: str) -> None:
    destination_id = call.data.split(":", 1)[1]
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        cities_map = data.get("cities_map", {})
        city_name = cities_map.get(destination_id, "выбранный город")
        data["destination_id"] = destination_id
        data["city_name"] = city_name
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None,
        )
    except Exception:
        pass
    if states_cls is LowPriceStates:
        bot.set_state(call.from_user.id, LowPriceStates.adults, call.message.chat.id)
    elif states_cls is GuestRatingStates:
        bot.set_state(call.from_user.id, GuestRatingStates.adults, call.message.chat.id)
    elif states_cls is BestDealStates:
        bot.set_state(call.from_user.id, BestDealStates.adults, call.message.chat.id)
    bot.send_message(call.message.chat.id, f"Город выбран: {city_name}\nСколько гостей будет проживать в номере?")
