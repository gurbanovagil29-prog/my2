"""Сборка месячных рядов для ДЗ2 из сырых данных.

На выходе (data/processed):
  prices.csv         — цены закрытия на конец месяца после склейки тикеров;
  dividends.csv      — дивиденды на акцию, отнесённые к месяцу экс-дивидендной даты;
  ret_price.csv      — ценовые доходности (без дивидендов);
  ret_total.csv      — полные доходности: (P_t + D_t) / P_{t-1} - 1;
  market_rf.csv      — IMOEX, MCFTR, RUONIA за месяц, 3М и 1Г ставки G-кривой.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from download_moex import SHARES

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

# новые тикеры и их предшественники: (старый, последний месяц старого)
SPLICE = {"YDEX": ("YNDX", "2024-06"), "X5": ("FIVE", "2024-04"), "HEAD": ("HHRU", "2024-08")}
# T уже содержит историю TCSG (Мосбиржа склеила и пересчитала на сплит 1:10)
OLD = {"YNDX", "TCSG", "FIVE", "HHRU"}
TICKERS = [t for t in SHARES if t not in OLD]

# строки dohod.ru, которые не относятся к обыкновенной акции (сверено со smart-lab)
DROP_DIVS = {("VTBR", "2021-07-15", 0.087)}

# переход на расчёты T+1 на Мосбирже
T1_FROM = pd.Timestamp("2023-07-31")


def monthly_close(t: str) -> pd.Series:
    d = pd.read_csv(RAW / "moex" / f"{t}.csv", parse_dates=["begin"])
    return pd.Series(d["close"].values, index=d["begin"].dt.to_period("M"), name=t)


def ex_date(record: pd.Timestamp, bdays: pd.DatetimeIndex) -> pd.Timestamp:
    """Первый день торгов без дивиденда.

    При T+2 — за один рабочий день до даты закрытия реестра,
    при T+1 (с 31.07.2023) — сама дата закрытия реестра (или ближайший рабочий день до неё).
    """
    pos = bdays.searchsorted(record, side="right") - 1  # последний рабочий день <= даты реестра
    return bdays[pos] if record >= T1_FROM else bdays[pos - 1]


if __name__ == "__main__":
    # --- рабочие дни: даты публикации RUONIA
    ruo = pd.read_excel(RAW / "cbr" / "ruonia.xlsx")[["DT", "ruo"]].sort_values("DT")
    bdays = pd.DatetimeIndex(ruo["DT"])

    # --- цены со склейкой старых и новых тикеров
    prices = {}
    for t in TICKERS:
        p = monthly_close(t)
        if t in SPLICE:
            old, last = SPLICE[t]
            p = pd.concat([monthly_close(old).loc[:last], p])
        prices[t] = p
    prices = pd.DataFrame(prices).sort_index()
    prices.index.name = "month"

    # --- дивиденды по месяцу экс-даты
    divs = pd.DataFrame(0.0, index=prices.index, columns=TICKERS)
    for t in TICKERS:
        d = pd.read_csv(RAW / "dividends" / f"{t}.csv", parse_dates=["record_date"])
        d = d[[(t, r.strftime("%Y-%m-%d"), v) not in DROP_DIVS
               for r, v in zip(d.record_date, d.dividend)]]
        d = d[(d.record_date >= bdays[1]) & (d.record_date <= bdays[-1])]
        d["month"] = [ex_date(r, bdays).to_period("M") for r in d.record_date]
        s = d.groupby("month")["dividend"].sum()
        divs.loc[s.index.intersection(divs.index), t] = s

    # --- доходности; месяцы без торгов (FIVE→X5: 05.2024–12.2024) дают NaN,
    #     доходность через разрыв не считаем
    prev = prices.shift(1)
    ret_price = prices / prev - 1
    ret_total = (prices + divs) / prev - 1
    gap = prices.isna() | prev.isna()
    ret_price[gap], ret_total[gap] = np.nan, np.nan

    # --- рынок и безрисковая ставка
    imoex, mcftr = monthly_close("IMOEX"), monthly_close("MCFTR")
    # RUONIA за месяц: капитализируем дневную ставку на каждый календарный день
    # (ставка пятницы действует и в выходные), конвенция ACT/365
    daily = ruo.set_index("DT")["ruo"].resample("D").ffill() / 100
    rf_ruonia = (1 + daily / 365).groupby(daily.index.to_period("M")).prod() - 1
    g = pd.read_csv(RAW / "cbr" / "gcurve_month_end.csv", parse_dates=["date"])
    g.index = g["date"].dt.to_period("M")
    # ставка G-кривой известна на конец месяца t-1 и применяется к месяцу t
    rf_ofz3m = ((1 + g["y0.25"] / 100) ** (1 / 12) - 1).shift(1)

    mkt = pd.DataFrame({
        "imoex_ret": imoex / imoex.shift(1) - 1,
        "mcftr_ret": mcftr / mcftr.shift(1) - 1,
        "rf_ruonia": rf_ruonia,
        "rf_ofz3m": rf_ofz3m,
        "ofz1y_annual": g["y1.00"] / 100,
    }).reindex(prices.index)
    mkt.index.name = "month"

    for name, df in [("prices", prices), ("dividends", divs), ("ret_price", ret_price),
                     ("ret_total", ret_total), ("market_rf", mkt)]:
        df.to_csv(OUT / f"{name}.csv")

    print("Акций:", len(TICKERS), "| месяцев:", len(prices))
    print("Средняя дивдоходность, % годовых (полная минус ценовая):")
    print(((ret_total - ret_price).mean() * 1200).round(1).sort_values(ascending=False).to_string())
    print(mkt.describe().T[["mean", "min", "max"]].round(4))
