from datetime import date
from typing import Any, Dict, List, Optional
import re

from .base_client import api_post
from utils.logger import logger


PROPERTIES_LIST_PATH = "/properties/v3/list"


def _date_to_dict(d: date) -> Dict[str, int]:
    """Преобразование даты к формату, который ожидает API."""
    return {"day": d.day, "month": d.month, "year": d.year}


def _extract_number_from_str(value: str) -> Optional[float]:
    """
    Извлекает первое число из строки.
    Примеры:
      '7,4' -> 7.4
      '10 out of 10' -> 10.0
      '$1,294 total' -> 1294.0
    """
    if not isinstance(value, str):
        return None
    # Берём первую "цифровую группу" с возможными точками/запятыми
    match = re.search(r"(\d[\d.,]*)", value)
    if not match:
        return None
    num_str = match.group(1)
    # Если есть запятая и нет точки — это либо десятичная запятая (9,2),
    # либо тысячные (1,294). Различаем по длине последнего блока.
    if "," in num_str and "." not in num_str:
        parts = num_str.split(",")
        last = parts[-1]
        if len(last) == 1:  # 9,2 -> 9.2
            num_str = num_str.replace(",", ".")
        else:  # 1,294 -> 1294
            num_str = num_str.replace(",", "")
    else:
        # В остальных случаях все запятые — разделители тысяч: 1,294.50 -> 1294.50
        num_str = num_str.replace(",", "")
    try:
        return float(num_str)
    except ValueError:
        return None


def _parse_property_card(
    card: Dict[str, Any],
    *,
    nights: int,
    region_name: Optional[str],
    is_distance_sort: bool,
) -> Dict[str, Any]:
    """
    Превращает одну LodgingCard из properties/v3/list в плоскую структуру:
    - id
    - name
    - city (по сути regionName / подпись в headingSection)
    - guest_rating, guest_rating_text
    - distance_km (для sort=DISTANCE)
    - price_total, price_nightly
    - booking_url
    - photo_url (первая фотка)
    - photo_urls (список фоток)
    """
    hotel_id = card.get("id")

    # Ссылка на бронирование
    booking_url = None
    card_link = card.get("cardLink") or {}
    resource = card_link.get("resource") or {}
    if isinstance(resource, dict):
        booking_url = resource.get("value")

    # Заголовок и "сообщения" (для DISTANCE там расстояние, для остальных — город)
    heading_section = card.get("headingSection") or {}
    name = heading_section.get("heading")

    messages = heading_section.get("messages") or []
    city: Optional[str] = None
    distance_km: Optional[float] = None

    if messages:
        text0 = (messages[0] or {}).get("text")
        if isinstance(text0, str):
            if is_distance_sort and "km from downtown" in text0:
                # Пример: "0.13 km from downtown"
                distance_km = _extract_number_from_str(text0)
            else:
                # В PRICE_LOW_TO_HIGH и REVIEW здесь обычно "London"
                city = text0

    # Если город не распарсился из headingSection, берём regionName
    if not city and region_name:
        city = region_name

    # Рейтинг гостей
    guest_rating: Optional[float] = None
    guest_rating_text: Optional[str] = None

    summary_sections = card.get("summarySections") or []
    if summary_sections:
        first_summary = summary_sections[0] or {}
        rating_section = first_summary.get("guestRatingSectionV2") or {}
        badge = rating_section.get("badge") or {}

        # badge.text: "10" или "9,2"
        guest_rating_text = badge.get("text")
        if guest_rating_text:
            guest_rating = _extract_number_from_str(guest_rating_text)

        # Запасной путь: badge.accessibility: "10 out of 10"
        if guest_rating is None:
            access = badge.get("accessibility")
            if access:
                guest_rating = _extract_number_from_str(access)

    # Цена (total и nightly)
    price_section = card.get("priceSection") or {}
    price_summary = price_section.get("priceSummary") or {}
    display_messages = price_summary.get("displayMessages") or []

    price_total: Optional[float] = None
    price_nightly: Optional[float] = None

    for block in display_messages:
        line_items = block.get("lineItems") or []
        for item in line_items:
            typename = item.get("__typename")
            if typename == "DisplayPrice":
                # Ищем роль LEAD: там "$723 total" и т.п.
                if item.get("role") == "LEAD":
                    price_data = item.get("price") or {}
                    formatted = price_data.get("formatted")
                    if formatted:
                        price_total = _extract_number_from_str(formatted)
            elif typename == "LodgingEnrichedMessage":
                # Здесь часто лежит "$136 nightly"
                value = item.get("value")
                if isinstance(value, str) and "night" in value.lower():
                    price_nightly = _extract_number_from_str(value)

    if price_nightly is None and price_total is not None and nights > 0:
        price_nightly = round(price_total / nights, 2)

    # Фото: берём несколько URL (понадобятся для with_photos)
    photo_url: Optional[str] = None
    photo_urls: List[str] = []

    media_section = card.get("mediaSection") or {}
    gallery = media_section.get("gallery") or {}
    media_items = gallery.get("media") or []
    for item in media_items:
        media = item.get("media") or {}
        url = media.get("url")
        if isinstance(url, str):
            photo_urls.append(url)
            if photo_url is None:
                photo_url = url
        if len(photo_urls) >= 10:
            break

    return {
        "id": hotel_id,
        "name": name,
        "city": city,                      # вместо адреса
        "guest_rating": guest_rating,      # float или None
        "guest_rating_text": guest_rating_text,
        "distance_km": distance_km,        # осмысленно в сортировке DISTANCE
        "price_total": price_total,        # за всё пребывание
        "price_nightly": price_nightly,    # за ночь
        "booking_url": booking_url,
        "photo_url": photo_url,
        "photo_urls": photo_urls,
    }


