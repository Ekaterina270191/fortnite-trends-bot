from __future__ import annotations
from typing import Dict, Any
from .base_client import BaseClient

class EpicStoreClient(BaseClient):
    """
    Еженедельные/текущие раздачи/акции Epic Games Store.
    """
    def __init__(self, promotions_url: str, user_agent: str | None = None):
        super().__init__(user_agent=user_agent)
        self.promotions_url = promotions_url

    def free_promotions(self) -> Dict[str, Any]:
        r = self.get(self.promotions_url)
        r.raise_for_status()
        return r.json()