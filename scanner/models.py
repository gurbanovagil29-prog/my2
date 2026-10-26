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


@dataclass
class Score:
    value: float
    hits: list[str]
