from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv
import logging

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_env(dotenv_path: Optional[str | Path] = None) -> None:
    """
    Загружает .env один раз. Безопасно вызывать повторно.
    """
    load_dotenv(dotenv_path=dotenv_path, override=False)

def get_env(name: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    value = os.getenv(name, default)
    if required and (value is None or value == ""):
        raise RuntimeError(f"ENV variable '{name}' is required but not set")
    return value

def get_logger(name: str = "bot", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        fmt = logging.Formatter("[%(levelname)s] %(asctime)s %(name)s: %(message)s", "%H:%M:%S")
        h = logging.StreamHandler()
        h.setFormatter(fmt)
        logger.addHandler(h)
    return logger

def write_json(obj: Any, path: Path, ensure_ascii: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=ensure_ascii, indent=2)

def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
