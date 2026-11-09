"""Загрузка данных по опционам и фьючерсам на Сбербанк с Мосбиржи (ISS API).

Что скачиваем:
1) справочник текущих опционов SBRF: страйк, тип, экспирация, базовый фьючерс, ГО;
2) дневную историю опционов декабрьской серии (экспирация 16.12.2026, фьючерс SRZ6) —
   для доски опционов на дату анализа;
3) дневную историю опционов сентябрьской серии (экспирация 16.09.2026, фьючерс SRU6) —
   для ретро-теста стратегии, открытой 1 июля 2026;
4) дневную историю фьючерсов SRZ6, SRU6 и акций SBER.

Код опциона на Мосбирже: SR<страйк>B<месяц><год>, где месяц — буква A..L для коллов
(январь..декабрь) и M..X для путов. Пример: SR28000BX6 — пут 28000, декабрь 2026.
"""
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
ISS = "https://iss.moex.com/iss"


def get(url, params=None, tries=5):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # соединение через прокси иногда рвётся
            print("retry", i, url, e, file=sys.stderr)
            time.sleep(2 ** i)
    raise RuntimeError(url)


def paged(url, block, params=None):
    """Собирает все страницы ответа ISS (по 100 строк)."""
    params = dict(params or {})
    rows, cols, start = [], None, 0
    while True:
        params["start"] = start
        d = get(url, params)[block]
        cols = d["columns"]
        if not d["data"]:
            break
        rows += d["data"]
        start += len(d["data"])
    return pd.DataFrame(rows, columns=cols)


def option_history(secid, start, till):
    return paged(f"{ISS}/history/engines/futures/markets/options/securities/{secid}.json",
                 "history", {"from": start, "till": till})


def many_options(secids, start, till):
    with ThreadPoolExecutor(8) as ex:
        parts = list(ex.map(lambda s: option_history(s, start, till), secids))
    return pd.concat([p for p in parts if len(p)], ignore_index=True)


def futures_history(secid, start):
    return paged(f"{ISS}/history/engines/futures/markets/forts/securities/{secid}.json",
                 "history", {"from": start})


if __name__ == "__main__":
    # 1. Справочник текущих опционов
    d = get(f"{ISS}/engines/futures/markets/options/securities.json", {"assets": "SBRF"})
    ref = pd.DataFrame(d["securities"]["data"], columns=d["securities"]["columns"])
    ref.to_csv(RAW / "sbrf_options_reference.csv", index=False)

    # 2. Декабрьская серия: все страйки из справочника
    dec = ref[(ref["LASTTRADEDATE"] == "2026-12-16") & (ref["UNDERLYINGASSET"] == "SRZ6")]
    h = many_options(dec["SECID"].tolist(), "2026-10-01", "2026-11-09")
    h.to_csv(RAW / "options_dec2026_history.csv", index=False)
    print("dec", len(dec), len(h))

    # 3. Сентябрьская серия уже истекла и в справочнике её нет — собираем коды по шаблону
    sep = [f"SR{k}B{m}6" for k in range(20000, 40001, 250) for m in "IU"]
    h = many_options(sep, "2026-06-25", "2026-09-18")
    h.to_csv(RAW / "options_sep2026_history.csv", index=False)
    print("sep", h["SECID"].nunique(), len(h))

    # 4. Фьючерсы и акции
    for sec in ["SRZ6", "SRU6"]:
        futures_history(sec, "2026-06-01").to_csv(RAW / f"futures_{sec}.csv", index=False)
    paged(f"{ISS}/history/engines/stock/markets/shares/boards/TQBR/securities/SBER.json",
          "history", {"from": "2026-06-01"}).to_csv(RAW / "sber_shares.csv", index=False)
    print("done")
