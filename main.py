from loader import bot
import handlers  # noqa
from utils.set_bot_commands import set_default_commands
from database.models import init_db


if __name__ == "__main__":
    init_db()
    set_default_commands(bot)
    bot.infinity_polling()