def _extract_properties(
    data: Dict[str, Any],
    *,
    nights: int,
    is_distance_sort: bool,
) -> List[Dict[str, Any]]:
    """
    Забирает data["data"]["propertySearch"] и превращает propertySearchListings
    в список словарей отелей.
    """
    property_search = (data.get("data") or {}).get("propertySearch") or {}

    # Полное имя региона: "London, England, United Kingdom"
    region_name = (
        property_search.get("criteria", {})
        .get("primary", {})
        .get("destination", {})
        .get("regionName")
    )

    listings = property_search.get("propertySearchListings") or []

    hotels: List[Dict[str, Any]] = []
    for card in listings:
        try:
            hotel = _parse_property_card(
                card,
                nights=nights,
                region_name=region_name,
                is_distance_sort=is_distance_sort,
            )
            hotels.append(hotel)
        except Exception:
            logger.exception("search_hotels: ошибка при разборе карточки: %r", card)

    logger.info(
        "search_hotels: получили %s отелей (без локальной фильтрации)",
        len(hotels),
    )
    return hotels


def _build_payload(
    *,
    region_id: str,
    check_in: date,
    check_out: date,
    adults: int,
    results_size: int,
    sort: str,
    min_price_total: Optional[float] = None,
    max_price_total: Optional[float] = None,
    guest_rating_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Готовит тело запроса к properties/v3/list.
    ВАЖНО: min_price_total / max_price_total — цена за ВЕСЬ период,
    а не за ночь (так работает API).
    """
    payload: Dict[str, Any] = {
        "currency": "USD",
        "eapid": 1,
        "locale": "ru_RU",
        "siteId": 300000001,
        "destination": {"regionId": region_id},
        "checkInDate": _date_to_dict(check_in),
        "checkOutDate": _date_to_dict(check_out),
        "rooms": [{"adults": adults}],
        "resultsStartingIndex": 0,
        "resultsSize": results_size,
        "sort": sort,
    }

    filters: Dict[str, Any] = {}

    # Фильтр по цене за весь период
    price_filter: Dict[str, Any] = {}
    if min_price_total is not None:
        price_filter["min"] = int(min_price_total)
    if max_price_total is not None:
        price_filter["max"] = int(max_price_total)
    if price_filter:
        filters["price"] = price_filter

    # Фильтр по рейтингу (ступенчатый: 7+, 8+, 9+)
    if guest_rating_filter:
        filters["guestRating"] = guest_rating_filter

    if filters:
        payload["filters"] = filters

    return payload


def _search_hotels(
    *,
    region_id: str,
    check_in: date,
    check_out: date,
    adults: int,
    results_size: int,
    sort: str,
    min_price_per_night: Optional[float] = None,
    max_price_per_night: Optional[float] = None,
    guest_rating_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Общая функция, которую используют lowprice / guest_rating / bestdeal.
    - sort: "PRICE_LOW_TO_HIGH" | "REVIEW" | "DISTANCE"
    - min/max_price_per_night — ограничения по цене за ночь (локальная фильтрация +
      пересчитанные фильтры для API по цене за весь период).
    - guest_rating_filter — код фильтра API: "35" (7+), "40" (8+), "45" (9+).
    """
    nights = (check_out - check_in).days
    if nights <= 0:
        raise ValueError("check_out must be later than check_in")

    # Пересчитываем ночные цены в total для API
    min_price_total: Optional[float] = None
    max_price_total: Optional[float] = None
    if min_price_per_night is not None:
        min_price_total = min_price_per_night * nights
    if max_price_per_night is not None:
        max_price_total = max_price_per_night * nights

    payload = _build_payload(
        region_id=region_id,
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        results_size=results_size,
        sort=sort,
        min_price_total=min_price_total,
        max_price_total=max_price_total,
        guest_rating_filter=guest_rating_filter,
    )

    logger.info("search_hotels: POST %s payload=%r", PROPERTIES_LIST_PATH, payload)

    try:
        # ВАЖНО: base_client.api_post(path, payload), а не json=payload
        data = api_post(PROPERTIES_LIST_PATH, payload)
    except Exception:
        logger.exception("search_hotels: ошибка при запросе к API")
        return []

    is_distance_sort = sort == "DISTANCE"
    hotels = _extract_properties(
        data,
        nights=nights,
        is_distance_sort=is_distance_sort,
    )

    # Локальная фильтрация по цене за ночь (чтобы логика бота была
    # консистентна с ожиданиями пользователя)
    def price_ok(h: Dict[str, Any]) -> bool:
        pn = h.get("price_nightly")
        if pn is None:
            return False
        if min_price_per_night is not None and pn < min_price_per_night:
            return False
        if max_price_per_night is not None and pn > max_price_per_night:
            return False
        return True

    if min_price_per_night is not None or max_price_per_night is not None:
        before = len(hotels)
        hotels = [h for h in hotels if price_ok(h)]
        logger.info(
            "search_hotels: после локальной фильтрации по цене осталось %s отелей (из %s)",
            len(hotels),
            before,
        )

    return hotels


def search_hotels_lowprice(
    *,
    region_id: str,
    check_in: date,
    check_out: date,
    adults: int,
    results_size: int,
    min_price_per_night: Optional[float] = None,
    max_price_per_night: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Низкая цена: сортировка по возрастанию цены, с опциональными
    ограничениями по цене за ночь.
    """
    hotels = _search_hotels(
        region_id=region_id,
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        results_size=results_size,
        sort="PRICE_LOW_TO_HIGH",
        min_price_per_night=min_price_per_night,
        max_price_per_night=max_price_per_night,
    )

    # На всякий случай досортируем локально по цене за ночь
    hotels.sort(
        key=lambda h: (h.get("price_nightly") if h.get("price_nightly") is not None else float("inf"))
    )
    return hotels


def _map_min_rating_to_guest_rating_filter(min_rating: Optional[float]) -> Optional[str]:
    """
    Маппинг минимального рейтинга пользователя на код фильтра API:
    7+ -> "35", 8+ -> "40", 9+ -> "45".
    """
    if min_rating is None:
        return None
    if min_rating >= 9:
        return "45"
    if min_rating >= 8:
        return "40"
    if min_rating >= 7:
        return "35"
    return None


def search_hotels_guest_rating(
    *,
    region_id: str,
    check_in: date,
    check_out: date,
    adults: int,
    results_size: int,
    min_guest_rating: Optional[float] = None,
    min_price_per_night: Optional[float] = None,
    max_price_per_night: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    По рейтингу гостей:
    - сортировка REVIEW на стороне API,
    - опциональный фильтр guestRating (7+, 8+, 9+),
    - опциональные границы по цене за ночь.
    """
    guest_rating_filter = _map_min_rating_to_guest_rating_filter(min_guest_rating)

    hotels = _search_hotels(
        region_id=region_id,
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        results_size=results_size,
        sort="REVIEW",
        min_price_per_night=min_price_per_night,
        max_price_per_night=max_price_per_night,
        guest_rating_filter=guest_rating_filter,
    )

    # Локально гарантируем сортировку по рейтингу по убыванию
    hotels.sort(
        key=lambda h: (h.get("guest_rating") if h.get("guest_rating") is not None else 0.0),
        reverse=True,
    )
    return hotels


def search_hotels_bestdeal(
    *,
    region_id: str,
    check_in: date,
    check_out: date,
    adults: int,
    results_size: int,
    min_price_per_night: Optional[float],
    max_price_per_night: Optional[float],
    max_distance_km: Optional[float],
    backend_results_size: int = 50,
) -> List[Dict[str, Any]]:
    """
    bestdeal:
    - сортировка по расстоянию от центра на стороне API (DISTANCE),
    - локальная фильтрация по цене за ночь и расстоянию,
    - на выходе максимум results_size отелей.
    """
    hotels = _search_hotels(
        region_id=region_id,
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        results_size=backend_results_size,
        sort="DISTANCE",
        min_price_per_night=min_price_per_night,
        max_price_per_night=max_price_per_night,
    )

    def distance_ok(h: Dict[str, Any]) -> bool:
        if max_distance_km is None:
            return True
        d = h.get("distance_km")
        if d is None:
            return False
        return d <= max_distance_km

    before = len(hotels)
    hotels = [h for h in hotels if distance_ok(h)]
    logger.info(
        "bestdeal: после фильтрации по расстоянию осталось %s отелей (из %s)",
        len(hotels),
        before,
    )

    # Сортируем по расстоянию (на всякий случай)
    hotels.sort(
        key=lambda h: (h.get("distance_km") if h.get("distance_km") is not None else float("inf"))
    )

    return hotels[:results_size]
