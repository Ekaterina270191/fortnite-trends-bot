from __future__ import annotations
import requests
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class EpicStoreClient:
    promotions_url: str
    user_agent: str = "FortniteTrendsBot/1.0"

    def ping(self) -> Dict[str, Any]:
        try:
            r = requests.get(self.promotions_url, timeout=15,
                             headers={"User-Agent": self.user_agent})
            return {"status": r.status_code, "bytes": len(r.content)}
        except Exception as e:
            return {"error": str(e)}

    # Реальные акции/бесплатные раздачи EGS
    def free_promotions(self) -> Dict[str, Any]:
        r = requests.get(self.promotions_url, timeout=20,
                         headers={"User-Agent": self.user_agent})
        r.raise_for_status()
        return r.json()