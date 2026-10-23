# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # ДЗ №2. Влияние рыночного фактора, фактора размера и фактора стоимости на доходность российских акций
#
# **Курс:** Теория финансов, Лекция 3 — «Базовое уравнение ценообразования. Классические модели ценообразования активов».
#
# **Цель:** оценить, насколько доходности 35 российских акций объясняются рыночным фактором (CAPM)
# и тремя факторами Фамы–Френча (рынок, размер SMB, стоимость HML), и сравнить премии за риск двух моделей.
#
# **Задачи:**
# 1. Собрать месячные доходности акций с учётом дивидендов, рыночный индекс и безрисковую ставку.
# 2. Оценить для каждой акции временные регрессии CAPM и трёхфакторной модели.
# 3. Сравнить модели: объяснительная сила (R²), альфы, совместный тест GRS, процедура Фамы–Макбета.
# 4. Посчитать и сравнить премии за риск и требуемую доходность по двум моделям.
# 5. Проверить устойчивость выводов (доходности без дивидендов, другая безрисковая ставка, другой рыночный фактор)
#    и посмотреть, что дают дополнительные факторы (моментум, ликвидность).
#
# **Данные** (скрипты загрузки — в папке `scripts/`):
#
# | Что | Источник | Период |
# |---|---|---|
# | Месячные цены закрытия 35 акций, индексы IMOEX и MCFTR | Мосбиржа, ISS API, режим TQBR | 01.2015–09.2026 |
# | Дивиденды на акцию, даты закрытия реестра | dohod.ru (сверка со smart-lab.ru) | 2015–2026 |
# | RUONIA (дневная), кривая бескупонной доходности ОФЗ | Банк России | 2015–2026 |
# | Факторы SMB, HML, MOM, LIQ и др. | CAPM-RU, ИПЭИ РАНХиГС (А.Е. Абрамов), aea.ru | по 12.2024 |
#
# Факторы РАНХиГС заканчиваются в 12.2024, поэтому **основной период оценки — 02.2015–12.2024 (119 месяцев)**.

# %%
# Библиотеки: pandas/numpy — работа с таблицами, statsmodels — регрессии МНК,
# scipy — распределения для тестов, matplotlib — графики
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
import matplotlib.pyplot as plt

pd.set_option("display.float_format", lambda x: f"{x:,.3f}")
pd.set_option("display.width", 160)
plt.rcParams.update({"figure.figsize": (10, 5), "axes.grid": True, "grid.alpha": 0.3,
                     "font.size": 10})

DATA = Path("data")
FIG = Path("figures"); FIG.mkdir(exist_ok=True)
RES = Path("results"); RES.mkdir(exist_ok=True)

START, END = "2015-02", "2024-12"   # основной период: по последний месяц факторов РАНХиГС
MIN_OBS = 36                        # минимум 3 года наблюдений для регрессии по акции
NW_LAGS = 3                         # лаги Ньюи–Уэста для стандартных ошибок

# %% [markdown]
# ## 1. Выборка: какие акции и почему
#
# В выборку вошли 15 бумаг из ДЗ1 и 20 крупнейших по капитализации и ликвидности акций Мосбиржи.
# Выборка покрывает основные отрасли российского рынка, поэтому акции различаются по размеру
# (от «голубых фишек» SBER, LKOH, GAZP до компаний второго эшелона RENI, MSNG, UPRO, CBOM)
# и по оценке (от «акций стоимости» с низким P/B — банки, энергетика, нефть — до «акций роста» — IT и e-commerce).
# Именно такой разброс нужен, чтобы факторы размера и стоимости могли проявиться.
#
# Что общего: все бумаги торгуются на одной площадке (Мосбиржа, режим TQBR), в рублях, входят или входили
# в индекс Мосбиржи, по всем есть данные о дивидендах. Различия — отрасль, размер, дивидендная политика,
# доля государства.

# %%
# Отрасль и группа каждой бумаги (ДЗ1 — из первого домашнего задания)
SECTORS = {
    "ROSN": "Нефть и газ", "BANEP": "Нефть и газ", "TRNFP": "Нефть и газ", "LKOH": "Нефть и газ",
    "GAZP": "Нефть и газ", "TATN": "Нефть и газ", "NVTK": "Нефть и газ", "SNGSP": "Нефть и газ",
    "BSPB": "Финансы", "CBOM": "Финансы", "RENI": "Финансы", "SBER": "Финансы", "T": "Финансы",
    "VTBR": "Финансы", "MOEX": "Финансы",
    "MAGN": "Металлы и добыча", "ALRS": "Металлы и добыча", "MTLR": "Металлы и добыча",
    "SELG": "Металлы и добыча", "GMKN": "Металлы и добыча", "PLZL": "Металлы и добыча",
    "CHMF": "Металлы и добыча", "NLMK": "Металлы и добыча", "RUAL": "Металлы и добыча",
    "HYDR": "Электроэнергетика", "FEES": "Электроэнергетика", "UPRO": "Электроэнергетика",
    "MSNG": "Электроэнергетика", "IRAO": "Электроэнергетика",
    "RTKM": "Телеком и IT", "MTSS": "Телеком и IT", "YDEX": "Телеком и IT", "HEAD": "Телеком и IT",
    "OZON": "Потребительский сектор", "X5": "Потребительский сектор",
}
HW1 = ["ROSN", "BANEP", "TRNFP", "BSPB", "CBOM", "RENI", "MAGN", "ALRS", "MTLR",
       "SELG", "HYDR", "FEES", "UPRO", "MSNG", "RTKM"]

# %% [markdown]
# ## 2. Данные
#
# ### 2.1. Доходности акций
#
# Цены Мосбиржи уже скорректированы на сплиты и консолидации (VTBR, GMKN, TRNFP, PLZL, T),
# но **не на дивиденды**. Для российских акций дивиденды — существенная часть дохода (у MTSS и SNGSP ~11–12% годовых),
# поэтому основная модель строится на **полной доходности**:
#
# $$R_{i,t} = \frac{P_{i,t} + D_{i,t}}{P_{i,t-1}} - 1,$$
#
# где $D_{i,t}$ — дивиденды с экс-дивидендной датой в месяце $t$ (при расчётах T+2 — день до закрытия реестра,
# с 31.07.2023 при T+1 — сама дата закрытия реестра). Это согласуется с Фамой–Френчем и с факторами РАНХиГС «с дивидендами».
#
# Склейка переименованных бумаг: YNDX→YDEX, FIVE→X5, HHRU→HEAD (T уже содержит историю TCSG).
# Восемь месяцев без торгов FIVE/X5 (05–12.2024) исключены — доходность через разрыв не считается.

