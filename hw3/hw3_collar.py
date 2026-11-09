"""ДЗ3. Zero-cost collar на опционах Сбербанка (Мосбиржа, срочный рынок).

Хеджируемая позиция — длинный фьючерс SBRF (1 контракт = 100 акций Сбербанка).
Collar: покупаем пут со страйком ниже текущей цены (страховка от падения) и
продаём колл со страйком выше (премия колла оплачивает пут).

Опционы на фьючерс на Мосбирже маржируемые: премия не платится сразу, а
переходит через вариационную маржу. Поэтому цена такого опциона — формула
Блэка для фьючерсов без дисконтирования:
    c = F·N(d1) − K·N(d2),   p = K·N(−d2) − F·N(−d1),
    d1 = [ln(F/K) + σ²T/2] / (σ√T),   d2 = d1 − σ√T.
Это формула BSM из лекции, где S0 заменена на цену фьючерса F, а множитель
e^(−rT) убран: ставка уже заложена в F, а премию никто не финансирует.
Проверка: для таких опционов выполняется паритет c − p = F − K (без дисконта).

Запуск: python hw3_collar.py  (данные — scripts/download_options.py)
Результат: results/*.xlsx, figures/*.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
RES = ROOT / "results"; RES.mkdir(exist_ok=True)

plt.rcParams.update({"font.size": 12, "axes.grid": True, "grid.alpha": 0.3,
                     "axes.spines.top": False, "axes.spines.right": False})
C_FUT, C_PUT, C_CALL, C_OPT, C_TOT = "#8A94A6", "#2C5A87", "#C0392B", "#E08A3C", "#15233B"

# ---------------------------------------------------------------------------
# 1. Формула Блэка и греки (маржируемый опцион на фьючерс)
# ---------------------------------------------------------------------------

def black(F, K, T, sigma, kind):
    d1 = (np.log(F / K) + 0.5 * sigma ** 2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if kind == "C":
        return F * norm.cdf(d1) - K * norm.cdf(d2)
    return K * norm.cdf(-d2) - F * norm.cdf(-d1)


def implied_vol(price, F, K, T, kind):
    """Подразумеваемая волатильность: σ, при которой формула даёт рыночную цену."""
    return brentq(lambda s: black(F, K, T, s, kind) - price, 1e-4, 5.0)


def greeks(F, K, T, sigma, kind):
    """Греки на 1 контракт. Дельта — в фьючерсах; вега — руб. на +1 п.п. волатильности;
    тета — руб. в календарный день. Ро у маржируемого опциона ≈ 0: премия не
    дисконтируется, а ставка влияет только через цену фьючерса."""
    d1 = (np.log(F / K) + 0.5 * sigma ** 2 * T) / (sigma * np.sqrt(T))
    pdf = norm.pdf(d1)
    delta = norm.cdf(d1) if kind == "C" else norm.cdf(d1) - 1
    return {"Дельта": delta,
            "Гамма, на 1000 руб. цены": pdf / (F * sigma * np.sqrt(T)) * 1000,
            "Вега, руб. на +1 п.п. σ": F * pdf * np.sqrt(T) / 100,
            "Тета, руб. в день": -F * pdf * sigma / (2 * np.sqrt(T)) / 365}


# ---------------------------------------------------------------------------
# 2. Доска опционов на дату анализа
# ---------------------------------------------------------------------------
DATE, EXPIRY = "2026-11-06", "2026-12-16"          # последний полный торговый день; экспирация
T = (pd.Timestamp(EXPIRY) - pd.Timestamp(DATE)).days / 365

fut = pd.read_csv(RAW / "futures_SRZ6.csv").set_index("TRADEDATE")
F0 = fut.loc[DATE, "SETTLEPRICE"]                    # расчётная цена фьючерса SRZ6, руб. за 100 акций
shares = pd.read_csv(RAW / "sber_shares.csv")
shares = shares[shares["BOARDID"] == "TQBR"].set_index("TRADEDATE")["CLOSE"]

ref = pd.read_csv(RAW / "sbrf_options_reference.csv")
hist = pd.read_csv(RAW / "options_dec2026_history.csv")
board = (hist[hist["TRADEDATE"] == DATE]
         .merge(ref[["SECID", "SHORTNAME", "STRIKE", "OPTIONTYPE", "IMNP", "IMP", "IMBUY"]], on="SECID"))
board = board.rename(columns={"STRIKE": "Страйк", "OPTIONTYPE": "Тип"})

piv = board.pivot_table(index="Страйк", columns="Тип",
                        values=["SETTLEPRICE", "OPENPOSITION", "VOLUME"], aggfunc="first")
piv.columns = [f"{a}_{b}" for a, b in piv.columns]
piv = piv.rename(columns={"SETTLEPRICE_C": "Премия колл", "SETTLEPRICE_P": "Премия пут",
                          "OPENPOSITION_C": "Откр. позиции колл", "OPENPOSITION_P": "Откр. позиции пут",
                          "VOLUME_C": "Объём колл", "VOLUME_P": "Объём пут"})
piv = piv[(piv.index >= 25000) & (piv.index <= 35000)]

# паритет пут-колл для маржируемых опционов: c − p = F − K
piv["c − p"] = piv["Премия колл"] - piv["Премия пут"]
piv["F − K"] = F0 - piv.index
piv["IV колл"] = [implied_vol(c, F0, k, T, "C") for k, c in piv["Премия колл"].items()]
piv["IV пут"] = [implied_vol(p, F0, k, T, "P") for k, p in piv["Премия пут"].items()]
# одна улыбка: для страйков ниже F берём путы (они вне денег), выше — коллы
piv["IV (OTM)"] = np.where(piv.index < F0, piv["IV пут"], piv["IV колл"])

print(f"Дата {DATE}: фьючерс SRZ6 = {F0:.0f} руб. ({F0/100:.2f} за акцию), акция SBER = {shares[DATE]:.2f}")
print(f"До экспирации {EXPIRY}: {T*365:.0f} дн., T = {T:.4f} года")
print("Паритет c − p = F − K, макс. расхождение:", (piv["c − p"] - piv["F − K"]).abs().max(), "руб.")

# ---------------------------------------------------------------------------
# 3. Выбор пары: пут ~6% ниже цены, колл с максимально близкой премией
# ---------------------------------------------------------------------------

def candidate_pairs(piv, F, put_strikes):
    rows = []
    for kp in put_strikes:
        pp = piv.loc[kp, "Премия пут"]
        calls = piv[piv.index > F]
        kc = (calls["Премия колл"] - pp).abs().idxmin()
        pc = calls.loc[kc, "Премия колл"]
        rows.append({"Пут: страйк": kp, "Пут: премия": pp, "Колл: страйк": kc, "Колл: премия": pc,
                     "Чистая премия (+ получаем)": pc - pp,
                     "Пол коридора, %": (kp / F - 1) * 100, "Потолок коридора, %": (kc / F - 1) * 100})
    return pd.DataFrame(rows)

pairs = candidate_pairs(piv, F0, [29000, 28500, 28000, 27500, 27000])
K1, K2 = 28000, 32000                       # выбранная пара
P1, P2 = piv.loc[K1, "Премия пут"], piv.loc[K2, "Премия колл"]
NET = P2 - P1                               # +3 руб.: сами получаем премию
print(pairs.round(1).to_string(index=False))
print(f"Выбор: купить пут {K1} за {P1:.0f}, продать колл {K2} за {P2:.0f}, чистая премия {NET:+.0f} руб.")

# Ликвидность: лучшие заявки на покупку и продажу в торговой сессии 09.11.2026.
# «Ноль» получается по расчётным ценам; при сделке по рынку платим спред.
import json
snap = json.loads((RAW / "sbrf_board_snapshot_2026-11-09.json").read_text())
md = pd.DataFrame(snap["marketdata"]["data"], columns=snap["marketdata"]["columns"]).set_index("SECID")
sid = lambda k, t: board.loc[(board["Страйк"] == k) & (board["Тип"] == t), "SECID"].iloc[0]
liq = pd.DataFrame({"Опцион": [f"Пут {K1}", f"Колл {K2}"],
                    "Расчётная цена 06.11": [P1, P2],
                    "Лучшая покупка (bid) 09.11": [md.loc[sid(K1, "P"), "BID"], md.loc[sid(K2, "C"), "BID"]],
                    "Лучшая продажа (offer) 09.11": [md.loc[sid(K1, "P"), "OFFER"], md.loc[sid(K2, "C"), "OFFER"]],
                    "Открытые позиции 06.11": [piv.loc[K1, "Откр. позиции пут"], piv.loc[K2, "Откр. позиции колл"]]})
COST_MKT = liq.iloc[0, 3] - liq.iloc[1, 2]   # купить пут по offer, продать колл по bid
print(liq.to_string(index=False)); print(f"Стоимость collar по рыночным заявкам: {COST_MKT:.0f} руб.")

# ---------------------------------------------------------------------------
# 4. Греки и IV выбранных опционов
# ---------------------------------------------------------------------------
iv1, iv2 = piv.loc[K1, "IV пут"], piv.loc[K2, "IV колл"]
iv_atm = piv.loc[30000, "IV (OTM)"] if 30000 in piv.index else np.nan
g_put, g_call = greeks(F0, K1, T, iv1, "P"), greeks(F0, K2, T, iv2, "C")
gr = pd.DataFrame({"Купленный пут 28000": {"Премия, руб.": P1, "IV, %": iv1 * 100, **g_put},
                   "Проданный колл 32000": {"Премия, руб.": P2, "IV, %": iv2 * 100,
                                            **{k: -v for k, v in g_call.items()}}})
gr["Фьючерс (1 шт.)"] = {"Премия, руб.": np.nan, "IV, %": np.nan, "Дельта": 1.0,
                         "Гамма, на 1000 руб. цены": 0, "Вега, руб. на +1 п.п. σ": 0, "Тета, руб. в день": 0}
gr["Весь collar"] = gr[["Купленный пут 28000", "Проданный колл 32000", "Фьючерс (1 шт.)"]].iloc[2:].sum(axis=1)
print(gr.round(4).to_string())

fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(piv.index, piv["IV (OTM)"] * 100, "o-", color=C_TOT)
ax.axvline(F0, color=C_FUT, ls="--"); ax.text(F0, ax.get_ylim()[1], " F = 29 814", va="top", color=C_FUT)
ax.scatter([K1, K2], [iv1 * 100, iv2 * 100], s=140, color=[C_PUT, C_CALL], zorder=3)
ax.annotate("купленный пут", (K1, iv1 * 100), xytext=(8, 8), textcoords="offset points", color=C_PUT)
ax.annotate("проданный колл", (K2, iv2 * 100), xytext=(-110, 10), textcoords="offset points", color=C_CALL)
ax.set_xlabel("Страйк, руб. за контракт (100 акций)"); ax.set_ylabel("IV, % годовых")
ax.set_title("Улыбка волатильности: опционы SBRF, экспирация 16.12.2026")
plt.tight_layout(); plt.savefig(FIG / "02_smile.png", dpi=150); plt.close()

# ---------------------------------------------------------------------------
# 5. Payoff на дату экспирации (руб. на 1 контракт = 100 акций)
# ---------------------------------------------------------------------------

def collar_payoff(FT, F0, K1, P1, K2, P2):
    fut_pnl = FT - F0
    put_pnl = np.maximum(K1 - FT, 0) - P1
    call_pnl = P2 - np.maximum(FT - K2, 0)
    return pd.DataFrame({"Фьючерс без хеджа": fut_pnl, "Купленный пут": put_pnl,
                         "Проданный колл": call_pnl, "Опционы вместе (пут + колл)": put_pnl + call_pnl,
                         "Collar: фьючерс + опционы": fut_pnl + put_pnl + call_pnl}, index=FT)

FT = np.arange(24000, 36001, 250)
pay = collar_payoff(FT, F0, K1, P1, K2, P2)
pay.index.name = "Цена фьючерса на экспирации"

fig, ax = plt.subplots(figsize=(10, 6))
styles = [("Фьючерс без хеджа", C_FUT, "--", 2), ("Купленный пут", C_PUT, "-", 1.6),
          ("Проданный колл", C_CALL, "-", 1.6), ("Опционы вместе (пут + колл)", C_OPT, ":", 2.2),
          ("Collar: фьючерс + опционы", C_TOT, "-", 3.2)]
for col, c, ls, lw in styles:
    ax.plot(pay.index, pay[col], color=c, ls=ls, lw=lw, label=col)
ax.axhline(0, color="black", lw=0.8)
for k in (K1, K2):
    ax.axvline(k, color="#B9C4D3", lw=1)
ax.axvline(F0, color=C_FUT, lw=1, ls=":")
lo, hi = K1 - F0 + NET, K2 - F0 + NET
ax.annotate(f"убыток не больше −{abs(lo):,.0f} руб.".replace(",", " "), (25000, lo), xytext=(0, -22),
            textcoords="offset points", color=C_TOT, fontweight="bold")
ax.annotate(f"прибыль не больше +{hi:,.0f} руб.".replace(",", " "), (33500, hi), xytext=(-40, 10),
            textcoords="offset points", color=C_TOT, fontweight="bold")
ax.set_xlabel("Цена фьючерса SRZ6 на 16.12.2026, руб. (100 акций)")
ax.set_ylabel("Финансовый результат, руб. на 1 контракт")
ax.set_title(f"Zero-cost collar: купить пут {K1}, продать колл {K2}")
ax.legend(loc="upper left", fontsize=10)
plt.tight_layout(); plt.savefig(FIG / "01_payoff.png", dpi=150); plt.close()

# ---------------------------------------------------------------------------
# 6. Гарантийное обеспечение
# ---------------------------------------------------------------------------
fut_im = 5363.89  # ГО фьючерса SRZ6 на 09.11.2026 (ISS, INITIALMARGIN)
im = ref.set_index("SECID")
sec_put = board.loc[(board["Страйк"] == K1) & (board["Тип"] == "P"), "SECID"].iloc[0]
sec_call = board.loc[(board["Страйк"] == K2) & (board["Тип"] == "C"), "SECID"].iloc[0]
go = pd.DataFrame({
    "Позиция": ["Длинный фьючерс SRZ6", f"Покупка пута {K1}", f"Продажа колла {K2} (непокрытая)",
                f"Продажа колла {K2} вместе с фьючерсом (синтетическая)"],
    "Код": ["SRZ6", sec_put, sec_call, sec_call],
    "ГО, руб.": [fut_im, im.loc[sec_put, "IMBUY"], im.loc[sec_call, "IMNP"], im.loc[sec_call, "IMP"]],
})
print(go.to_string(index=False))

# ---------------------------------------------------------------------------
# 7. Ретро-тест: collar открыт 01.07.2026, экспирация 16.09.2026 (фьючерс SRU6)
# ---------------------------------------------------------------------------
BT0, BT1 = "2026-07-01", "2026-09-16"
futu = pd.read_csv(RAW / "futures_SRU6.csv").set_index("TRADEDATE")["SETTLEPRICE"]
sep = pd.read_csv(RAW / "options_sep2026_history.csv")
sep["Страйк"] = sep["SECID"].str.extract(r"SR(\d+)B")[0].astype(int)
sep["Тип"] = sep["SECID"].str[-2].map({"I": "C", "U": "P"})
F0b = futu[BT0]
Tb = (pd.Timestamp(BT1) - pd.Timestamp(BT0)).days / 365
bd = sep[sep["TRADEDATE"] == BT0].pivot_table(index="Страйк", columns="Тип", values="SETTLEPRICE")
bd = bd.rename(columns={"C": "Премия колл", "P": "Премия пут"})
bd = bd[(bd.index >= 24000) & (bd.index <= 32000)]
pairs_bt = candidate_pairs(bd, F0b, [27000, 26750, 26500, 26250])
K1b, K2b = 26500, 29500                     # тот же принцип: пут ≈ 6% ниже цены, колл с той же премией
P1b, P2b = bd.loc[K1b, "Премия пут"], bd.loc[K2b, "Премия колл"]
iv1b = implied_vol(P1b, F0b, K1b, Tb, "P"); iv2b = implied_vol(P2b, F0b, K2b, Tb, "C")
print(f"Ретро: F({BT0}) = {F0b:.0f}; пут {K1b} за {P1b:.0f} (IV {iv1b:.1%}), колл {K2b} за {P2b:.0f} (IV {iv2b:.1%})")

def settle_path(strike, kind):
    s = sep[(sep["Страйк"] == strike) & (sep["Тип"] == kind)].set_index("TRADEDATE")["SETTLEPRICE"]
    return s.loc[BT0:BT1]

path = pd.DataFrame({"Фьючерс SRU6": futu.loc[BT0:BT1],
                     f"Пут {K1b}": settle_path(K1b, "P"), f"Колл {K2b}": settle_path(K2b, "C")})
FTb = path["Фьючерс SRU6"].iloc[-1]
# в день экспирации опционы исполняются по внутренней стоимости
path.iloc[-1, 1] = max(K1b - FTb, 0); path.iloc[-1, 2] = max(FTb - K2b, 0)
path["Без хеджа, накоплено"] = path["Фьючерс SRU6"] - F0b
path["Опционы, накоплено"] = (path[f"Пут {K1b}"] - P1b) - (path[f"Колл {K2b}"] - P2b)
path["Collar, накоплено"] = path["Без хеджа, накоплено"] + path["Опционы, накоплено"]
# вариационная маржа за день = изменение расчётной цены (по каждой ноге со своим знаком)
path["Вар. маржа за день: фьючерс"] = path["Фьючерс SRU6"].diff().fillna(0)
path["Вар. маржа за день: опционы"] = path["Опционы, накоплено"].diff().fillna(path["Опционы, накоплено"].iloc[0])
path["Вар. маржа за день: collar"] = path["Collar, накоплено"].diff().fillna(path["Collar, накоплено"].iloc[0])
path["Акция SBER, руб."] = shares.reindex(path.index)
path.index.name = "Дата"

bt = pd.Series({
    "Фьючерс на 01.07.2026": F0b, "Фьючерс на 16.09.2026": FTb,
    "Результат без хеджа, руб.": FTb - F0b,
    "Результат опционов, руб.": path["Опционы, накоплено"].iloc[-1],
    "Результат collar, руб.": path["Collar, накоплено"].iloc[-1],
    "Худший день без хеджа (накоплено), руб.": path["Без хеджа, накоплено"].min(),
    "Худший день collar (накоплено), руб.": path["Collar, накоплено"].min(),
    "Лучший день без хеджа (накоплено), руб.": path["Без хеджа, накоплено"].max(),
    "Лучший день collar (накоплено), руб.": path["Collar, накоплено"].max(),
    "Ст. откл. дневной вар. маржи без хеджа, руб.": path["Вар. маржа за день: фьючерс"].std(),
    "Ст. откл. дневной вар. маржи collar, руб.": path["Вар. маржа за день: collar"].std(),
})
print(bt.round(1).to_string())

fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})
d = pd.to_datetime(path.index)
ax = axes[0]
ax.plot(d, path["Фьючерс SRU6"], color=C_TOT, lw=2)
ax.axhline(K1b, color=C_PUT, ls="--"); ax.axhline(K2b, color=C_CALL, ls="--"); ax.axhline(F0b, color=C_FUT, ls=":")
ax.text(d[-1], K1b, f"пол коридора {K1b} ", va="bottom", ha="right", color=C_PUT)
ax.text(d[0], K2b, f" потолок {K2b}", va="bottom", color=C_CALL)
ax.set_ylabel("Фьючерс SRU6, руб."); ax.set_title("Ретро-тест: collar с 01.07.2026 до экспирации 16.09.2026")
ax = axes[1]
ax.plot(d, path["Без хеджа, накоплено"], color=C_FUT, ls="--", lw=2, label="Без хеджа")
ax.plot(d, path["Collar, накоплено"], color=C_TOT, lw=2.6, label="С collar")
ax.axhline(0, color="black", lw=0.8)
ax.set_ylabel("Накопленный результат, руб."); ax.legend(loc="lower left")
plt.tight_layout(); plt.savefig(FIG / "03_backtest.png", dpi=150); plt.close()

# ---------------------------------------------------------------------------
# 8. Excel: исходные данные, расчёты (с формулами) и графики
# ---------------------------------------------------------------------------
from openpyxl import load_workbook
from openpyxl.chart import Reference, ScatterChart, Series
from openpyxl.styles import Font

xlsx = RES / "ДЗ3_collar_Сбербанк.xlsx"
params = pd.DataFrame({
    "Параметр": ["Дата анализа (последний полный торговый день)", "Базовый актив опционов", "Экспирация опционов",
                 "Дней до экспирации", "T, лет", "Цена фьючерса F0, руб. за контракт",
                 "Цена акции SBER на ту же дату, руб.", "Хеджируемая позиция",
                 "Покупаем: пут, страйк K1", "Премия пута P1, руб.", "Продаём: колл, страйк K2",
                 "Премия колла P2, руб.", "Чистая премия P2 − P1, руб.", "Модель цены"],
    "Значение": [DATE, "фьючерс SRZ6 (SBRF-12.26), 100 акций Сбербанка", EXPIRY, int(T * 365), T, F0,
                 shares[DATE], "длинный фьючерс SRZ6, 1 контракт (= 100 акций)",
                 K1, P1, K2, P2, NET,
                 "Блэк для маржируемых опционов на фьючерс, без дисконтирования"]})
with pd.ExcelWriter(xlsx, engine="openpyxl") as xw:
    params.to_excel(xw, sheet_name="Параметры", index=False)
    piv.to_excel(xw, sheet_name="Доска опционов")
    pairs.to_excel(xw, sheet_name="Выбор пары", index=False)
    liq.to_excel(xw, sheet_name="Выбор пары", index=False, startrow=len(pairs) + 3)
    gr.to_excel(xw, sheet_name="Греки и IV")
    pay.to_excel(xw, sheet_name="Payoff")
    go.to_excel(xw, sheet_name="ГО", index=False)
    path.to_excel(xw, sheet_name="Ретро-тест")
    bt.rename("Значение").to_excel(xw, sheet_name="Ретро-тест итог")
    pairs_bt.to_excel(xw, sheet_name="Ретро-тест выбор пары", index=False)

wb = load_workbook(xlsx)
# Payoff: значения заменяем формулами Excel, чтобы расчёт был виден и проверяем
ws = wb["Payoff"]
wp = wb["Параметры"]
# ссылки на параметры: F0 — B7, K1 — B10, P1 — B11, K2 — B12, P2 — B13
for r in range(2, ws.max_row + 1):
    ws[f"B{r}"] = f"=A{r}-Параметры!$B$7"
    ws[f"C{r}"] = f"=MAX(Параметры!$B$10-A{r},0)-Параметры!$B$11"
    ws[f"D{r}"] = f"=Параметры!$B$13-MAX(A{r}-Параметры!$B$12,0)"
    ws[f"E{r}"] = f"=C{r}+D{r}"
    ws[f"F{r}"] = f"=B{r}+E{r}"
ch = ScatterChart(); ch.title = "Payoff на дату экспирации"; ch.style = 13
ch.x_axis.title = "Цена фьючерса, руб."; ch.y_axis.title = "Результат, руб."
ch.height, ch.width = 12, 22
xs = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)
for col in range(2, 7):
    s = Series(Reference(ws, min_col=col, min_row=1, max_row=ws.max_row), xs, title_from_data=True)
    s.marker.symbol = "none"; s.smooth = False
    ch.series.append(s)
ws.add_chart(ch, "H2")

# Греки: формулы Блэка в Excel для проверки цен по найденной IV
wg = wb.create_sheet("Проверка формулой")
rows = [("Параметр", "Пут K1", "Колл K2"),
        ("F", F0, F0), ("K", K1, K2), ("T, лет", T, T), ("σ (IV)", iv1, iv2),
        ("d1", "=(LN(B2/B3)+B5^2/2*B4)/(B5*SQRT(B4))", "=(LN(C2/C3)+C5^2/2*C4)/(C5*SQRT(C4))"),
        ("d2", "=B6-B5*SQRT(B4)", "=C6-C5*SQRT(C4)"),
        ("Цена по формуле", "=B3*NORMSDIST(-B7)-B2*NORMSDIST(-B6)",
         "=C2*NORMSDIST(C6)-C3*NORMSDIST(C7)"),
        ("Цена биржи (settle)", P1, P2),
        ("Дельта", "=NORMSDIST(B6)-1", "=NORMSDIST(C6)"),
        ("Гамма", "=EXP(-(B6^2)/2)/SQRT(2*PI())/(B2*B5*SQRT(B4))", "=EXP(-(C6^2)/2)/SQRT(2*PI())/(C2*C5*SQRT(C4))"),
        ("Вега на 1 п.п.", "=B2*EXP(-(B6^2)/2)/SQRT(2*PI())*SQRT(B4)/100", "=C2*EXP(-(C6^2)/2)/SQRT(2*PI())*SQRT(C4)/100"),
        ("Тета в день", "=-B2*EXP(-(B6^2)/2)/SQRT(2*PI())*B5/(2*SQRT(B4))/365",
         "=-C2*EXP(-(C6^2)/2)/SQRT(2*PI())*C5/(2*SQRT(C4))/365")]
for r in rows:
    wg.append(r)

for name in wb.sheetnames:
    w = wb[name]
    for c in w[1]:
        c.font = Font(bold=True)
    for col in w.columns:
        w.column_dimensions[col[0].column_letter].width = 22
wb["Параметры"].column_dimensions["A"].width = 48
wb["Параметры"].column_dimensions["B"].width = 62
wb.save(xlsx)
print("Сохранено:", xlsx)
