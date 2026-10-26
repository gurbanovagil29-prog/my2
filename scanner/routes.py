"""Каналы-получатели: у каждого свои правила, какие истории в него отправлять."""
import os
from dataclasses import dataclass

from .importance import importance
from .store import Story


@dataclass
class Route:
    key: str
    name: str
    chat: str
    min_importance: float
    mark: str = ""
    burst: dict | None = None           # {sources, minutes, min_importance}: N СМИ за M минут — резкая новость
    max_delay_minutes: float | None = None  # не слать, если история уже "остыла"

    @classmethod
    def from_config(cls, key: str, cfg: dict) -> "Route":
        # Своя переменная окружения на канал; если её нет — общий CHAT_ID.
        chat = os.getenv(cfg.get("chat_env", ""), "") or os.getenv("CHAT_ID", "") or key
        return cls(
            key=key,
            name=cfg.get("name", key),
            chat=chat,
            min_importance=cfg["min_importance"],
            mark=cfg.get("mark", ""),
            burst=cfg.get("burst"),
            max_delay_minutes=cfg.get("max_delay_minutes"),
        )

    def reason(self, story: Story, now: float, scale: dict) -> str | None:
        """Почему историю надо отправить в этот канал; None — не надо."""
        if self.max_delay_minutes is not None and now - story.created > self.max_delay_minutes * 60:
            return None
        value = importance(story, scale)
        burst = self.burst
        if burst and value >= burst["min_importance"]:
            n = story.sources_within(burst["minutes"])
            if n >= burst["sources"]:
                return f"⚡ {n} СМИ за {burst['minutes']} мин"
        if value >= self.min_importance:
            return f"🔁 {len(story.sources)} СМИ" if len(story.sources) > 1 else ""
        return None