# %%
ret_total = pd.read_csv(DATA / "processed/ret_total.csv", index_col="month")   # с дивидендами
ret_price = pd.read_csv(DATA / "processed/ret_price.csv", index_col="month")   # только цены
mkt = pd.read_csv(DATA / "processed/market_rf.csv", index_col="month")
for df in (ret_total, ret_price, mkt):
    df.index = pd.PeriodIndex(df.index, freq="M")

TICKERS = list(ret_total.columns)
print("Акций:", len(TICKERS))
mkt.tail()

# %% [markdown]
# ### 2.2. Безрисковая ставка
#
# Ключевая ставка в 2015–2026 гг. менялась от 4,25% до 21%, поэтому одна средняя ставка на весь период
# исказила бы избыточные доходности. Берём **свою ставку на каждый месяц**:
#
# * **основной вариант — RUONIA за месяц**: дневные ставки овернайт капитализируются по календарным дням
#   (ставка пятницы действует и в выходные, ACT/365). Это доход безрискового рублёвого размещения «овернайт» за месяц —
#   аналог 1-месячных T-bills у Фамы и Френча;
# * **проверка устойчивости — 3-месячные ОФЗ** с G-кривой ЦБ на конец *предыдущего* месяца
#   (ставка, известная инвестору заранее), месячная ставка $(1+y)^{1/12}-1$.
#
# Почему не RGBI, как у РАНХиГС: в их файлах «безрисковая ставка» — это месячное изменение ценового индекса ОФЗ RGBI
# (без купонов). Покажем, что это рисковый актив, а не безрисковая ставка.

# %%
ranepa = pd.read_csv(DATA / "raw/ranepa/Factor_premiums_2025-02-05.csv", sep=";", decimal=",")
ranepa.index = pd.PeriodIndex(pd.to_datetime(ranepa["Date"]), freq="M")
long_p = pd.read_csv(DATA / "raw/ranepa/Long_factor_portfolios_2025-02-05.csv", sep=";", decimal=",")
long_p.index = pd.PeriodIndex(pd.to_datetime(long_p["Date"]), freq="M")

# факторы РАНХиГС даны в процентах за месяц -> переводим в доли
fcols = ["RM", "SMB", "HML", "MOM", "LIQ", "RM_TR", "SMB_TR", "HML_TR", "MOM_TR", "LIQ_TR"]
ranepa = ranepa[fcols] / 100
rgbi = long_p["RF_RGBI_Index"] / 100

rf_cmp = pd.DataFrame({"RUONIA": mkt["rf_ruonia"], "ОФЗ 3М": mkt["rf_ofz3m"],
                       "RGBI (РАНХиГС)": rgbi}).loc[START:END] * 100
summary_rf = rf_cmp.describe().T[["mean", "std", "min", "max"]]
summary_rf["месяцев < 0"] = (rf_cmp < 0).sum()
print("Безрисковые ставки, % в месяц, 02.2015–12.2024")
summary_rf

# %%
ax = rf_cmp.plot(title="Кандидаты на безрисковую ставку, % в месяц")
ax.axhline(0, color="black", lw=0.8)
ax.set_xlabel("")
plt.tight_layout(); plt.savefig(FIG / "01_rf_compare.png", dpi=150); plt.show()

# %% [markdown]
# RGBI падал в 56 месяцах из 119, в феврале 2022 г. — на 16%, а в среднем растёт всего на 0,05% в месяц (купоны в индекс не входят).
# RUONIA всегда положительна и почти совпадает с ключевой ставкой. Поэтому рыночный фактор строим сами:
#
# $$MKT_t = R^{MCFTR}_t - r^{RUONIA}_t,$$
#
# где MCFTR — индекс Мосбиржи полной доходности (с реинвестированием дивидендов, согласован с полными доходностями акций).
# SMB и HML берём у РАНХиГС как есть: это портфели «длинная минус короткая позиция», безрисковая ставка в разнице сокращается.

# %%
# Факторы основной модели (все — в долях за месяц)
F = pd.DataFrame({
    "MKT": mkt["mcftr_ret"] - mkt["rf_ruonia"],
    "SMB": ranepa["SMB_TR"],
    "HML": ranepa["HML_TR"],
}).loc[START:END]

# Избыточные доходности акций над RUONIA
EXR = ret_total.sub(mkt["rf_ruonia"], axis=0).loc[START:END]

print("Периоды:", F.index.min(), "–", F.index.max(), "| месяцев:", len(F))
print("Наблюдений по акциям (мин/медиана/макс):",
      EXR.count().min(), int(EXR.count().median()), EXR.count().max())

# %% [markdown]
# ### 2.3. Описательная статистика акций

# %%
def ann_stats(r: pd.DataFrame, rf: pd.Series) -> pd.DataFrame:
    """Годовые характеристики по месячным доходностям: среднее ×12, волатильность ×√12, Шарп."""
    ex = r.sub(rf, axis=0)
    out = pd.DataFrame({
        "Отрасль": pd.Series(SECTORS),
        "ДЗ1": pd.Series({t: "да" if t in HW1 else "" for t in r.columns}),
        "Месяцев": r.count(),
        "Доходность, % год.": r.mean() * 1200,
        "Волатильность, % год.": r.std() * np.sqrt(12) * 100,
        "Шарп": ex.mean() / ex.std() * np.sqrt(12),
        "Дивиденды, % год.": (ret_total - ret_price).loc[r.index].mean()[r.columns] * 1200,
    })
    return out.loc[r.columns]

desc = ann_stats(ret_total.loc[START:END], mkt["rf_ruonia"].loc[START:END])
desc.sort_values("Шарп", ascending=False)

# %%
# Накопленный рост 1 рубля: рынок с дивидендами, без дивидендов и безрисковое размещение
grow = (1 + mkt[["mcftr_ret", "imoex_ret", "rf_ruonia"]].loc[START:"2026-09"]).cumprod()
grow.columns = ["MCFTR (с дивидендами)", "IMOEX (без дивидендов)", "RUONIA"]
ax = grow.plot(title="Рост 1 рубля, вложенного в 01.2015")
ax.axvline(pd.Period(END, "M"), color="grey", ls="--", lw=0.8)
ax.text(pd.Period(END, "M"), ax.get_ylim()[1] * 0.95, " конец данных РАНХиГС", color="grey")
ax.set_xlabel("")
plt.tight_layout(); plt.savefig(FIG / "02_market_growth.png", dpi=150); plt.show()

# %% [markdown]
# ### 2.4. Факторы

