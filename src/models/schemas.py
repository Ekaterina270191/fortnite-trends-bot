from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

# --- Базовые классификаторы (чтобы не плодить разнобой строк) ---


class Genre(str, Enum):
    shooter = "shooter"
    moba = "moba"
    battle_royale = "battle_royale"
    rpg = "rpg"
    mmorpg = "mmorpg"
    action = "action"
    strategy = "strategy"
    sports = "sports"
    racing = "racing"
    sandbox = "sandbox"
    survival = "survival"
    simulation = "simulation"
    horror = "horror"
    # при необходимости добавим ещё


class Mechanic(str, Enum):
    solo = "solo"
    coop = "coop"
    team_competitive = "team_competitive"
    open_world = "open_world"
    shooter = "shooter"
    extraction = "extraction"
    # механики ≠ жанры, но часть пересекается — оставляем для фильтров


# --- Снимок данных по одной игре на текущую дату ---


class GameSnapshot(BaseModel):
    # Идентификация / нормализация названий
    title: str = Field(..., description="Основное название игры")
    aliases: list[str] = Field(default_factory=list, description="Синонимы/варианты названий")
    platform: str | None = Field(default=None, description="steam/epic/playstation/xbox/mobile/…")
    external_ids: dict[str, str] = Field(
        default_factory=dict, description="Идентификаторы: {'steam_appid':'570', 'epic':'…'}"
    )

    # Таксономия
    genres: list[Genre] = Field(default_factory=list)
    mechanics: list[Mechanic] = Field(default_factory=list)

    # Метрики популярности (все опциональны — какой-то источник может отсутствовать)
    # 3,5 Активные игроки
    active_players: int | None = None  # текущее онлайн-число (напр., Steam)
    # 6 Просмотры/аудитория
    twitch_viewers: int | None = None  # текущие зрители Twitch (категория)
    youtube_views_daily: int | None = None  # суммарные дневные просмотры по игре
    reddit_mentions_daily: int | None = None  # упоминания/комменты за сутки
    esports_viewers: int | None = None  # аудитория киберспорта (если доступно)
    # 7 Продажи/монетизация
    sales_or_revenue_index: float | None = None  # прокси-метрика (индекс 0..100)
    # 8-10 Мнения игроков и критиков
    critic_score: float | None = None  # OpenCritic/Metacritic (0..100)
    user_score: float | None = None  # Steam/Stores (0..100)
    # 11-14 Тренды/поиск/контент
    google_trends_score: float | None = None  # 0..100 за окно (нормализованное)
    # прочие поля можно добавлять по мере подключения источников

    # Техническое
    source_timestamps: dict[str, str] = Field(
        default_factory=dict, description="{'twitch':'2025-10-23T12:34:56Z', ...}"
    )
    collected_at: str | None = Field(
        default=None, description="ISO-время формирования снимка (UTC)"
    )

    class Config:
        extra = "ignore"


# --- Результат скоринга для ранжирования и нарезок (по жанрам/механикам) ---


class ScoredGame(BaseModel):
    title: str
    genres: list[Genre] = Field(default_factory=list)
    mechanics: list[Mechanic] = Field(default_factory=list)
    metrics: GameSnapshot
    popularity_score: float = Field(..., ge=0, le=1)
    # нормализованные компоненты (0..1) до умножения на веса — для объяснимости
    components: dict[str, float] = Field(default_factory=dict)
