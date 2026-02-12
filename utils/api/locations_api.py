from typing import Any, Dict, List

from .base_client import api_get
from utils.logger import logger


def search_cities(
    query: str,
    locale: str = "ru_RU",
    langid: int = 1049,
    siteid: int = 300000001,
) -> List[Dict[str, Any]]:
    """
    Поиск городов/регионов по строке запроса.

    Использует эндпоинт:
      GET /locations/v3/search

    Пример запроса (по документации APIDojo):
      /locations/v3/search?q=berlin&locale=en_US&langid=1033&siteid=300000001

    Возвращает список словарей:
      {
        "gaia_id": "536",
        "full_name": "Berlin, Germany",
        "type": "CITY",
        "country": "Germany",
        "lat": 52.51,
        "lon": 13.35,
    }
    """
    params = {
        "q": query,
        "locale": locale,
        "langid": langid,
        "siteid": siteid,
    }
    raw = api_get("/locations/v3/search", params=params)

    results = []

    sr = raw.get("sr") or []  # список suggestion results
    if not isinstance(sr, list):
        logger.error("Unexpected locations/v3/search format: 'sr' is not a list")
        return results

    for item in sr:
        # Примеры объектов (gaiaRegionResult) в официальном ответе:
        # {
        #   "@type": "gaiaRegionResult",
        #   "gaiaId": "536",
        #   "type": "CITY",
        #   "regionNames": {
        #       "fullName": "Berlin, Germany",
        #       "shortName": "Berlin",
        #       ...
        #   },
        #   "coordinates": {"lat": "52.51384", "long": "13.35008"},
        #   ...
        # }
        try:
            item_type = item.get("type")
            if item_type not in ("CITY", "NEIGHBORHOOD"):
                continue
            region_names = item.get("regionNames") or {}
            # coords = item.get("coordinates") or {}
            full_name = (
                    region_names.get("fullName")
                    or region_names.get("displayName")
                    or region_names.get("shortName")
                    or None
            )
            if not full_name:
                continue
            gaia_id = item.get("gaiaId") or item.get("gaia_id")
            if not gaia_id:
                continue
            # country_info = (item.get("hierarchyInfo") or {}).get("country") or {}

            results.append(
                {
                    "destination_id": str(gaia_id),
                    "caption": full_name,
                    # "gaia_id": str(item.get("gaiaId") or item.get("gaia_id") or ""),
                    # "hotel_id": item.get("hotelId"),  # для случаев type == HOTEL
                    # "type": item_type,
                    # "full_name": region_names.get("fullName") or region_names.get("displayName"),
                    # "short_name": region_names.get("shortName") or region_names.get("primaryDisplayName"),
                    # "country": country_info.get("name"),
                    # "lat": float(coords["lat"]) if "lat" in coords else None,
                    # "lon": float(coords["long"]) if "long" in coords else None,
                }
            )
        except Exception as exc:
            logger.error("Error parsing location item: %s, item=%s", exc, item, exc_info=True)
    logger.info("search_cities (%r) -> %d результатов", query, len(results))
    return results