# %%
fac_stats = pd.DataFrame({
    "Среднее, % мес.": F.mean() * 100,
    "Среднее, % год.": F.mean() * 1200,
    "Ст. откл., % мес.": F.std() * 100,
    "t-стат. среднего": F.mean() / F.std() * np.sqrt(F.count()),
})
print("Факторы 02.2015–12.2024")
display(fac_stats)
print("Корреляции факторов")
F.corr()

# %%
ax = (1 + F).cumprod().plot(title="Накопленная доходность факторов (портфели с нулевыми вложениями)")
ax.set_xlabel("")
plt.tight_layout(); plt.savefig(FIG / "03_factors_cum.png", dpi=150); plt.show()

# %% [markdown]
# **Наблюдения.** Премия за рыночный риск за 2015–2024 гг. — около 5% годовых, но статистически незначима (t ≈ 0,8):
# высокие ставки ЦБ и обвал 2022 г. «съели» большую часть превышения акций над депозитом
# (а в 2025–2026 гг. MCFTR и вовсе отстал от RUONIA). SMB в среднем положителен и значим (~18% годовых)
# во многом за счёт взрывного роста малых компаний в 2023 г. (SMB за год +137%). HML отрицателен и незначим:
# «акции стоимости» в России за десятилетие не обогнали «акции роста».
# Корреляции факторов низкие — мультиколлинеарность в регрессиях не грозит.

# %% [markdown]
# ## 3. Методология
#
# **Шаг 1. Временные регрессии** (для каждой акции $i$ отдельно, МНК по месяцам):
#
# * CAPM: $\;R_{i,t} - r_{f,t} = \alpha_i + \beta_i\,MKT_t + \varepsilon_{i,t}$
# * Фама–Френч: $\;R_{i,t} - r_{f,t} = \alpha_i + b_i\,MKT_t + s_i\,SMB_t + h_i\,HML_t + \varepsilon_{i,t}$
#
# Беты — «количество риска» акции; альфа — средняя доходность, которую факторы не объясняют
# (если модель верна, $\alpha_i = 0$). Стандартные ошибки — Ньюи–Уэста (HAC, 3 лага): устойчивы
# к гетероскедастичности и автокорреляции остатков, что важно для кризисных месяцев (2020, 2022).
#
# **Шаг 2. Сравнение моделей:** R² и скорректированный R², число значимых альф, средняя |α|,
# совместный тест GRS (Gibbons, Ross, Shanken, 1989): $H_0: \alpha_1 = \dots = \alpha_N = 0$.
#
# **Шаг 3. Цена риска (Фама–Макбет, 1973):** каждый месяц регрессируем доходности акций на их беты,
# усредняем коэффициенты по времени — получаем рыночную оценку премий $\lambda_k$.
#
# **Шаг 4. Премии за риск и требуемая доходность:**
# $\;E[R_i] - r_f = \sum_k \beta_{i,k}\,\lambda_k$, где $\lambda_k$ — средняя доходность фактора за период;
# требуемая доходность = текущая безрисковая ставка (1-летняя ОФЗ на дату анализа) + премия.

# %%
def ts_regress(y: pd.Series, X: pd.DataFrame) -> dict:
    """Временная регрессия y на факторы X с константой; ошибки Ньюи–Уэста."""
    d = pd.concat([y, X], axis=1).dropna()
    if len(d) < MIN_OBS:
        return None
    res = sm.OLS(d.iloc[:, 0], sm.add_constant(d.iloc[:, 1:])).fit(
        cov_type="HAC", cov_kwds={"maxlags": NW_LAGS})
    out = {"n": int(res.nobs), "R2": res.rsquared, "R2_adj": res.rsquared_adj,
           "resid_vol": res.resid.std() * np.sqrt(12)}
    for k in res.params.index:
        name = "alpha" if k == "const" else k
        out[name] = res.params[k]
        out[f"t_{name}"] = res.tvalues[k]
    return out


def run_model(EXR: pd.DataFrame, X: pd.DataFrame) -> pd.DataFrame:
    """Оценивает модель для всех акций; альфа переводится в % годовых."""
    rows = {t: ts_regress(EXR[t], X) for t in EXR.columns}
    tab = pd.DataFrame({t: r for t, r in rows.items() if r is not None}).T
    tab["alpha_%год"] = tab["alpha"] * 1200
    return tab

# %% [markdown]
# ## 4. Результаты CAPM

# %%
capm = run_model(EXR, F[["MKT"]])
capm_view = capm[["n", "alpha_%год", "t_alpha", "MKT", "t_MKT", "R2"]].rename(
    columns={"MKT": "beta", "t_MKT": "t_beta"})
capm_view.sort_values("beta", ascending=False)

# %% [markdown]
# **Интерпретация CAPM.**
# * Все беты положительны и значимы, от 0,55 (CBOM) до 1,66 (HEAD). Выше рынка (β > 1,3) — компании роста и крупнейшие
#   банки/нефтяники: HEAD, OZON, T, MTLR, ROSN, SBER. Ниже рынка (β < 0,7) — «защитные» бумаги с регулируемым или
#   стабильным бизнесом: электроэнергетика (HYDR, IRAO), телеком (RTKM), привилегированные акции с дивидендной формулой
#   (SNGSP, TRNFP), золотодобытчик PLZL (золото — защитный актив в кризис).
# * Средний R² ≈ 0,38: рынок объясняет около трети колебаний доходности отдельной акции, остальное — специфический риск.
# * Альфы в большинстве незначимы — для большинства акций CAPM не отвергается. Исключения: BSPB (+27% год., t = 2,6),
#   HEAD (+36%, t = 2,1) и VTBR (−21%, t = −3,1).

# %% [markdown]
# ## 5. Результаты трёхфакторной модели Фамы–Френча

# %%
ff3 = run_model(EXR, F[["MKT", "SMB", "HML"]])
ff3_view = ff3[["n", "alpha_%год", "t_alpha", "MKT", "t_MKT", "SMB", "t_SMB",
                "HML", "t_HML", "R2", "R2_adj"]].rename(columns={"MKT": "b", "SMB": "s", "HML": "h"})
ff3_view.sort_values("s", ascending=False)

# %%
# Сколько акций значимо нагружены на каждый фактор (|t| > 1,96)
load_cnt = pd.DataFrame({
    "значимо > 0": [(ff3[f"t_{f}"] > 1.96).sum() for f in ["MKT", "SMB", "HML"]],
    "значимо < 0": [(ff3[f"t_{f}"] < -1.96).sum() for f in ["MKT", "SMB", "HML"]],
}, index=["MKT", "SMB", "HML"])
load_cnt

