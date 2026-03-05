import html
from typing import Any, Dict, Optional


def format_hotel_card(
    hotel: Dict[str, Any],
    *,
    nights: int,
    adults: int,
    check_in: Optional[Any] = None,
    check_out: Optional[Any] = None,
    show_distance: bool = False,
) -> str:
    """
    Возвращает HTML-строку с информацией об отеле для отправки через Telegram.
    Используй parse_mode='HTML' при вызове bot.send_message.
    """
    name = html.escape(hotel.get("name") or "—")
    city = html.escape(hotel.get("city") or "—")

    lines = [
        f"<b>{name}</b>",
        f"Локация: {city}",
        f"Гостей в номере: {adults}",
    ]

    price_nightly = hotel.get("price_nightly")
    price_total = hotel.get("price_total")

    if price_nightly is not None:
        lines.append(f"Цена за ночь: {price_nightly:.2f} USD")
    if price_total is not None and nights:
        lines.append(f"Итого за {nights} ночей (включая налоги): {price_total:.2f} USD")

    guest_rating = hotel.get("guest_rating")
    if guest_rating is not None:
        lines.append(f"Оценка гостей: {guest_rating}")

    if show_distance:
        distance = hotel.get("distance_km")
        if distance is not None:
            lines.append(f"Расстояние до центра: {distance} км")

    if check_in and check_out:
        lines.append(f"Даты: {check_in} — {check_out}")

    booking_url = hotel.get("booking_url")
    if booking_url:
        lines.append(f'<a href="{html.escape(booking_url)}">Забронировать →</a>')

    return "\n".join(lines)
