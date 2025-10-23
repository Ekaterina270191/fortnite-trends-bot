from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class LiquipediaClient:
    base_url: str
    user_agent: str

    def ping(self) -> dict[str, Any]:
        """Проверка доступности Liquipedia API."""
        params = {"action": "query", "format": "json", "list": "search", "srsearch": "Fortnite"}
        headers = {"User-Agent": self.user_agent}

        try:
            r = requests.get(
                self.base_url,
                params=params,
                timeout=15,
                headers=headers,
            )
            return {
                "status": r.status_code,
                "bytes": len(r.content),
            }
        except Exception as e:
            return {"error": str(e)}

    def search(self, term: str = "Fortnite", limit: int = 25) -> dict[str, Any]:
        """Реальный поиск по Liquipedia."""
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": term,
            "srlimit": limit,
        }
        headers = {"User-Agent": self.user_agent}

        r = requests.get(
            self.base_url,
            params=params,
            timeout=20,
            headers=headers,
        )
        r.raise_for_status()
        return r.json()