# %%
# Беты по трём факторам: кто ведёт себя как малая компания (s>0), кто как акция стоимости (h>0)
fig, axes = plt.subplots(1, 3, figsize=(15, 8), sharey=True)
order = ff3_view.sort_values("b").index
for ax, (col, tcol, title) in zip(axes, [("b", "t_MKT", "Рынок (b)"), ("s", "t_SMB", "Размер (s)"),
                                         ("h", "t_HML", "Стоимость (h)")]):
    vals = ff3_view.loc[order, col]
    sig = ff3_view.loc[order, tcol].abs() > 1.96
    ax.barh(order, vals, color=np.where(sig, "#1f77b4", "#c6dbef"))
    ax.axvline(0, color="black", lw=0.8)
    ax.set_title(title)
fig.suptitle("Нагрузки на факторы Фамы–Френча (тёмные — значимы на 5%)")
plt.tight_layout(); plt.savefig(FIG / "04_ff3_betas.png", dpi=150); plt.show()

# %%
# Версия для слайда: только акции со значимой нагрузкой на размер или стоимость, крупный шрифт
sig_any = ff3_view[(ff3_view["t_SMB"].abs() > 1.96) | (ff3_view["t_HML"].abs() > 1.96)]
order = sig_any.sort_values("s").index
fig, axes = plt.subplots(1, 2, figsize=(9.5, 6.4), sharey=True)
for ax, (col, tcol, title, c_dark) in zip(axes, [("s", "t_SMB", "Размер (s)", "#2C5A87"),
                                                 ("h", "t_HML", "Стоимость (h)", "#A9521A")]):
    vals = sig_any.loc[order, col]
    sig = sig_any.loc[order, tcol].abs() > 1.96
    ax.barh(order, vals, color=np.where(sig, c_dark, "#D8D3C8"))
    ax.axvline(0, color="black", lw=1)
    ax.set_title(title, fontsize=20)
    ax.tick_params(labelsize=16)
    ax.grid(axis="x", alpha=0.3)
fig.text(0.5, 0.005, "цветные — значимы на 5%, серые — незначимы", ha="center", fontsize=15, color="#44505F")
plt.tight_layout(rect=(0, 0.04, 1, 1)); plt.savefig(FIG / "04s_ff3_loadings_slide.png", dpi=150); plt.show()

# %% [markdown]
# **Интерпретация трёхфакторной модели.** Нагрузки экономически осмысленны:
# * **Размер (s > 0, ведут себя как малые компании):** BSPB, SELG, HEAD, HYDR, VTBR, MOEX, UPRO, X5, FEES, RENI.
#   **s < 0 (как крупные):** GAZP, ALRS, T — бумаги с большой капитализацией.
# * **Стоимость (h > 0, «акции стоимости»):** банки (BSPB, VTBR, SBER), энергетика (MSNG, IRAO), BANEP, GAZP —
#   низкий P/B, зрелый бизнес, высокая зависимость от государства и ставок.
#   **h < 0 («акции роста»):** HEAD, OZON, RENI, GMKN, ALRS — компании, за перспективы которых рынок платит премию к балансу.
# * Рыночная бета почти не меняется по сравнению с CAPM (средняя ~1,0): SMB и HML слабо коррелируют с рынком.

# %% [markdown]
# ## 6. Сравнение моделей

# %%
def grs_test(EXR: pd.DataFrame, X: pd.DataFrame) -> dict:
    """GRS-тест (Gibbons, Ross, Shanken, 1989) на сбалансированной панели.

    GRS = (T/N)·((T−N−L)/(T−L−1))·α'Σ⁻¹α / (1 + μ'Ω⁻¹μ) ~ F(N, T−N−L)
    Σ — ковариация остатков, Ω — ковариация факторов, μ — средние факторов.
    """
    d = pd.concat([EXR, X], axis=1).dropna()       # только месяцы, где есть все акции
    Y, Xf = d[EXR.columns].values, d[X.columns].values
    T, N, L = len(d), Y.shape[1], Xf.shape[1]
    Z = np.column_stack([np.ones(T), Xf])
    B = np.linalg.lstsq(Z, Y, rcond=None)[0]
    alpha, E = B[0], Y - Z @ B
    Sigma = E.T @ E / (T - L - 1)
    mu, Omega = Xf.mean(0), np.cov(Xf, rowvar=False).reshape(L, L)
    grs = (T / N) * ((T - N - L) / (T - L - 1)) * (alpha @ np.linalg.solve(Sigma, alpha)) \
        / (1 + mu @ np.linalg.solve(Omega, mu))
    return {"T": T, "N": N, "GRS": grs, "p-value": 1 - stats.f.cdf(grs, N, T - N - L)}

# GRS требует одинакового периода для всех акций: берём бумаги с полной историей
full = [t for t in TICKERS if EXR[t].count() == len(F)]

compare = pd.DataFrame({
    "CAPM": {
        "Средний R²": capm["R2"].mean(),
        "Средний скорр. R²": capm["R2_adj"].mean(),
        "Средняя |α|, % год.": capm["alpha_%год"].abs().mean(),
        "Значимых α (5%)": int((capm["t_alpha"].abs() > 1.96).sum()),
        **{f"GRS {k}": v for k, v in grs_test(EXR[full], F[["MKT"]]).items()},
    },
    "Фама–Френч": {
        "Средний R²": ff3["R2"].mean(),
        "Средний скорр. R²": ff3["R2_adj"].mean(),
        "Средняя |α|, % год.": ff3["alpha_%год"].abs().mean(),
        "Значимых α (5%)": int((ff3["t_alpha"].abs() > 1.96).sum()),
        **{f"GRS {k}": v for k, v in grs_test(EXR[full], F[["MKT", "SMB", "HML"]]).items()},
    },
})
print(f"Акций в регрессиях: {len(ff3)}; в GRS-тесте (полная история): {len(full)}")
compare

# %% [markdown]
# **Сравнение.**
# * Трёхфакторная модель объясняет доходности лучше: средний скорректированный R² растёт с 0,37 до 0,41,
#   средняя |α| падает с 9,8 до 8,1 п.п. годовых. Сильнее всего выигрывают малые компании и акции стоимости/роста:
#   BSPB (R² 0,32 → 0,50), HEAD (0,39 → 0,55), UPRO, HYDR, OZON.
# * **Пример из лекции, слайд 70, на российских данных:** «альфа» BSPB по CAPM +27% годовых (t = 2,6) в трёхфакторной
#   модели снижается до +18% и становится незначимой (t = 1,9) — треть её объясняется тем, что BSPB — малая акция стоимости.
#   То же у HEAD: +36% (t = 2,1) → +10% (t = 0,6).
# * **VTBR** — устойчиво отрицательная альфа (−24%, t = −4,0) в обеих моделях. Факторы её не объясняют: акционеры
#   ВТБ проиграли из-за размывания доли при допэмиссиях 2022–2025 гг. — это специфический, а не систематический риск.
# * **GRS-тест** отвергает обе модели на 5% (p = 0,015 для CAPM, 0,037 для ФФ): совместно альфы не равны нулю.
#   Трёхфакторная модель ближе к цели, но не идеальна — как и на американских данных, нужны дополнительные факторы.

