import os
import requests
from dotenv import load_dotenv

def main():
    load_dotenv()

    REQUIRED_KEYS = [
        # для smoke достаточно этих трёх; остальное проверим позже в своих клиентах
        "REDDIT_USER_AGENT",
        "EPIC_STORE_API_URL",
        "LIQUIPEDIA_API_URL",
    ]

    missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]
    if missing:
        print("⚠️ Не найдены переменные в .env:", ", ".join(missing))
    else:
        print("✅ Базовые переменные окружения загружены.")

    # Epic Games Free Games / Promotions
    epic_url = os.getenv("EPIC_STORE_API_URL")
    try:
        r = requests.get(epic_url, timeout=15)
        print(f"Epic Games status: {r.status_code}, bytes: {len(r.content)}")
    except Exception as e:
        print("Epic Games request error:", e)

    # Liquipedia (MediaWiki API). Нужен корректный User-Agent
    liquipedia_url = os.getenv("LIQUIPEDIA_API_URL")
    headers = {"User-Agent": os.getenv("REDDIT_USER_AGENT", "FortniteTrendsBot/1.0")}
    params = {"action": "query", "format": "json", "list": "search", "srsearch": "Fortnite"}

    try:
        r = requests.get(liquipedia_url, headers=headers, params=params, timeout=15)
        print(f"Liquipedia status: {r.status_code}, bytes: {len(r.content)}")
    except Exception as e:
        print("Liquipedia request error:", e)

if __name__ == "__main__":
    main()