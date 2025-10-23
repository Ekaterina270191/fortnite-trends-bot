from __future__ import annotations
import requests
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class LiquipediaClient:
    base_url: str
    user_agent: str

    def ping(self) -> Dict[str, Any]:
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": "Fortnite",
        }
        try:
            r = requests.get(self.base_url, params=params, timeout=15, headers={"User-Agent": self.user_agent})
            return {"status": r.status_code, "bytes": len(r.content)}
        except Exception as e:
            return {"error": str(e)}