# %%
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
ax = axes[0]
ax.scatter(capm["R2"], ff3["R2"])
for t in ff3.index:
    ax.annotate(t, (capm.loc[t, "R2"], ff3.loc[t, "R2"]), fontsize=7)
ax.plot([0, 1], [0, 1], color="grey", ls="--")
ax.set_xlabel("R² CAPM"); ax.set_ylabel("R² Фама–Френч"); ax.set_title("Объяснительная сила")
ax = axes[1]
ax.scatter(capm["alpha_%год"], ff3["alpha_%год"])
for t in ff3.index:
    ax.annotate(t, (capm.loc[t, "alpha_%год"], ff3.loc[t, "alpha_%год"]), fontsize=7)
lim = [min(capm["alpha_%год"].min(), ff3["alpha_%год"].min()) - 2,
       max(capm["alpha_%год"].max(), ff3["alpha_%год"].max()) + 2]
ax.plot(lim, lim, color="grey", ls="--")
ax.set_xlabel("α CAPM, % год."); ax.set_ylabel("α Фама–Френч, % год."); ax.set_title("Альфы")
plt.tight_layout(); plt.savefig(FIG / "05_capm_vs_ff3.png", dpi=150); plt.show()

# %% [markdown]
# ### 6.1. Процедура Фамы–Макбета: сколько рынок платит за единицу риска
#
# Этап 1 — беты из временных регрессий выше. Этап 2 — каждый месяц поперечная регрессия
# избыточных доходностей акций на их беты; $\lambda_k$ — среднее по месяцам, t-статистика по ряду $\lambda_{k,t}$.
# Если модель верна, константа $\lambda_0 \approx 0$, а $\lambda_k$ близки к средним доходностям факторов.
# 35 отдельных акций — маленькая и шумная выборка (беты оценены с ошибкой), поэтому результат иллюстративный.

# %%
def fama_macbeth(EXR: pd.DataFrame, betas: pd.DataFrame) -> pd.DataFrame:
    lams = []
    for t, row in EXR.iterrows():
        d = pd.concat([row.rename("y"), betas], axis=1).dropna()
        if len(d) < 10:
            continue
        lams.append(sm.OLS(d["y"], sm.add_constant(d[betas.columns])).fit().params.rename(t))
    lam = pd.DataFrame(lams)
    return pd.DataFrame({"λ, % мес.": lam.mean() * 100,
                         "λ, % год.": lam.mean() * 1200,
                         "t-стат.": lam.mean() / lam.std() * np.sqrt(len(lam))})

fm_capm = fama_macbeth(EXR, capm[["MKT"]].astype(float))
fm_ff3 = fama_macbeth(EXR, ff3[["MKT", "SMB", "HML"]].astype(float))
fm = pd.concat({"CAPM": fm_capm, "Фама–Френч": fm_ff3})
fm["Ср. доходность фактора, % год."] = [np.nan, F["MKT"].mean() * 1200,
                                        np.nan, *(F.mean() * 1200)]
fm

# %% [markdown]
# Константы близки к нулю, знаки премий совпадают со средними доходностями факторов (рынок и размер — плюс,
# стоимость — минус), но все $\lambda$ статистически незначимы: на 35 акциях и 10 годах высоковолатильного рынка
# цену риска точно оценить нельзя. Поэтому для расчёта премий ниже используем средние доходности факторов
# (стандартный подход для торгуемых факторов), а оценки Фамы–Макбета — как проверку знаков.

# %% [markdown]
# ## 7. Премии за риск и требуемая доходность: CAPM против Фамы–Френча
#
# Премия за риск акции = сумма (бета × премия фактора). Премии факторов — их средние доходности за 02.2015–12.2024.
# Требуемая (ожидаемая) доходность считается **на дату анализа**: безрисковая ставка — доходность 1-летних ОФЗ
# с G-кривой ЦБ на конец последнего месяца данных (инвестор принимает решение сегодня, а не по средней ставке за 10 лет).

# %%
lam = F.mean() * 12                                        # годовые премии факторов
RF_NOW = mkt["ofz1y_annual"].dropna().iloc[-1]
RF_DATE = mkt["ofz1y_annual"].dropna().index[-1]
print(f"Безрисковая ставка на {RF_DATE}: {RF_NOW:.2%} (1-летние ОФЗ)")
print("Премии факторов, % год.:", (lam * 100).round(2).to_dict())

prem = pd.DataFrame({
    "Отрасль": pd.Series(SECTORS),
    "Премия CAPM": capm["MKT"] * lam["MKT"],
    "Премия ФФ: рынок": ff3["MKT"] * lam["MKT"],
    "Премия ФФ: размер": ff3["SMB"] * lam["SMB"],
    "Премия ФФ: стоимость": ff3["HML"] * lam["HML"],
}).dropna(subset=["Премия CAPM"])
prem["Премия ФФ"] = prem[["Премия ФФ: рынок", "Премия ФФ: размер", "Премия ФФ: стоимость"]].sum(axis=1)
prem["Разница ФФ − CAPM"] = prem["Премия ФФ"] - prem["Премия CAPM"]
prem["Факт. избыт. доходность"] = EXR.mean() * 12
prem["Треб. доходность CAPM"] = RF_NOW + prem["Премия CAPM"]
prem["Треб. доходность ФФ"] = RF_NOW + prem["Премия ФФ"]
num = prem.columns.drop("Отрасль")
prem[num] = prem[num].astype(float) * 100            # в % годовых
prem.sort_values("Разница ФФ − CAPM", ascending=False)

