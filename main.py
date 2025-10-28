from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from src.clients.epic_store_client import EpicStoreClient
from src.clients.liquipedia_client import LiquipediaClient
from src.clients.twitch_client import TwitchClient
from src.collector import (
    Collector,
    aggregate_daily_twitch,
    collect_from_twitch_csv,
    only_games,
    save_raw_twitch_snapshot,
    sort_and_top,
)
from src.models.schemas import ScoredGame
from src.scoring import score_games
from src.utils import get_env, get_logger, load_env

log = get_logger("fortnite-bot.main")

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


def main() -> None:
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
                "  %2d. %-30s score=%.3f (twitch=%s)",
                i,
                g.title,
                g.popularity_score,
                f"{(g.metrics.twitch_viewers or 0):,}".replace(",", " "),
            )
    else:
        log.info("Twitch не настроен или не вернул данные")

    # --- LIVE: общий и "только игры" + raw snapshot ---
    live_rows = collector.twitch_live_rows(limit_games=50)
    if live_rows:
        # сохраняем raw
        raw_path = save_raw_twitch_snapshot(live_rows)
        log.info("Saved raw Twitch snapshot: %s", raw_path)

        # общий топ (всё, включая Just Chatting)
        top_live_all = sort_and_top(live_rows, 10)
        save_top_as = Path("data/top10/top10_live_all_latest")
        from src.collector import (
            save_top_as_csv_json,  # локальный импорт, чтобы не тянуть наверх всё
        )

        save_top_as_csv_json(top_live_all, save_top_as)
        log.info("Saved: %s.csv/json", save_top_as)

        # только игры
        top_live_games = sort_and_top(only_games(live_rows), 10)
        save_top_as_games = Path("data/top10/top10_live_games_latest")
        save_top_as_csv_json(top_live_games, save_top_as_games)
        log.info("Saved: %s.csv/json", save_top_as_games)

    # --- DAILY: агрегат за сутки (медиана)
    all_daily, games_daily = aggregate_daily_twitch()
    if all_daily:
        ds = datetime.now(UTC).strftime("%Y-%m-%d")

        # общий (всё)
        save_top_as_csv_json(all_daily, Path(f"data/top10/top10_daily_all_{ds}"))
        save_top_as_csv_json(all_daily, Path("data/top10/top10_daily_all_latest"))

        # только игры
        save_top_as_csv_json(games_daily, Path(f"data/top10/top10_daily_games_{ds}"))
        save_top_as_csv_json(games_daily, Path("data/top10/top10_daily_games_latest"))

        log.info("Saved daily aggregated tops (all/games).")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fortnite trends aggregator")
    parser.add_argument(
        "--mode",
        choices=["all", "live", "daily"],
        default="all",
        help="What to run: all (default), live, or daily",
    )
    args = parser.parse_args()

    # Инициализация клиентов
    collector = bootstrap()

    # 1) Всегда делаем быстрый ping (полезно в логах)
    report = collector.quick_check()
    log.info("Quick check:")
    for name, info in report.items():
        log.info("  %-12s -> %s", name, info)

    # 2) Основной «скоринг дня» (Twitch топ -> scoring -> top10_latest.*)
    # Выполняем только в режимах all/daily, чтобы не грузить лишний раз при live-обновлениях
    if args.mode in ("all", "daily"):
        top10 = collector.trending_from_twitch(limit_games=50, top_n=10)
        if top10:
            log.info("Top-10 игр по аудитории Twitch (сейчас):")
            for i, row in enumerate(top10, 1):
                viewers_human = f'{row["twitch_viewers"]:,}'.replace(",", " ")
                log.info("  %2d. %-30s %8s viewers", i, row["name"], viewers_human)
            log.info("Файлы сохранены: data/top10_twitch.json, data/top10_twitch.csv")

            # Интегральный скоринг (пока ед. метрика — Twitch; позже добавим Steam, Trends и т.п.)
            twitch_csv = DATA_DIR / "top10_twitch.csv"
            snapshots = collect_from_twitch_csv(twitch_csv)
            scored = score_games(snapshots)

            # Полный дамп скорингов
            scores_latest = OUT_SCORES_DIR / "latest.json"
            with scores_latest.open("w", encoding="utf-8") as f:
                json.dump([s.model_dump() for s in scored], f, ensure_ascii=False, indent=2)
            log.info("Saved detailed scores: %s", scores_latest)

            # Топ-10 по интегральному индексу
            save_top10(scored, n=10)

            # Короткий вывод в лог (можно удалить/расширить до 10)
            log.info("Top-5 по интегральному индексу популярности:")
            for i, g in enumerate(scored[:5], 1):
                log.info(
                    "  %2d. %-30s score=%.3f (twitch=%s)",
                    i,
                    g.title,
                    g.popularity_score,
                    f"{(g.metrics.twitch_viewers or 0):,}".replace(",", " "),
                )
        else:
            log.info("Twitch не настроен или не вернул данные")

    # 3) LIVE-срезы (каждые 10–15 минут)
    if args.mode in ("all", "live"):
        live_rows = collector.twitch_live_rows(limit_games=50)
        if live_rows:
            raw_path = save_raw_twitch_snapshot(live_rows)
            log.info("Saved raw Twitch snapshot: %s", raw_path)

            top_live_all = sort_and_top(live_rows, 10)
            from src.collector import save_top_as_csv_json  # локально

            save_top_as_csv_json(top_live_all, Path("data/top10/top10_live_all_latest"))
            log.info("Saved: data/top10/top10_live_all_latest.csv/json")

            top_live_games = sort_and_top(only_games(live_rows), 10)
            save_top_as_csv_json(top_live_games, Path("data/top10/top10_live_games_latest"))
            log.info("Saved: data/top10/top10_live_games_latest.csv/json")

    # 4) DAILY-агрегаты (медиана за сутки)
    if args.mode in ("all", "daily"):
        all_daily, games_daily = aggregate_daily_twitch()
        if all_daily:
            ds = datetime.now(UTC).strftime("%Y-%m-%d")

            from src.collector import save_top_as_csv_json  # локально

            # общий
            save_top_as_csv_json(all_daily, Path(f"data/top10/top10_daily_all_{ds}"))
            save_top_as_csv_json(all_daily, Path("data/top10/top10_daily_all_latest"))
            # только игры
            save_top_as_csv_json(games_daily, Path(f"data/top10/top10_daily_games_{ds}"))
            save_top_as_csv_json(games_daily, Path("data/top10/top10_daily_games_latest"))

            log.info("Saved daily aggregated tops (all/games).")
