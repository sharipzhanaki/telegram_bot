import os
from dotenv import load_dotenv, find_dotenv

if not find_dotenv():
    exit("Переменные окружения не загружены т.к отсутствует файл .env")
else:
    load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
RAPID_API_KEY = os.getenv("RAPID_API_KEY")
DB_NAME = os.getenv("DB_NAME")
RAPID_API_HOST = "hotels4.p.rapidapi.com"
BASE_URL = f"https://{RAPID_API_HOST}"

DEFAULT_COMMANDS = (
    ("start", "Запустить бота"),
    ("help", "Вывести справку"),
    ("lowprice", "Топ самых дешёвых отелей"),
    ("guest_rating", "Популярные отели по оценкам гостей"),
    ("bestdeal", "Лушее предложение по расстоянию до центра"),
    ("history", "История запросов"),
)
