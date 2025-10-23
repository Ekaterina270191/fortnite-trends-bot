from __future__ import annotations
import time
import requests
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

TWITCH_OAUTH_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_API_BASE = "https://api.twitch.tv/helix"

@dataclass
class TwitchClient:
    client_id: str
    client_secret: str

    _token: Optional[str] = None
    _token_expires_at: float = 0.0

    def _ensure_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expires_at - 60:
            return self._token
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }
        r = requests.post(TWITCH_OAUTH_URL, data=data, timeout=20)
        r.raise_for_status()
        payload = r.json()
        self._token = payload["access_token"]
        self._token_expires_at = now + payload.get("expires_in", 3600)
        return self._token

    def _headers(self) -> Dict[str, str]:
        token = self._ensure_token()
        return {"Client-Id": self.client_id, "Authorization": f"Bearer {token}"}

    def top_games(self, first: int = 50) -> List[Dict[str, Any]]:
        """Топ категорий (игр) по текущей аудитории."""
        r = requests.get(f"{TWITCH_API_BASE}/games/top",
                         params={"first": min(first, 100)},
                         headers=self._headers(), timeout=20)
        r.raise_for_status()
        return r.json().get("data", [])

    def game_viewers(self, game_id: str) -> int:
        """Сумма зрителей по первым 100 стримам игры (достаточно для топовых)."""
        params = {"game_id": game_id, "first": 100}
        r = requests.get(f"{TWITCH_API_BASE}/streams",
                         params=params, headers=self._headers(), timeout=20)
        r.raise_for_status()
        streams = r.json().get("data", [])
        return sum(s.get("viewer_count", 0) for s in streams)