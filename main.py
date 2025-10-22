import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Проверяем ключи из .env
REQUIRED_KEYS = [
    "YOUTUBE_API_KEY", "TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET",
    "TMDB_API_KEY", "FORTNITE_API_KEY", "STEAM_API_KEY",
    "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT",
    "TRN_API_KEY", "OPENCRITIC_API_KEY", "OPENCRITIC_API_HOST",
    "EPIC_STORE_API_URL", "LIQUIPEDIA_API_URL"
]

missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]
if missing:
    print("⚠️ Не найдены переменные в .env:", ", ".join(missing))
else:
    print("✅ Все переменные окружения загружены.")

# Мини-пинг Epic Games Free Games (публичный JSON)
epic_url = os.getenv("EPIC_STORE_API_URL")
try:
    r = requests.get(epic_url, timeout=15)
    print(f"Epic Games status: {r.status_code}, bytes: {len(r.content)}")
except Exception as e:
    print("Epic Games request error:", e)

# Мини-пинг Liquipedia (MediaWiki API). Нужен User-Agent
liquipedia_url = os.getenv("LIQUIPEDIA_API_URL")
headers = {"User-Agent": os.getenv("REDDIT_USER_AGENT", "FortniteTrendsBot/1.0")}
params = {
    "action": "query",
    "format": "json",
    "list": "search",
    "srsearch": "Fortnite"
}
try:
    r = requests.get(liquipedia_url, headers=headers, params=params, timeout=15)
    print(f"Liquipedia status: {r.status_code}, bytes: {len(r.content)}")
except Exception as e:
    print("Liquipedia request error:", e)
