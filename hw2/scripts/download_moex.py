"""Скачивание месячных свечей (цены закрытия) с Мосбиржи через ISS API.

ISS отдаёт свечи страницами по 500 строк, поэтому листаем параметром start.
Цены НЕ скорректированы на сплиты/консолидации — это делаем отдельно.
"""
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "moex"
OUT.mkdir(parents=True, exist_ok=True)

START, END = "2015-01-01", "2026-09-30"

SHARES = [
    # 15 бумаг из ДЗ1
    "ROSN", "BANEP", "TRNFP", "BSPB", "CBOM", "RENI", "MAGN", "ALRS", "MTLR",
    "SELG", "HYDR", "FEES", "UPRO", "MSNG", "RTKM",
    # 20 новых бумаг
    "LKOH", "SBER", "GAZP", "YDEX", "TATN", "T", "NVTK", "GMKN", "OZON", "X5",
    "VTBR", "PLZL", "SNGSP", "HEAD", "MOEX", "IRAO", "MTSS", "CHMF", "NLMK", "RUAL",
    # старые тикеры для склейки
    "YNDX", "TCSG", "FIVE", "HHRU",
]
INDICES = ["IMOEX"]


def get_json(url: str, tries: int = 5) -> dict:
    # соединение через прокси иногда рвётся — повторяем с паузой
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except OSError:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)


def fetch_candles(market: str, secid: str) -> pd.DataFrame:
    # акции берём строго с основного режима TQBR: без указания режима ISS
    # подмешивает другие бумаги с тем же тикером (под «T» до 11.2024 — иностранная акция)
    board = "boards/TQBR/" if market == "shares" else ""
    base = (f"https://iss.moex.com/iss/engines/stock/markets/{market}/{board}securities/"
            f"{secid}/candles.json?interval=31&from={START}&till={END}")
    rows, cols, start = [], None, 0
    while True:
        block = get_json(f"{base}&start={start}")["candles"]
        cols = block["columns"]
        if not block["data"]:
            break
        rows += block["data"]
        start += len(block["data"])
        time.sleep(0.2)
    return pd.DataFrame(rows, columns=cols)


def fetch_index_history(secid: str) -> pd.DataFrame:
    """Дневные закрытия индекса -> последнее закрытие месяца.

    Свечи MCFTR в ISS начинаются только с 11.2016, а дневная история — раньше.
    """
    base = (f"https://iss.moex.com/iss/history/engines/stock/markets/index/securities/"
            f"{secid}.json?from={START}&till={END}&iss.meta=off")
    rows, start = [], 0
    while True:
        block = get_json(f"{base}&start={start}")["history"]
        if not block["data"]:
            break
        rows += [dict(zip(block["columns"], r)) for r in block["data"]]
        start += len(block["data"])
    d = pd.DataFrame(rows)[["TRADEDATE", "CLOSE"]].dropna()
    d["TRADEDATE"] = pd.to_datetime(d["TRADEDATE"])
    m = d.groupby(d["TRADEDATE"].dt.to_period("M")).last()
    return pd.DataFrame({"begin": m.index.to_timestamp().strftime("%Y-%m-%d 00:00:00"),
                         "close": m["CLOSE"].values, "end": m["TRADEDATE"].dt.strftime("%Y-%m-%d").values})


if __name__ == "__main__":
    if not (OUT / "MCFTR.csv").exists():
        df = fetch_index_history("MCFTR")
        df.to_csv(OUT / "MCFTR.csv", index=False)
        print(f"MCFTR  {len(df):4d} мес.  {df['begin'].min()[:7]} – {df['begin'].max()[:7]}")
    for market, tickers in (("shares", SHARES), ("index", INDICES)):
        for t in tickers:
            if (OUT / f"{t}.csv").exists():
                continue
            df = fetch_candles(market, t)
            df.to_csv(OUT / f"{t}.csv", index=False)
            span = f"{df['begin'].min()[:7]} – {df['begin'].max()[:7]}" if len(df) else "нет данных"
            print(f"{t:6s} {len(df):4d} мес.  {span}")
