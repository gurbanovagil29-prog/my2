"""Скачивание факторов CAPM-RU (ИПЭИ РАНХиГС, А.Е. Абрамов) с сайта aea.ru.

Проект переехал с ipei.ranepa.ru на aea.ru (раздел «Материалы для загрузки»).
Обновление от 02.02.2025: месячные данные по 12.2024 включительно.
Факторы в процентах за месяц; колонки без суффикса — по курсовой доходности,
с суффиксом _TR — с учётом дивидендов. RM уже является премией Rm - Rf
(безрисковый актив — индекс гособлигаций RGBI).
"""
import time
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "ranepa"
OUT.mkdir(parents=True, exist_ok=True)

FILES = [
    "Factor_premiums_2025-02-05.csv",         # месячные факторы
    "Factor_premiums_yearly_2025-02-05.csv",  # годовые факторы
    "two-factor_portfolios_2025-02-05.csv",   # портфели 2x2: размер x стоимость, размер x ликвидность
    "Long_factor_portfolios_2025-02-05.csv",  # длинные портфели по каждому признаку + RGBI
]

if __name__ == "__main__":
    for f in FILES:
        for i in range(5):  # соединение иногда рвётся — повторяем
            try:
                req = urllib.request.Request(f"https://aea.ru/data/csv/{f}",
                                             headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    (OUT / f).write_bytes(r.read())
                break
            except OSError:
                time.sleep(2 ** i)
        print(f, (OUT / f).stat().st_size, "байт")
