from __future__ import annotations
from typing import Any, Dict, List
from pathlib import Path
import json
import csv

class Collector:
    """Собирает быстрые проверки и реальные метрики (постепенно расширяем)."""

    def __init__(self, liquipedia, epic, twitch=None):
        self.liquipedia = liquipedia
        self.epic = epic
        self.twitch = twitch

    def quick_check(self) -> Dict[str, Any]:
        """Мини-проверка API-доступности (ping)."""
        report: Dict[str, Any] = {}
        report["liquipedia"] = self.liquipedia.ping()
        report["epic_store"] = self.epic.ping()
        return report

    def trending_from_twitch(self, limit_games: int = 50, top_n: int = 10) -> List[Dict[str, Any]]:
        """Топ-N игр по 'живой' аудитории Twitch сейчас.
        Сохраняет результаты в data/top10_twitch.json и .csv
        """
        if not self.twitch:
            return []

        # 1️⃣ Получаем список топ игр
        games = self.twitch.top_games(first=limit_games)  # [{id, name, box_art_url}, ...]

        # 2️⃣ Для каждой игры считаем суммарных зрителей
        enriched = []
        for g in games:
            viewers = self.twitch.game_viewers(g["id"])
            enriched.append({
                "name": g["name"],
                "twitch_viewers": viewers,
            })

        # 3️⃣ Сортировка и топ-10
        enriched.sort(key=lambda x: x["twitch_viewers"], reverse=True)
        top = enriched[:top_n]

        # 4️⃣ Сохраняем файлы (JSON и CSV)
        data_dir = Path("data")
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "top10_twitch.json").write_text(
            json.dumps(top, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        with (data_dir / "top10_twitch.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["name", "twitch_viewers"])
            w.writeheader()
            w.writerows(top)

        return top