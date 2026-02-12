import json
from datetime import datetime
from config_data import config

from peewee import (
    Model,
    SqliteDatabase,
    AutoField,
    IntegerField,
    CharField,
    DateTimeField,
    TextField,
)

db = SqliteDatabase(config.DB_NAME)


class BaseModel(Model):
    class Meta:
        database = db


class History(BaseModel):
    """История поисков пользователя."""
    id = AutoField()
    user_id = IntegerField()
    command = CharField(max_length=50)
    created_at = DateTimeField(default=datetime.utcnow)
    request_params = TextField()
    hotels_json = TextField()


def init_db() -> None:
    db.connect(reuse_if_open=True)
    db.create_tables([History])


def save_history(user_id: int, command: str, params: dict, hotels: list) -> None:
    """Сохранение результата поиска в историю."""
    History.create(
        user_id=user_id,
        command=command,
        request_params=json.dumps(params, ensure_ascii=False),
        hotels_json=json.dumps(hotels, ensure_ascii=False),
    )


def get_user_history(user_id: int, limit: int = 5) -> list[History]:
    """Получить последние limit записей истории пользователя."""
    query = (
        History.select()
        .where(History.user_id == user_id)
        .order_by(History.created_at.desc())
        .limit(limit)
    )
    return list(query)
