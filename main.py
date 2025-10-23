from __future__ import annotations
from src.utils import load_env, get_env, get_logger
from src.collector import Collector
from src.clients.liquipedia_client import LiquipediaClient
from src.clients.epic_store_client import EpicStoreClient

log = get_logger("main")

def bootstrap() -> Collector:
    load_env()

    user_agent = get_env("REDDIT_USER_AGENT", "FortniteTrendsBot/1.0")
    liquipedia_url = get_env("LIQUIPEDIA_API_URL", required=True)
    epic_url = get_env("EPIC_STORE_API_URL", required=True)

    liqui = LiquipediaClient(base_url=liquipedia_url, user_agent=user_agent)
    epic = EpicStoreClient(promotions_url=epic_url, user_agent=user_agent)
    return Collector(liquipedia=liqui, epic=epic)

if __name__ == "__main__":
    collector = bootstrap()
    report = collector.quick_check()

    log.info("Quick check:")
    for name, info in report.items():
        log.info("  %-12s -> %s", name, info)