# %%
p = prem.sort_values("Премия ФФ")
fig, ax = plt.subplots(figsize=(10, 9))
y = np.arange(len(p))
ax.barh(y - 0.2, p["Премия CAPM"], height=0.4, label="CAPM")
ax.barh(y + 0.2, p["Премия ФФ"], height=0.4, label="Фама–Френч")
ax.scatter(p["Факт. избыт. доходность"], y, color="black", marker="|", s=80, label="Фактическая избыточная доходность")
ax.set_yticks(y); ax.set_yticklabels(p.index)
ax.axvline(0, color="black", lw=0.8)
ax.set_xlabel("% годовых"); ax.set_title("Премии за риск по двум моделям, 02.2015–12.2024")
ax.legend(loc="lower right")
plt.tight_layout(); plt.savefig(FIG / "06_premia.png", dpi=150); plt.show()

# %%
# Версия для слайда: 6 малых бумаг и 6 голубых фишек, крупный шрифт
KEY = ["HEAD", "SELG", "BSPB", "OZON", "RENI", "X5", "LKOH", "NVTK", "SBER", "TATN", "ROSN", "GAZP"]
p = prem.loc[KEY[::-1]]
fig, ax = plt.subplots(figsize=(8.6, 7.0))
y = np.arange(len(p))
ax.barh(y + 0.2, p["Премия CAPM"], height=0.4, color="#2C5A87", label="CAPM")
ax.barh(y - 0.2, p["Премия ФФ"], height=0.4, color="#E08A3C", label="Фама–Френч")
ax.scatter(p["Факт. избыт. доходность"], y, color="black", marker="|", s=400, linewidths=3,
           label="Факт. избыт. доходность")
ax.axhline(5.5, color="#6B7684", ls="--", lw=1)
ax.text(36, 11.4, "малые", ha="right", va="top", fontsize=16, color="#6B7684")
ax.text(36, 5.3, "крупные", ha="right", va="top", fontsize=16, color="#6B7684")
ax.set_yticks(y); ax.set_yticklabels(p.index)
ax.axvline(0, color="black", lw=1)
ax.tick_params(labelsize=16)
ax.set_xlabel("% годовых", fontsize=16)
ax.grid(axis="x", alpha=0.3)
ax.legend(loc="lower right", fontsize=13)
plt.tight_layout(); plt.savefig(FIG / "06s_premia_slide.png", dpi=150); plt.show()

# %% [markdown]
# **Сравнение премий за риск.**
# * Для **крупных компаний** трёхфакторная премия равна или ниже CAPM: от +0,3 п.п. у LKOH до −2–3 п.п. у SBER, ROSN, TATN
#   и −4,4 п.п. у GAZP. Причина — отрицательная нагрузка на SMB (это крупные бумаги, а малые в 2015–2024 гг. обгоняли)
#   и, у «стоимостных» GAZP и SBER, отрицательная историческая премия HML. CAPM для них слегка завышает премию.
# * Для **малых компаний** трёхфакторная модель даёт заметно более высокую премию: HEAD +16 п.п., SELG +12 п.п.,
#   BSPB +9 п.п., OZON +7 п.п. CAPM занижает для них требуемую доходность (стоимость капитала).
# * У BSPB, SELG, HEAD, X5 и MOEX фактическая доходность ближе к оценке ФФ, чем к CAPM: модель «доначисляет»
#   премию за размер, которую CAPM записывает в альфу. У части малых бумаг (UPRO, HYDR, RENI) фактическая доходность
#   ниже обеих оценок — их отставание факторы не объясняют.
# * **Оговорка:** премия SMB (~18% годовых) сильно зависит от одного 2023 г. Использовать её как прогноз на будущее
#   рискованно — для оценки стоимости капитала разумно брать более консервативную премию за размер.

# %% [markdown]
# ### 7.1. Как меняются выводы при расширении выборки: 15 бумаг ДЗ1 → 35
#
# Сначала оцениваем обе модели только на 15 акциях из ДЗ1, затем — на всей выборке из 35 бумаг
# и смотрим, какие выводы сохраняются, а какие появляются только на широкой выборке.
# Факторы, период и методика те же; GRS — на бумагах с полной историей внутри каждой выборки.

# %%
def sample_summary(cols: list) -> dict:
    """Сводка CAPM и Фамы–Френча на подвыборке акций."""
    c, f = capm.loc[cols], ff3.loc[cols]
    fl = [t for t in full if t in cols]
    g_c, g_f = grs_test(EXR[fl], F[["MKT"]]), grs_test(EXR[fl], F[["MKT", "SMB", "HML"]])
    fm_f = fama_macbeth(EXR[cols], f[["MKT", "SMB", "HML"]].astype(float))
    return {
        "Акций": len(cols),
        "Диапазон β CAPM": f"{c['MKT'].min():.2f}–{c['MKT'].max():.2f}",
        "Средний R² CAPM": c["R2"].mean(),
        "Средний R² ФФ": f["R2"].mean(),
        "Средний скорр. R² CAPM": c["R2_adj"].mean(),
        "Средний скорр. R² ФФ": f["R2_adj"].mean(),
        "Средняя |α| CAPM, % год.": c["alpha_%год"].abs().mean(),
        "Средняя |α| ФФ, % год.": f["alpha_%год"].abs().mean(),
        "Значимых α CAPM": int((c["t_alpha"].abs() > 1.96).sum()),
        "Значимых α ФФ": int((f["t_alpha"].abs() > 1.96).sum()),
        "Значимых нагрузок SMB (+/−)": f"{(f['t_SMB'] > 1.96).sum()} / {(f['t_SMB'] < -1.96).sum()}",
        "Значимых нагрузок HML (+/−)": f"{(f['t_HML'] > 1.96).sum()} / {(f['t_HML'] < -1.96).sum()}",
        "GRS: акций с полной историей": len(fl),
        "GRS p-value CAPM": g_c["p-value"],
        "GRS p-value ФФ": g_f["p-value"],
        "Фама–Макбет λ SMB, % год. (t)": f"{fm_f.loc['SMB', 'λ, % год.']:.1f} ({fm_f.loc['SMB', 't-стат.']:.2f})",
        "Фама–Макбет λ HML, % год. (t)": f"{fm_f.loc['HML', 'λ, % год.']:.1f} ({fm_f.loc['HML', 't-стат.']:.2f})",
        "Премия ФФ выше CAPM, акций": f"{(prem.loc[cols, 'Разница ФФ − CAPM'] > 0).sum()} из {len(cols)}",
    }

NEW20 = [t for t in ff3.index if t not in HW1]
hw1_vs_all = pd.DataFrame({"15 бумаг ДЗ1": sample_summary(HW1),
                           "20 новых бумаг": sample_summary(NEW20),
                           "Все 35": sample_summary(list(ff3.index))})
hw1_vs_all

# %%
# Чем отличается состав выборок: отрасли
pd.DataFrame({"ДЗ1": pd.Series(SECTORS)[HW1].value_counts(),
              "Все 35": pd.Series(SECTORS).value_counts()}).fillna(0).astype(int)

