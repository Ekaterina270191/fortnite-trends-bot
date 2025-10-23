from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from .models.schemas import GameSnapshot, Genre, Mechanic, ScoredGame

# ==== ВЕСА ДЛЯ КРИТЕРИЕВ ====
# Соответствие пунктам из ТЗ:
# 3/5 active_players
# 6 twitch_viewers / youtube_views_daily / reddit_mentions_daily
# 7 sales_or_revenue_index
# 8-10 critic_score / user_score
# 11 google_trends_score
# 15 esports_viewers
DEFAULT_WEIGHTS: dict[str, float] = {
    "active_players": 0.25,  # (п.3,5) текущая активность — главный сигнал
    "twitch_viewers": 0.20,  # (п.6) аудитория стриминга
    "youtube_views_daily": 0.10,  # (п.14) контент на YouTube
    "reddit_mentions_daily": 0.05,  # (п.12) соцсети/форумы
    "critic_score": 0.10,  # (п.9) критики
    "user_score": 0.10,  # (п.10) отзывы игроков
    "google_trends_score": 0.10,  # (п.11,13) тренды/поиски
    "esports_viewers": 0.07,  # (п.15) киберспорт
    "sales_or_revenue_index": 0.03,  # (п.7) продажи/монетизация (прокси)
}


@dataclass
class ScoringConfig:
    weights: dict[str, float] = None
    # normalization: minmax для «бесконечных» метрик,
    # фиксированные шкалы (0..100) — нормализуем делением на 100.
    treat_missing_as_zero: bool = True

    def __post_init__(self):
        if self.weights is None:
            self.weights = DEFAULT_WEIGHTS


def _metric_ranges(
    games: Iterable[GameSnapshot], keys: Iterable[str]
) -> dict[str, tuple[float, float]]:
    mins = {k: math.inf for k in keys}
    maxs = {k: -math.inf for k in keys}
    for g in games:
        for k in keys:
            v = getattr(g, k, None)
            if v is None:
                continue
            # clamp на всякий
            try:
                v = float(v)
            except Exception:
                continue
            mins[k] = min(mins[k], v)
            maxs[k] = max(maxs[k], v)
    return {k: (mins[k], maxs[k]) for k in keys}


# метрики с естественной шкалой 0..100: нормализуем просто делением
FIXED_0_100 = {"critic_score", "user_score", "google_trends_score", "sales_or_revenue_index"}


def _normalize(value: float | None, vmin: float, vmax: float, fixed_0_100: bool) -> float:
    if value is None:
        return 0.0
    v = float(value)
    if fixed_0_100:
        return max(0.0, min(1.0, v / 100.0))
    if vmax <= vmin:
        return 0.0
    return max(0.0, min(1.0, (v - vmin) / (vmax - vmin)))


def score_games(games: list[GameSnapshot], config: ScoringConfig | None = None) -> list[ScoredGame]:
    """
    Возвращает список ScoredGame, отсортированный по popularity_score (desc).
    """
    config = config or ScoringConfig()
    keys = list(config.weights.keys())
    ranges = _metric_ranges(games, keys)

    scored: list[ScoredGame] = []
    for g in games:
        components: dict[str, float] = {}
        for k, w in config.weights.items():
            v = getattr(g, k, None)
            components[k] = _normalize(
                v,
                ranges[k][0],
                ranges[k][1],
                fixed_0_100=(k in FIXED_0_100),
            )
        score = sum(components[k] * config.weights[k] for k in keys)
        scored.append(
            ScoredGame(
                title=g.title,
                genres=g.genres,
                mechanics=g.mechanics,
                metrics=g,
                popularity_score=round(float(score), 6),
                components=components,
            )
        )
    scored.sort(key=lambda x: x.popularity_score, reverse=True)
    return scored


# ===== СРЕЗЫ (по жанрам / механикам) =====


def top_by_genre(scored: list[ScoredGame], genre: Genre, n: int = 10) -> list[ScoredGame]:
    return [g for g in scored if genre in g.genres][:n]


def top_by_mechanic(scored: list[ScoredGame], mech: Mechanic, n: int = 10) -> list[ScoredGame]:
    return [g for g in scored if mech in g.mechanics][:n]
