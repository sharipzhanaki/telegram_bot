from typing import List

from .base_client import api_get
from utils.logger import logger

PHOTOS_PATH = "properties/get-hotel-photos"


def get_hotel_photos(hotel_id: str, limit: int = 5) -> List[str]:
    """
    Возвращает список URL фотографий отеля.
    Если API недоступно или структура изменилась — возвращает [].
    """
    data = api_get(PHOTOS_PATH, params={"id": hotel_id})
    if not data:
        return []

    photos: List[str] = []
    try:
        images = data.get("hotelImages") or []
        for img in images:
            base = img.get("baseUrl")
            if not base:
                continue
            # как в типичном дипломном решении: заменяем плейсхолдер размера
            url = base.replace("_{size}", "_z")
            photos.append(url)
            if len(photos) >= limit:
                break
    except Exception:
        logger.exception("get_hotel_photos: ошибка парсинга фотографий отеля %s", hotel_id)
        return []

    return photos
