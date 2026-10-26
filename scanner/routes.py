"""Каналы-получатели: у каждого свои правила, какие истории в него отправлять."""
import os
from dataclasses import dataclass

from .store import Story


@dataclass
class Route:
    key: str
    name: str
    chat: str
    min_score: float
    mark: str = ""
    corroboration: dict | None = None   # {sources, min_score}: история из N разных СМИ
    burst: dict | None = None           # {sources, minutes, min_score}: N СМИ за M минут — резкая новость
    max_delay_minutes: float | None = None  # не слать, если история уже "остыла"

    @classmethod
    def from_config(cls, key: str, cfg: dict) -> "Route":
        # Своя переменная окружения на канал; если её нет — общий CHAT_ID.
        chat = os.getenv(cfg.get("chat_env", ""), "") or os.getenv("CHAT_ID", "") or key
        return cls(
            key=key,
            name=cfg.get("name", key),
            chat=chat,
            min_score=cfg["min_score"],
            mark=cfg.get("mark", ""),
            corroboration=cfg.get("corroboration"),
            burst=cfg.get("burst"),
            max_delay_minutes=cfg.get("max_delay_minutes"),
        )

    def reason(self, story: Story, now: float) -> str | None:
        """Почему историю надо отправить в этот канал; None — не надо."""
        if self.max_delay_minutes is not None and now - story.created > self.max_delay_minutes * 60:
            return None
        if story.score >= self.min_score:
            return f"🔁 {len(story.sources)} источника(ов)" if len(story.sources) > 1 else ""
        burst = self.burst
        if burst and story.score >= burst["min_score"]:
            n = story.sources_within(burst["minutes"])
            if n >= burst["sources"]:
                return f"⚡ {n} СМИ за {burst['minutes']} мин"
        corr = self.corroboration
        if corr and story.score >= corr["min_score"] and len(story.sources) >= corr["sources"]:
            return f"🔁 {len(story.sources)} источника(ов)"
        return None
