from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from src.clients.epic_store_client import EpicStoreClient
from src.clients.liquipedia_client import LiquipediaClient
from src.clients.twitch_client import TwitchClient
from src.collector import Collector, collect_from_twitch_csv
from src.models.schemas import ScoredGame
from src.scoring import score_games
from src.utils import get_env, get_logger, load_env

log = get_logger("main")

# Пути для данных/выгрузок
DATA_DIR = Path("data")
OUT_TOP10_DIR = DATA_DIR / "top10"
OUT_SCORES_DIR = DATA_DIR / "scores"
OUT_TOP10_DIR.mkdir(parents=True, exist_ok=True)
OUT_SCORES_DIR.mkdir(parents=True, exist_ok=True)


def bootstrap() -> Collector:
    """Инициализируем клиентов и Collector."""
    load_env()

    user_agent = get_env("REDDIT_USER_AGENT", "FortniteTrendsBot/1.0")
    liquipedia_url = get_env("LIQUIPEDIA_API_URL", required=True)
    epic_url = get_env("EPIC_STORE_API_URL", required=True)

    liqui = LiquipediaClient(base_url=liquipedia_url, user_agent=user_agent)
    epic = EpicStoreClient(promotions_url=epic_url, user_agent=user_agent)

    # Twitch — подключаем только если заданы ключи
    twitch_id = get_env("TWITCH_CLIENT_ID")
    twitch_secret = get_env("TWITCH_CLIENT_SECRET")
    twitch = TwitchClient(twitch_id, twitch_secret) if twitch_id and twitch_secret else None

    return Collector(liquipedia=liqui, epic=epic, twitch=twitch)


def save_top10(scored: list[ScoredGame], n: int = 10) -> None:
    """Сохранение топ-10 по интегральному индексу (CSV + JSON payload)."""
    ts = datetime.now(UTC).strftime("%Y-%m-%d")
    out_csv = OUT_TOP10_DIR / f"top10_{ts}.csv"
    out_csv_latest = OUT_TOP10_DIR / "top10_latest.csv"
    out_json_latest = OUT_TOP10_DIR / "top10_latest.json"

    header = ["rank", "title", "popularity_score", "twitch_viewers"]
    rows = []
    for i, g in enumerate(scored[:n], 1):
        rows.append([i, g.title, g.popularity_score, g.metrics.twitch_viewers])

    # CSV (датированный и latest)
    for p in (out_csv, out_csv_latest):
        with p.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)

    # JSON payload (для второго бота)
    payload = [
        {
            "rank": i + 1,
            "title": g.title,
            "popularity_score": g.popularity_score,
            "metrics": {
                "twitch_viewers": g.metrics.twitch_viewers,
                # позже добавим: active_players, critic_score, user_score, trends, youtube, etc.
            },
            "genres": [getattr(x, "value", str(x)) for x in g.genres],
            "mechanics": [getattr(x, "value", str(x)) for x in g.mechanics],
            "components": g.components,  # нормализованные вклады метрик 0..1
        }
        for i, g in enumerate(scored[:n])
    ]
    with out_json_latest.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    log.info("Saved Top-10 index files: %s, %s", out_csv_latest, out_json_latest)


if __name__ == "__main__":
    collector = bootstrap()

    # 1) Быстрый ping-репорт
    report = collector.quick_check()
    log.info("Quick check:")
    for name, info in report.items():
        log.info("  %-12s -> %s", name, info)

    # 2) Топ-10 Twitch (сырые метрики и сохранение CSV/JSON)
    top10 = collector.trending_from_twitch(limit_games=50, top_n=10)
    if top10:
        log.info("Top-10 игр по аудитории Twitch (сейчас):")
        for i, row in enumerate(top10, 1):
            viewers_human = f'{row["twitch_viewers"]:,}'.replace(",", " ")
            log.info("  %2d. %-30s %8s viewers", i, row["name"], viewers_human)
        log.info("Файлы сохранены: data/top10_twitch.json, data/top10_twitch.csv")

        # 3) Интегральный скоринг (пока метрика из Twitch, остальные добавим по мере подключения)
        twitch_csv = DATA_DIR / "top10_twitch.csv"
        snapshots = collect_from_twitch_csv(twitch_csv)
        scored = score_games(snapshots)

        # 4) Полный список со скором (для анализа и отчётов)
        scores_latest = OUT_SCORES_DIR / "latest.json"
        with scores_latest.open("w", encoding="utf-8") as f:
            json.dump([s.model_dump() for s in scored], f, ensure_ascii=False, indent=2)
        log.info("Saved detailed scores: %s", scores_latest)

        # 5) Топ-10 по интегральному индексу (для отчётов и Телеграм-бота)
        save_top10(scored, n=10)

        # 6) Выводим топ-5 по интегральному индексу в лог
        log.info("Top-5 по интегральному индексу популярности:")
        for i, g in enumerate(scored[:5], 1):
            log.info(
                "  %2d. %-30s score=%.3f (twitch=%.0f)",
                i,
                g.title,
                g.popularity_score,
                g.metrics.twitch_viewers or 0,
            )
    else:
        log.info("Twitch не настроен или не вернул данные")
