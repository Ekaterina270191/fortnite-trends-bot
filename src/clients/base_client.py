from __future__ import annotations
import requests
from requests.adapters import HTTPAdapter, Retry

DEFAULT_TIMEOUT = 15

class BaseClient:
    """
    Базовый HTTP-клиент: сессия + ретраи.
    """
    def __init__(self, user_agent: str | None = None, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.session = requests.Session()
        retries = Retry(
            total=3, backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "POST"),
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        self.session.mount("http://", HTTPAdapter(max_retries=retries))
        if user_agent:
            self.session.headers.update({"User-Agent": user_agent})

    def get(self, url: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        return self.session.get(url, **kwargs)

    def close(self) -> None:
        self.session.close()