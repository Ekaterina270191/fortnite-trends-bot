from __future__ import annotations
from typing import Any, Dict

class Collector:
    """Собирает быстрые проверки с клиентов (далее будет собирать полноценные данные)."""

    def __init__(self, liquipedia, epic):
        self.liquipedia = liquipedia
        self.epic = epic

    def quick_check(self) -> Dict[str, Any]:
        report: Dict[str, Any] = {}
        report["liquipedia"] = self.liquipedia.ping()
        report["epic_store"] = self.epic.ping()
        return report