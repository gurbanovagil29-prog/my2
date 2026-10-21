"""Скачивание истории дивидендов с dohod.ru (таблица «Дата закрытия реестра / Дивиденд»).

Прогнозные выплаты отбрасываем — нужны только фактические.
"""
import io
import time
import urllib.request
from pathlib import Path

import pandas as pd

from download_moex import SHARES

OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "dividends"
OUT.mkdir(parents=True, exist_ok=True)

URL = "https://www.dohod.ru/ik/analytics/dividend/{}"


def get(url: str, tries: int = 5) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError:
            raise
        except OSError:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)


def fetch(ticker: str) -> pd.DataFrame:
    tables = pd.read_html(io.StringIO(get(URL.format(ticker.lower()))))
    t = next(t for t in tables if "Дата закрытия реестра" in t.columns)
    t = t[~t["Дата закрытия реестра"].astype(str).str.contains("прогноз")]
    return pd.DataFrame({
        "record_date": pd.to_datetime(t["Дата закрытия реестра"], format="%d.%m.%Y"),
        "dividend": pd.to_numeric(t["Дивиденд"], errors="coerce"),
    }).dropna().sort_values("record_date")


if __name__ == "__main__":
    for t in SHARES:
        try:
            d = fetch(t)
        except Exception as e:  # у части тикеров страницы нет — разберём вручную
            print(f"{t:6s} ошибка: {e}")
            continue
        d.to_csv(OUT / f"{t}.csv", index=False)
        print(f"{t:6s} {len(d):3d} выплат  {d.record_date.min():%Y-%m} – {d.record_date.max():%Y-%m}"
              if len(d) else f"{t:6s} выплат нет")
        time.sleep(0.5)
