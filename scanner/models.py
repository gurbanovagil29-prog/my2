from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Item:
    uid: str            # уникальный id в рамках источника
    source: str
    category: str
    title: str
    summary: str
    link: str
    published: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_weight: float = 0
    outlet: str = ""    # издание: сайт ТАСС и канал @tass_agency — одно СМИ, в охвате считаются один раз

    def __post_init__(self):
        self.outlet = self.outlet or self.source


@dataclass
class Score:
    value: float
    hits: list[str]
    event: bool = False  # найдено историческое событие (группа с event: true)
