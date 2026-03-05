from datetime import date, timedelta
from types import SimpleNamespace

from telebot.types import CallbackQuery

from loader import bot


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_min_date(call: CallbackQuery, state: str) -> date:
    """Return the earliest selectable date based on the current FSM state."""
    if "end_date" in state:
        with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
            check_in = data.get("check_in")
        if check_in:
            return check_in + timedelta(days=1)
    return date.today()


# ── Callbacks ─────────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: call.data == "cal:ignore")
def handle_cal_ignore(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("cal:nav:"))
def handle_cal_nav(call: CallbackQuery) -> None:
    from keyboards.calendar.calendar_kb import create_calendar

    parts = call.data.split(":")
    year, month = int(parts[2]), int(parts[3])

    state = bot.get_state(call.from_user.id, call.message.chat.id) or ""
    min_date = _get_min_date(call, state)

    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=create_calendar(year, month, min_date=min_date),
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("cal:day:"))
def handle_cal_day(call: CallbackQuery) -> None:
    from keyboards.calendar.calendar_kb import create_calendar
    from states.search_states import LowPriceStates, GuestRatingStates, BestDealStates

    parts = call.data.split(":")
    selected = date(int(parts[2]), int(parts[3]), int(parts[4]))

    state = bot.get_state(call.from_user.id, call.message.chat.id) or ""

    # ── Check-in selection ────────────────────────────────────────────────────
    if "start_date" in state:
        if selected < date.today():
            bot.answer_callback_query(
                call.id, "Дата заезда не может быть в прошлом.", show_alert=True
            )
            return

        with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
            data["check_in"] = selected

        # Advance FSM to end_date
        if "LowPriceStates" in state:
            bot.set_state(call.from_user.id, LowPriceStates.end_date, call.message.chat.id)
        elif "GuestRatingStates" in state:
            bot.set_state(call.from_user.id, GuestRatingStates.end_date, call.message.chat.id)
        elif "BestDealStates" in state:
            bot.set_state(call.from_user.id, BestDealStates.end_date, call.message.chat.id)

        min_checkout = selected + timedelta(days=1)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Дата заезда: {selected}\nВыберите дату выезда:",
            reply_markup=create_calendar(
                min_checkout.year, min_checkout.month, min_date=min_checkout
            ),
        )
        bot.answer_callback_query(call.id)

    # ── Check-out selection ───────────────────────────────────────────────────
    elif "end_date" in state:
        with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
            check_in = data.get("check_in")

        if check_in and selected <= check_in:
            bot.answer_callback_query(
                call.id, "Дата выезда должна быть позже даты заезда.", show_alert=True
            )
            return

        with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
            data["check_out"] = selected

        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None,
            )
        except Exception:
            pass

        bot.answer_callback_query(call.id)

        # Bestdeal needs price/distance questions before search
        if "BestDealStates" in state:
            bot.set_state(call.from_user.id, BestDealStates.min_price, call.message.chat.id)
            bot.send_message(
                call.message.chat.id, "Введите минимальную цену за ночь (целое число):"
            )
        else:
            # Lowprice / GuestRating — dispatch to search directly
            fake_msg = SimpleNamespace(chat=call.message.chat, from_user=call.from_user)
            with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
                data_copy = dict(data)

            if "LowPriceStates" in state:
                from handlers.custom_handlers.lowprice import _lowprice_search_and_send
                _lowprice_search_and_send(fake_msg, data_copy)
            elif "GuestRatingStates" in state:
                from handlers.custom_handlers.guest_rating import _guest_search_and_send
                _guest_search_and_send(fake_msg, data_copy)

    else:
        bot.answer_callback_query(call.id)
