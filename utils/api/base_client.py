import json
from typing import Any, Dict, Optional
import requests

from config_data import config
from utils.logger import logger


def _default_headers() -> Dict[str, str]:
    """Общие заголовки для всех запросов к RapidAPI."""
    return {
        "x-rapidapi-key": config.RAPID_API_KEY,
        "x-rapidapi-host": config.RAPID_API_HOST,
        "Content-Type": "application/json",
    }


def api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Универсальный GET-запрос к hotels4."""
    url = config.BASE_URL + path
    logger.info("GET %s params=%s", url, params)
    try:
        response = requests.get(url, headers=_default_headers(), params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.debug("Response GET %s: %s", url, json.dumps(data)[:1000])
        return data
    except Exception as exc:
        logger.error("Error GET %s: %s", url, exc, exc_info=True)
        return {}


def api_post(path: str, payload:  Dict[str, Any]) -> Dict[str, Any]:
    """Универсальный POST-запрос к hotels4."""
    url = config.BASE_URL + path
    logger.info("POST %s payload=%s", url, json.dumps(payload, ensure_ascii=False))
    try:
        response = requests.post(
            url,
            headers=_default_headers(),
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.exception("Error POST %s: %s", url, e)
        return {}
