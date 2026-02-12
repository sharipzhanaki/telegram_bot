from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


def yes_no_keyboard() -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("Да"), KeyboardButton("Нет"))
    return markup


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
