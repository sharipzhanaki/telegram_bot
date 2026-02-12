from loader import bot
from telebot import custom_filters
from telebot.handler_backends import StatesGroup, State
from utils.logger import logger
from telebot.storage import StateMemoryStorage

state_storage = StateMemoryStorage()


class LowPriceStates(StatesGroup):
    """Состояния сценария команды /lowprice"""
    logger.info('Init LowPriceStates')
    city = State()
    cities = State()
    adults = State()
    count_hotels = State()
    min_price = State()
    max_price = State()
    photo = State()
    count_photo = State()
    start_date = State()
    end_date = State()


class GuestRatingStates(StatesGroup):
    """Состояния сценария команды /guest_rating"""
    logger.info('Init GuestRatingStates')
    city = State()
    cities = State()
    adults = State()
    count_hotels = State()
    photo = State()
    count_photo = State()
    start_date = State()
    end_date = State()


class BestDealStates(StatesGroup):
    """Состояния сценария команды /bestdeal"""
    logger.info('Init BestDealStates')
    city = State()
    cities = State()
    adults = State()
    count_hotels = State()
    photo = State()
    count_photo = State()
    start_date = State()
    end_date = State()
    min_price = State()
    max_price = State()
    max_distance = State()


bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.add_custom_filter(custom_filters.IsDigitFilter())
