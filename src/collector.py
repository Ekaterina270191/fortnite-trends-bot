from __future__ import annotations
from typing import Dict, Any
from .utils import get_logger
from .clients.liquipedia_client import LiquipediaClient
from .clients.epic_store_client import EpicStoreClient

logger = get_logger("collector")

class Collector:
    def __init__(self, liquipedia: LiquipediaClient, epic: EpicStoreClient):
        self.liquipedia = liquipedia
        self.epic = epic

    def quick_check(self) -> Dict[str, Any]:
        """
        Мини-сбор: провали, статус-коды/размеры — чтобы убедиться,
        что API доступны.
        """
        result: Dict[str, Any] = {}

        # Liquipedia
        try:
            data = self.liquipedia.search("Fortnite", limit=10)
            result["liquipedia"] = {
                "hits": len(data.get("query", {}).get("search", [])),
                "ok": True,
            }
        except Exception as e:
            logger.exception("Liquipedia error")
            result["liquipedia"] = {"ok": False, "error": str(e)}

        # Epic Store
        try:
            data = self.epic.free_promotions()
            promos = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
            result["epic_store"] = {
                "items": len(promos),
                "ok": True,
            }
        except Exception as e:
            logger.exception("EpicStore error")
            result["epic_store"] = {"ok": False, "error": str(e)}

        return result