from __future__ import annotations
from src.utils import load_env, get_env, get_logger
from src.collector import Collector
from src.clients.liquipedia_client import LiquipediaClient
from src.clients.epic_store_client import EpicStoreClient
from src.clients.twitch_client import TwitchClient  # Twitch

log = get_logger("main")

def bootstrap() -> Collector:
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

if __name__ == "__main__":
    collector = bootstrap()

    # 1) Быстрый ping-репорт
    report = collector.quick_check()
    log.info("Quick check:")
    for name, info in report.items():
        log.info("  %-12s -> %s", name, info)

    # 2) Топ-10 с Twitch (сохранение в data/ и вывод в лог)
    top10 = collector.trending_from_twitch(limit_games=50, top_n=10)
    if top10:
        log.info("Top-10 игр по аудитории Twitch (сейчас):")
        for i, row in enumerate(top10, 1):
            viewers_human = f'{row["twitch_viewers"]:,}'.replace(",", " ")
            log.info("  %2d. %-30s %8s viewers", i, row["name"], viewers_human)
        log.info("Файлы сохранены: data/top10_twitch.json, data/top10_twitch.csv")
    else:
        log.info("Twitch не настроен или не вернул данные")