# %% [markdown]
# **Что меняется при расширении выборки.**
# * **Главный вывод сохраняется:** в обеих выборках трёхфакторная модель лучше CAPM — R² растёт на 0,04–0,05,
#   средняя |α| падает примерно на 1,5–1,7 п.п. годовых.
# * **GRS-тест меняет вывод.** На 15 бумагах ДЗ1 CAPM отвергается (p = 0,035), а Фама–Френч — нет (p = 0,096):
#   можно было бы решить, что трёх факторов достаточно. На 35 бумагах отвергаются обе модели (p = 0,015 и 0,037).
#   Широкая выборка — более мощный тест: в неё вошли VTBR и HEAD с крупными альфами, которые факторы не объясняют.
# * **Премии за риск: картина становится двусторонней.** ДЗ1 — в основном второй эшелон, поэтому премия ФФ выше
#   CAPM у 10 бумаг из 15. Только с голубыми фишками (SBER, GAZP, TATN, NVTK) видно, что для крупных компаний
#   ФФ даёт премию ниже CAPM. Рекомендация «для крупных бумаг хватает CAPM» опирается на расширенную выборку.
# * **Фактор стоимости проявляется только на 35 бумагах.** В ДЗ1 нет «акций роста» из IT и e-commerce, поэтому
#   значимых нагрузок на HML 5, а на 35 бумагах — 12 (HEAD и OZON дают отрицательный полюс). Диапазон β
#   расширяется с 0,55–1,45 до 0,55–1,66.
# * На 15 бумагах Фама–Макбет даёт премию за размер почти значимой (t ≈ 1,8), на 35 — незначимой: оценка цены риска
#   на малой выборке неустойчива.

# %%
# График: R² и средняя |α| в двух выборках
fig, axes = plt.subplots(1, 2, figsize=(11, 5.2))
labels, xs = ["15 бумаг ДЗ1", "Все 35"], np.arange(2)
for ax, (rc, rf, title) in zip(axes, [("Средний R² CAPM", "Средний R² ФФ", "Средний R²"),
                                      ("Средняя |α| CAPM, % год.", "Средняя |α| ФФ, % год.",
                                       "Средняя |α|, % годовых")]):
    vc = hw1_vs_all.loc[rc, labels].astype(float).values
    vf = hw1_vs_all.loc[rf, labels].astype(float).values
    ax.bar(xs - 0.2, vc, width=0.4, color="#2C5A87", label="CAPM")
    ax.bar(xs + 0.2, vf, width=0.4, color="#E08A3C", label="Фама–Френч")
    for x, v in zip(np.r_[xs - 0.2, xs + 0.2], np.r_[vc, vf]):
        ax.text(x, v, f"{v:.2f}".replace(".", ","), ha="center", va="bottom", fontsize=15)
    ax.set_xticks(xs); ax.set_xticklabels(labels, fontsize=16)
    ax.set_title(title, fontsize=18); ax.tick_params(axis="y", labelsize=14)
    ax.set_ylim(0, max(vc.max(), vf.max()) * 1.2)
axes[0].legend(fontsize=14, loc="lower right")
plt.tight_layout(); plt.savefig(FIG / "07_hw1_vs_all.png", dpi=150); plt.show()

# %% [markdown]
# ## 8. Проверка устойчивости
#
# Повторяем обе модели при других допущениях и смотрим, меняются ли выводы:
# 1. **Без дивидендов:** ценовые доходности акций, IMOEX, факторы РАНХиГС без дивидендов.
# 2. **Безрисковая ставка — ОФЗ 3М** вместо RUONIA.
# 3. **Рыночный фактор РАНХиГС** (широкий рынок с ограничением веса 15%, безрисковая — RGBI).
# 4. **Полный период CAPM 02.2015–09.2026** (для CAPM факторы РАНХиГС не нужны).

# %%
def model_summary(EXR, X) -> dict:
    t = run_model(EXR, X)
    return {"Средняя бета рынка": t[X.columns[0]].mean(), "Средний R²": t["R2"].mean(),
            "Средняя |α|, % год.": t["alpha_%год"].abs().mean(),
            "Значимых α": int((t["t_alpha"].abs() > 1.96).sum())}

rf_ofz = mkt["rf_ofz3m"]
specs = {
    "Основная": (EXR, F),
    "Без дивидендов": (
        ret_price.sub(mkt["rf_ruonia"], axis=0).loc[START:END],
        pd.DataFrame({"MKT": mkt["imoex_ret"] - mkt["rf_ruonia"],
                      "SMB": ranepa["SMB"], "HML": ranepa["HML"]}).loc[START:END]),
    "rf = ОФЗ 3М": (
        ret_total.sub(rf_ofz, axis=0).loc[START:END],
        F.assign(MKT=(mkt["mcftr_ret"] - rf_ofz).loc[START:END])),
    "Рынок РАНХиГС": (EXR, F.assign(MKT=ranepa["RM_TR"].loc[START:END])),
}
rob = {}
for name, (y, X) in specs.items():
    rob[(name, "CAPM")] = model_summary(y, X[["MKT"]])
    rob[(name, "ФФ")] = model_summary(y, X[["MKT", "SMB", "HML"]])
EXR_full = ret_total.sub(mkt["rf_ruonia"], axis=0).loc[START:"2026-09"]
MKT_full = (mkt["mcftr_ret"] - mkt["rf_ruonia"]).loc[START:"2026-09"].to_frame("MKT")
rob[("CAPM до 09.2026", "CAPM")] = model_summary(EXR_full, MKT_full)
robust = pd.DataFrame(rob).T
robust

# %% [markdown]
# **Выводы устойчивы:**
# * Замена RUONIA на ОФЗ 3М почти ничего не меняет (беты и R² те же, альфы сдвигаются на ~0,1 п.п.) —
#   выбор безрисковой ставки не влияет на выводы, важно лишь, чтобы она менялась во времени.
# * Без дивидендов альфы по модулю выше (≈11 п.п. против 10) и значимых больше: игнорирование дивидендов
#   искажает результат — подтверждает выбор полных доходностей.
# * С рыночным фактором РАНХиГС R² заметно ниже (0,29 против 0,38) и больше значимых альф: их широкий рынок
#   с ограничением веса 15% и «безрисковой» RGBI хуже описывает наши крупные бумаги, чем MCFTR − RUONIA.
# * На полном периоде до 09.2026 CAPM даёт те же беты и R².

