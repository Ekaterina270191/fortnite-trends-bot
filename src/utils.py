from __future__ import annotations
import logging
import os
from dotenv import load_dotenv

_LOGGER: logging.Logger | None = None
_ENV_LOADED = False

def load_env() -> None:
    """Грузим .env один раз за всё время выполнения."""
    global _ENV_LOADED
    if not _ENV_LOADED:
        load_dotenv()
        _ENV_LOADED = True

def get_env(name: str, default: str | None = None, *, required: bool = False) -> str | None:
    """Безопасно читаем переменные окружения."""
    load_env()
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"ENV var {name} is required but not set")
    return value

def get_logger(name: str = "fortnite-bot") -> logging.Logger:
    """Единый формат логов."""
    global _LOGGER
    if _LOGGER:
        return _LOGGER.getChild(name)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )
    _LOGGER = logging.getLogger("fortnite-bot")
    return _LOGGER.getChild(name)