from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any

from .models.schemas import GameSnapshot

# Известные не-игровые категории Twitch (игнорим при "только игры")
NON_GAME_CATEGORY_IDS = {
    "509658",  # Just Chatting
    "509660",  # Music
    "509659",  # Special Events
    "511224",  # IRL/Travel & Outdoors (пример)
    # при необходимости дополняем
}

# ---- Директории для RAW-снимков Twitch ----
RAW_DIR = Path("data/raw/twitch")
RAW_DIR.mkdir(parents=True, exist_ok=True)


def _now_utc_date_str() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _now_utc_time_str() -> str:
    return datetime.now(UTC).strftime("%H%M%S")


class Collector:
    """Собирает быстрые проверки и реальные метрики (постепенно расширяем)."""

    def __init__(self, liquipedia, epic, twitch=None):
        self.liquipedia = liquipedia
        self.epic = epic
        self.twitch = twitch

    # ---------- PING / QUICK CHECK ----------
    def quick_check(self) -> dict[str, Any]:
        """Мини-проверка API-доступности (ping)."""
        report: dict[str, Any] = {}
        report["liquipedia"] = self.liquipedia.ping()
        report["epic_store"] = self.epic.ping()
        return report

    # ---------- TWITCH: LIVE-СТРОКА ----------
    def twitch_live_rows(self, limit_games: int = 50) -> list[dict[str, Any]]:
        """
        Возвращает список категорий со зрителями прямо сейчас:
        [{"id": "..","name": "..","twitch_viewers": 12345}, ...]
        """
        if not self.twitch:
            return []
        games = self.twitch.top_games(first=limit_games)  # [{id, name, ...}]
        rows: list[dict[str, Any]] = []
        for g in games:
            viewers = self.twitch.game_viewers(g["id"])
            rows.append({"id": g["id"], "name": g["name"], "twitch_viewers": viewers})
        return rows

    def trending_from_twitch(self, limit_games: int = 50, top_n: int = 10) -> list[dict[str, Any]]:
        """
        Совместимая версия (как было раньше): считает Top-N «сейчас»,
        сохраняет data/top10_twitch.json и data/top10_twitch.csv и возвращает список.
        """
        rows = self.twitch_live_rows(limit_games=limit_games)
        if not rows:
            return []

        rows.sort(key=lambda x: x["twitch_viewers"], reverse=True)
        top = rows[:top_n]

        data_dir = Path("data")
        data_dir.mkdir(parents=True, exist_ok=True)

        # JSON (как раньше)
        (data_dir / "top10_twitch.json").write_text(
            json.dumps(top, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # CSV (как раньше)
        with (data_dir / "top10_twitch.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["name", "twitch_viewers"])
            w.writeheader()
            w.writerows([{"name": r["name"], "twitch_viewers": r["twitch_viewers"]} for r in top])

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


# -------- Вспомогательные функции для LIVE/DILY топов и RAW-снимков --------
def save_raw_twitch_snapshot(rows: list[dict[str, Any]]) -> Path:
    """
    Сохраняет «сырое» live-состояние категорий Twitch с текущим временем.
    rows: [{"id": "509658", "name": "...", "twitch_viewers": 12345}, ...]
    """
    day_dir = RAW_DIR / _now_utc_date_str()
    day_dir.mkdir(parents=True, exist_ok=True)
    p = day_dir / f"snapshot_{_now_utc_time_str()}.json"
    p.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def only_games(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in rows if r.get("id") not in NON_GAME_CATEGORY_IDS]


def sort_and_top(rows: list[dict[str, Any]], n: int = 10) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda x: x.get("twitch_viewers", 0), reverse=True)[:n]


def save_top_as_csv_json(rows: list[dict[str, Any]], base: Path) -> None:
    """
    base — путь без расширения. Сохраняем base.csv и base.json
    CSV колонки: rank, title, popularity_score, twitch_viewers
    popularity_score сейчас 0.0 (позже можно подмешать live-скоринг).
    """
    base.parent.mkdir(parents=True, exist_ok=True)

    # CSV
    with (base.with_suffix(".csv")).open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "title", "popularity_score", "twitch_viewers"])
        for i, r in enumerate(rows, 1):
            w.writerow([i, r.get("name"), r.get("popularity_score", 0.0), r.get("twitch_viewers")])

    # JSON
    payload = [
        {
            "rank": i + 1,
            "title": r.get("name"),
            "popularity_score": r.get("popularity_score", 0.0),
            "metrics": {"twitch_viewers": r.get("twitch_viewers")},
        }
        for i, r in enumerate(rows)
    ]
    (base.with_suffix(".json")).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def aggregate_daily_twitch(
    date_str: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Собирает все RAW-снимки за дату (UTC), считает медиану зрителей по каждой категории.
    Возвращает два списка: (all_categories, only_games)
    """
    if not date_str:
        date_str = _now_utc_date_str()
    day_dir = RAW_DIR / date_str
    if not day_dir.exists():
        return [], []

    # id -> {"name": str, "values": [ints]}
    acc: dict[str, dict[str, Any]] = defaultdict(lambda: {"name": "", "values": []})

    for p in sorted(day_dir.glob("snapshot_*.json")):
        try:
            js = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for r in js:
            cid = str(r.get("id") or "")
            name = r.get("name") or ""
            v = r.get("twitch_viewers")
            if not cid or v is None:
                continue
            acc[cid]["name"] = name
            acc[cid]["values"].append(int(v))

    aggregated: list[dict[str, Any]] = []
    for cid, info in acc.items():
        vals = info["values"]
        if not vals:
            continue
        aggregated.append(
            {
                "id": cid,
                "name": info["name"],
                "twitch_viewers": int(median(vals)),  # медиана за день
            }
        )

    all_cats = sort_and_top(aggregated, 10)
    games_only = sort_and_top([r for r in aggregated if r["id"] not in NON_GAME_CATEGORY_IDS], 10)
    return all_cats, games_only