# %% [markdown]
# ## 9. Какие ещё факторы можно добавить
#
# РАНХиГС публикует ещё факторы моментума (MOM, Carhart, 1997) и ликвидности (LIQ, близкий по смыслу к Pástor, Stambaugh, 2003).
# Проверим, улучшают ли они объяснение доходностей поверх трёх факторов.

# %%
F5 = F.assign(MOM=ranepa["MOM_TR"], LIQ=ranepa["LIQ_TR"]).loc[START:END]
ext = {
    "CAPM": run_model(EXR, F5[["MKT"]]),
    "Фама–Френч (3)": ff3,
    "Кархарт (4: + MOM)": run_model(EXR, F5[["MKT", "SMB", "HML", "MOM"]]),
    "5 факторов (+ MOM, LIQ)": run_model(EXR, F5[["MKT", "SMB", "HML", "MOM", "LIQ"]]),
}
ext_tab = pd.DataFrame({k: {"Средний R²": v["R2"].mean(), "Средний скорр. R²": v["R2_adj"].mean(),
                            "Средняя |α|, % год.": v["alpha_%год"].abs().mean(),
                            "Значимых α": int((v["t_alpha"].abs() > 1.96).sum())}
                        for k, v in ext.items()}).T
for f in ["MOM", "LIQ"]:
    t = ext["5 факторов (+ MOM, LIQ)"][f"t_{f}"]
    ext_tab.loc["5 факторов (+ MOM, LIQ)", f"Значимых нагрузок {f}"] = int((t.abs() > 1.96).sum())
ext_tab

# %% [markdown]
# Моментум и ликвидность добавляют немного: скорректированный R² 0,406 → 0,413, средняя |α| почти не меняется,
# значимые нагрузки на MOM — у 4 акций, на LIQ — у 2. Основная часть систематического риска уже покрыта рынком,
# размером и стоимостью.
#
# ### Какие ещё факторы и модели можно рассмотреть (обзор литературы)
#
# | Модель / фактор | Идея | Чем может помочь на российском рынке |
# |---|---|---|
# | Carhart (1997), моментум MOM | «Победители» последних 12 мес. продолжают расти | Объясняет инерцию трендов, которую не ловит ФФ3 |
# | Fama, French (2015), RMW и CMA | Прибыльность и инвестиции компаний | Разделяет «дешёвые» качественные компании и компании в дистрессе |
# | Hou, Xue, Zhang (2015), q-модель | Инвестиции и рентабельность из теории производства | Альтернатива ФФ5 с экономическим обоснованием |
# | Pástor, Stambaugh (2003), Amihud (2002), ликвидность | Премия за неликвидность | Важна для второго эшелона (RENI, MSNG, UPRO) |
# | Chen, Roll, Ross (1986), макрофакторы | Промпроизводство, инфляция, спреды | Для России — **цена нефти и курс рубля** (вся нефтегазовая выборка) |
# | Фактор госсобственности SOE (РАНХиГС) | Акции госкомпаний несут политический риск | У VTBR, GAZP, HYDR, ALRS — объяснение части отрицательных альф |
# | Условные CAPM (Jagannathan, Wang, 1996), DCC-беты | Беты меняются во времени | Беты до и после 2022 г. заметно различаются |
#
# ## 10. Рекомендации
#
# 1. **Для крупных ликвидных бумаг** (SBER, LKOH, ROSN, TATN, NVTK, GAZP, MTSS) CAPM даёт близкую или немного завышенную
#    (на 0–4 п.п.) оценку требуемой доходности — для них простой модели достаточно. Для **малых компаний и бумаг
#    роста/стоимости** (BSPB, SELG, HEAD, OZON, X5, HYDR, UPRO) следует использовать трёхфакторную модель — CAPM занижает
#    их стоимость капитала на 4–16 п.п.
# 2. **«Альфа» по CAPM часто ложная.** Высокая доходность BSPB и HEAD в большой мере — плата за размер и стоимость;
#    оценивать управляющих и инвестидеи нужно по альфе многофакторной модели.
# 3. **Значимая положительная альфа в модели ФФ — только у SBER** (+13% годовых, t = 1,99, на границе значимости):
#    Сбербанк зарабатывал больше, чем требует его риск, — кандидат на перевес в портфеле, но с осторожностью.
#    Значимо отрицательная альфа у VTBR и UPRO: исторически акционеры недополучали доход относительно принятого риска
#    (допэмиссии, корпоративные события) — при прочих равных такие бумаги стоит недовешивать.
# 4. **Для защитного портфеля** — акции с низкой рыночной бетой (CBOM, SNGSP, TRNFP, IRAO, RTKM, PLZL);
#    для ставки на рост рынка — высокобетовые (HEAD, OZON, T, ROSN, SBER).
# 5. Требуемую доходность считать от **текущей** безрисковой ставки (1-летние ОФЗ 13,7% на 09.2026), а премию за размер
#    брать консервативнее исторической — её оценка неустойчива.
#
# ## 11. Заключение
#
# * На 35 российских акциях в 2015–2024 гг. рыночный фактор объясняет ~38% колебаний доходности; добавление факторов
#   размера и стоимости повышает R² до ~42% и снижает средние ошибки ценообразования на 1,7 п.п. в год.
# * Нагрузки на SMB и HML экономически осмысленны и значимы у трети выборки; премия за размер в России была высокой (2023 г.),
#   премия за стоимость — отрицательной.
# * Обе модели формально отвергаются GRS-тестом, но трёхфакторная — заметно ближе к цели. Выводы устойчивы к выбору
#   безрисковой ставки, учёту дивидендов и периоду; моментум и ликвидность дают лишь небольшое улучшение.

# %% [markdown]
# ## 12. Выгрузка результатов в Excel (для презентации)

# %%
with pd.ExcelWriter(RES / "hw2_results.xlsx") as xw:
    desc.to_excel(xw, sheet_name="Описательная статистика")
    fac_stats.to_excel(xw, sheet_name="Факторы")
    capm_view.to_excel(xw, sheet_name="CAPM")
    ff3_view.to_excel(xw, sheet_name="Фама-Френч")
    compare.to_excel(xw, sheet_name="Сравнение моделей")
    fm.to_excel(xw, sheet_name="Фама-Макбет")
    prem.to_excel(xw, sheet_name="Премии за риск")
    hw1_vs_all.to_excel(xw, sheet_name="ДЗ1 (15) vs 35")
    robust.to_excel(xw, sheet_name="Устойчивость")
    ext_tab.to_excel(xw, sheet_name="Доп. факторы")
    summary_rf.to_excel(xw, sheet_name="Безрисковая ставка")
print("Сохранено:", RES / "hw2_results.xlsx")
