from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .models.schemas import GameSnapshot


class Collector:
    """Собирает быстрые проверки и реальные метрики (постепенно расширяем)."""

    def __init__(self, liquipedia, epic, twitch=None):
        self.liquipedia = liquipedia
        self.epic = epic
        self.twitch = twitch

    def quick_check(self) -> dict[str, Any]:
        """Мини-проверка API-доступности (ping)."""
        report: dict[str, Any] = {}
        report["liquipedia"] = self.liquipedia.ping()
        report["epic_store"] = self.epic.ping()
        return report

    def trending_from_twitch(self, limit_games: int = 50, top_n: int = 10) -> list[dict[str, Any]]:
        """
        Топ-N игр по «живой» аудитории Twitch сейчас.
        Сохраняет результаты в data/top10_twitch.json и data/top10_twitch.csv.
        Возвращает список словарей: [{"name": ..., "twitch_viewers": ...}, ...]
        """
        if not self.twitch:
            return []

        # 1) Получаем список топ игр
        games = self.twitch.top_games(first=limit_games)  # [{id, name, box_art_url}, ...]

        # 2) Для каждой игры считаем суммарных зрителей
        enriched: list[dict[str, Any]] = []
        for g in games:
            viewers = self.twitch.game_viewers(g["id"])
            enriched.append({"name": g["name"], "twitch_viewers": viewers})

        # 3) Сортировка и топ-N
        enriched.sort(key=lambda x: x["twitch_viewers"], reverse=True)
        top = enriched[:top_n]

        # 4) Сохраняем файлы (JSON и CSV)
        data_dir = Path("data")
        data_dir.mkdir(parents=True, exist_ok=True)

        (data_dir / "top10_twitch.json").write_text(
            json.dumps(top, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        with (data_dir / "top10_twitch.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["name", "twitch_viewers"])
            w.writeheader()
            w.writerows(top)

        return top


# -------- Доп. утилита для скоринга из готового CSV --------


def collect_from_twitch_csv(path: Path) -> list[GameSnapshot]:
    """
    Читает CSV с колонками: name,twitch_viewers
    Возвращает список GameSnapshot с заполненной метрикой twitch_viewers.
    """
    rows: list[GameSnapshot] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            title = r.get("name") or r.get("title") or "Unknown"
            viewers = r.get("twitch_viewers")
            rows.append(
                GameSnapshot(
                    title=title,
                    twitch_viewers=int(viewers) if viewers else None,
                )
            )
    return rows
