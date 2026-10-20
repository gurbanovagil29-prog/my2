"""Скачивание с сайта Банка России: дневная RUONIA и G-кривая ОФЗ.

RUONIA — выгрузка XLSX за весь период одним запросом.
Кривая бескупонной доходности (G-кривая) на сайте отдаётся только на одну
дату, поэтому берём её на последний рабочий день каждого месяца
(рабочие дни определяем по датам публикации RUONIA).
"""
import re
import time
import urllib.request
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "cbr"
OUT.mkdir(parents=True, exist_ok=True)

RUONIA_XLSX = ("https://www.cbr.ru/Queries/UniDbQuery/DownloadExcel/14315?Posted=True"
               "&From=01.01.2015&To=30.09.2026&FromDate=01%2F01%2F2015&ToDate=09%2F30%2F2026")
ZCYC = "https://www.cbr.ru/hd_base/zcyc_params/zcyc/?UniDbQuery.Posted=True&UniDbQuery.To={}"


def get(url: str, tries: int = 5) -> bytes:
    # соединение через прокси иногда рвётся — повторяем с паузой
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except OSError:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)


def to_num(s: str):
    # ЦБ ставит «—», если на дату по сроку нет оценки
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def zcyc_on(date: pd.Timestamp) -> list:
    """Доходности G-кривой (% годовых) на дату по 12 срокам."""
    html = get(ZCYC.format(date.strftime("%d.%m.%Y"))).decode("utf-8")
    table = html[html.index('<table class="data">'):]
    table = table[:table.index("</table>")]
    cells = re.findall(r"<t[hd]>\s*([^<]*?)\s*</t[hd]>", table)
    return cells


if __name__ == "__main__":
    ruonia_path = OUT / "ruonia.xlsx"
    if not ruonia_path.exists():
        ruonia_path.write_bytes(get(RUONIA_XLSX))
    ruo = pd.read_excel(ruonia_path)[["DT", "ruo"]].sort_values("DT")
    print(f"RUONIA: {len(ruo)} дней, {ruo.DT.min():%d.%m.%Y} – {ruo.DT.max():%d.%m.%Y}")

    month_ends = ruo.groupby(ruo.DT.dt.to_period("M"))["DT"].max()
    rows = []
    trade_days = list(ruo.DT)
    for d in month_ends:
        # если на последний день месяца кривой нет (28.02.2022 биржа была закрыта),
        # откатываемся на предыдущие рабочие дни
        i = trade_days.index(d)
        while True:
            cells = zcyc_on(trade_days[i])
            n = len(cells) // 2  # первая строка — сроки, вторая — доходности
            terms, ylds = cells[1:n], [to_num(y) for y in cells[n + 1:]]
            if any(y is not None for y in ylds):
                break
            i -= 1
        rows.append({"date": trade_days[i].date(),
                     **{f"y{t}": y for t, y in zip(terms, ylds)}})
        time.sleep(0.3)
    g = pd.DataFrame(rows)
    g.to_csv(OUT / "gcurve_month_end.csv", index=False)
    print(f"G-кривая: {len(g)} месяцев, пропусков {int(g.isna().any(axis=1).sum())}")
    print(g.head(2).to_string(), g.tail(2).to_string(), sep="\n")
