#!/usr/bin/env python3
"""График спреда акция − фьючерс по данным Мосбиржи (ISS API, бесплатно, без ключа).

Примеры:
    python3 spread.py                                  # PHOR vs PHZ6, часовые свечи
    python3 spread.py --interval 24                    # дневные свечи
    python3 spread.py --interval 10 --days 5           # 10-минутки за 5 дней
    python3 spread.py --stock SBER --fut SRZ6          # любая другая пара

Интервалы ISS: 1, 10, 60 (минуты), 24 (день), 7 (неделя), 31 (месяц).
"""
import argparse
from datetime import date, timedelta

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import requests

ISS = "https://iss.moex.com/iss"


def fetch_candles(path, interval, date_from, date_till):
    """Загружает свечи постранично (ISS отдаёт не больше 500 строк за запрос)."""
    rows, start = [], 0
    while True:
        r = requests.get(
            f"{ISS}/{path}/candles.json",
            params={
                "interval": interval,
                "from": date_from,
                "till": date_till,
                "start": start,
                "iss.meta": "off",
            },
            timeout=30,
        )
        r.raise_for_status()
        block = r.json()["candles"]
        if not block["data"]:
            break
        rows += [dict(zip(block["columns"], row)) for row in block["data"]]
        start += len(block["data"])
    if not rows:
        raise SystemExit(f"Нет данных: {path}")
    df = pd.DataFrame(rows)
    df["begin"] = pd.to_datetime(df["begin"])
    return df.set_index("begin")["close"]


def futures_info(secid):
    r = requests.get(
        f"{ISS}/engines/futures/markets/forts/securities/{secid}.json",
        params={"iss.meta": "off", "iss.only": "securities"},
        timeout=30,
    )
    r.raise_for_status()
    block = r.json()["securities"]
    if not block["data"]:
        raise SystemExit(f"Фьючерс {secid} не найден")
    return dict(zip(block["columns"], block["data"][0]))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--stock", default="PHOR", help="тикер акции (режим TQBR)")
    p.add_argument("--fut", default="PHZ6", help="код фьючерса на FORTS")
    p.add_argument("--interval", type=int, default=60, help="таймфрейм свечей (по умолчанию 60 мин)")
    p.add_argument("--days", type=int, help="сколько дней истории (по умолчанию с начала торгов фьючерсом)")
    p.add_argument("--out", default="spread.png", help="файл с графиком")
    args = p.parse_args()

    info = futures_info(args.fut)
    lot = info["LOTVOLUME"]  # акций в одном контракте
    expiry = info["LASTTRADEDATE"]
    till = date.today().isoformat()
    since = (date.today() - timedelta(days=args.days)).isoformat() if args.days else info["FRSTTRADE"]

    stock = fetch_candles(
        f"engines/stock/markets/shares/boards/TQBR/securities/{args.stock}", args.interval, since, till
    )
    fut = fetch_candles(f"engines/futures/markets/forts/securities/{args.fut}", args.interval, since, till)

    # Фьючерс котируется за контракт: приводим к цене одной акции
    df = pd.concat({"stock": stock, "fut": fut / lot}, axis=1, join="inner").dropna()
    df["spread"] = df["stock"] - df["fut"]
    df["spread_pct"] = df["spread"] / df["fut"] * 100
    df.to_csv(args.out.rsplit(".", 1)[0] + ".csv")

    s = df["spread"]
    mean, std = s.mean(), s.std()
    last = df.iloc[-1]

    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=(12, 10), sharex=True, gridspec_kw={"height_ratios": [2, 2, 1.2]}
    )
    title = f"{args.stock} − {args.fut}  (экспирация {expiry}, таймфрейм {args.interval})"
    fig.suptitle(title, fontsize=13)

    ax1.plot(df.index, df["stock"], label=f"{args.stock}, ₽", lw=1.2)
    ax1.plot(df.index, df["fut"], label=f"{args.fut}, ₽ за акцию", lw=1.2)
    ax1.legend(loc="upper left")
    ax1.grid(alpha=0.3)

    ax2.plot(df.index, s, color="black", lw=1.2)
    ax2.axhline(mean, color="tab:blue", ls="--", lw=1, label=f"среднее {mean:.1f}")
    ax2.axhline(mean + 2 * std, color="tab:red", ls=":", lw=1, label=f"±2σ ({std:.1f})")
    ax2.axhline(mean - 2 * std, color="tab:red", ls=":", lw=1)
    ax2.axhline(0, color="gray", lw=0.8)
    ax2.set_ylabel("Спред, ₽")
    ax2.legend(loc="upper left")
    ax2.grid(alpha=0.3)
    ax2.annotate(
        f"{last['spread']:.0f} ₽",
        (df.index[-1], last["spread"]),
        xytext=(5, 0),
        textcoords="offset points",
        va="center",
        fontweight="bold",
    )

    ax3.plot(df.index, df["spread_pct"], color="tab:green", lw=1.2)
    ax3.axhline(0, color="gray", lw=0.8)
    ax3.set_ylabel("Спред, %")
    ax3.grid(alpha=0.3)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))

    fig.tight_layout()
    fig.savefig(args.out, dpi=120)

    print(f"Период: {df.index[0]} — {df.index[-1]}, свечей: {len(df)}")
    print(f"Последнее: акция {last['stock']:.0f}, фьючерс {last['fut']:.0f}, "
          f"спред {last['spread']:.0f} ₽ ({last['spread_pct']:.2f}%)")
    print(f"Спред: среднее {mean:.1f}, σ {std:.1f}, min {s.min():.0f}, max {s.max():.0f}")
    print(f"График: {args.out}")


if __name__ == "__main__":
    main()
