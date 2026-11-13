const pptxgen = require('pptxgenjs');
const fs = require('fs');
const { applyTheme } = require('/root/.claude/skills/synced/d31f7550-65ba-4021-ac6a-4b7f2c693e33_fa3cedb5-d4e6-454a-ade6-9bd28b5cc8dd/pptx/scripts/apply_theme.js');
const V = JSON.parse(fs.readFileSync(__dirname + '/vals.json', 'utf8'));
const OUT = process.argv[2];

const THEME = {
  name: 'DIOD Health', headFontFace: 'Cambria', bodyFontFace: 'Calibri',
  colors: { dk1: '1F2A24', lt1: 'FFFFFF', dk2: '2C5F2D', lt2: 'EEF4EA', accent1: '2C5F2D', accent2: '97BC62', accent3: 'C0504D',
    accent4: 'E0A526', accent5: '5B7F95', accent6: '8C8C8C', hlink: '2C5F2D', folHlink: '5B7F95' },
};
const HEX = { forest: '2C5F2D', moss: '97BC62', red: 'C0504D', amber: 'E0A526', slate: '5B7F95', grey: '8C8C8C', tint: 'EEF4EA', text: '1F2A24', grid: 'D9D9D9' };

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = 'ПАО «ДИОД»: стоимость капитала';
const C = pres.SchemeColor;

const n = (x, d = 2) => (x < 0 ? '−' : '') + Math.abs(x).toFixed(d).replace('.', ',');
const pct = (x, d = 2) => n(x * 100, d) + '%';
const th = (x) => (x < 0 ? '−' : '') + Math.abs(Math.round(x)).toLocaleString('ru-RU').replace(/ /g, ' ');

pres.defineSlideMaster({
  title: 'CONTENT',
  background: { color: 'FFFFFF' },
  objects: [
    { placeholder: { options: { name: 'title', type: 'title', x: 0.5, y: 0.3, w: 12.3, h: 0.8, fontFace: 'Cambria', fontSize: 30, bold: true, color: C.text2, valign: 'middle', margin: 0 }, text: '' } },
    { text: { text: 'ПАО «ДИОД» · Этап 3 · Стоимость капитала на 31.12.2025', options: { x: 0.5, y: 7.05, w: 8, h: 0.3, fontSize: 10, color: C.accent6, fontFace: 'Calibri' } } },
  ],
  slideNumber: { x: 12.3, y: 7.05, w: 0.5, h: 0.3, fontSize: 10, color: '8C8C8C', fontFace: 'Calibri', align: 'right' },
});

function src(slide, text) {
  slide.addText(text, { x: 0.5, y: 6.62, w: 12.3, h: 0.4, fontSize: 10, color: C.accent6, italic: true, isTextBox: true, valign: 'top', margin: 0, objectName: 'Источники' });
}
function card(slide, x, y, w, h, opts = {}) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: opts.fill || C.background2 }, line: { color: opts.fill || C.background2 }, objectName: opts.name || 'Карточка' });
}
function stat(slide, x, y, w, big, label, color) {
  slide.addText(big, { x, y, w, h: 0.6, fontSize: 30, bold: true, color: color || C.accent1, fontFace: 'Cambria', isTextBox: true, margin: 0 });
  slide.addText(label, { x, y: y + 0.6, w, h: 0.5, fontSize: 12, color: C.text1, isTextBox: true, margin: 0, valign: 'top' });
}
const chartFont = { catAxisLabelFontFace: '+mn-lt', valAxisLabelFontFace: '+mn-lt', dataLabelFontFace: '+mn-lt', titleFontFace: '+mn-lt', legendFontFace: '+mn-lt' };
const chartBase = () => ({ ...chartFont, catAxisLabelColor: '595959', valAxisLabelColor: '595959', catAxisLabelFontSize: 11, valAxisLabelFontSize: 10, dataLabelFontSize: 11,
  valGridLine: { color: HEX.grid, size: 0.5 }, catGridLine: { style: 'none' }, showTitle: true, titleFontSize: 13, titleColor: HEX.text });

const sm = V.analogs;
const ebitM = V.ebit.map((x) => x / 1000), revM = V.rev.map((x) => x / 1000);

// ---------------- Slide 1: business, stage, method ----------------
pres.addSection({ title: 'ДИОД: стоимость капитала' });
let s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'ДИОД: стоимость капитала' });
s.addText('ДИОД: стадия спада и выбор методики', { placeholder: 'title' });
s.addChart(pres.charts.BAR, [
  { name: 'Выручка', labels: ['2021', '2022', '2023', '2024', '2025'], values: revM },
  { name: 'EBIT', labels: ['2021', '2022', '2023', '2024', '2025'], values: ebitM },
], { x: 0.5, y: 1.25, w: 6.4, h: 3.6, barDir: 'col', barGapWidthPct: 60, chartColors: [HEX.moss, HEX.forest], ...chartBase(),
  title: 'Выручка и EBIT по МСФО, млн руб.', showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '#,##0', valAxisLabelFormatCode: '#,##0',
  showLegend: true, legendPos: 'b', legendFontSize: 11, objectName: 'График выручки и EBIT' });
card(s, 0.5, 5.0, 6.4, 1.5);
s.addText([
  { text: 'Бизнес: ', options: { bold: true } }, { text: 'БАД (79–83% выручки), лечебная косметика, водородные напитки, фармацевтика. ', options: {} },
  { text: 'Спад: ', options: { bold: true } }, { text: `выручка ${th(revM[0])} → ${th(revM[4])} млн руб., EBIT +${th(ebitM[0])} → ${th(ebitM[4])} млн, капитал ${th(V.eq[0] / 1000)} → ${th(V.eq[4] / 1000)} млн руб.`, options: {} },
], { x: 0.7, y: 5.1, w: 6.0, h: 1.3, fontSize: 14, color: C.text1, isTextBox: true, valign: 'middle', margin: 0 });
// right: method
const meth = [
  ['Ke', 'CAPM: Ke = Rf + βlev × ERP', `Rf 13,91% (ОФЗ 20 лет), ERP 5,24%, CRP 0%. Бета — по 10 аналогам развитых рынков (ДРТ, сл. 21–27), а не по акции ДИОД: оборот ~23 млн руб./мес., R² собственной беты ${n(V.own_r2, 2)}`],
  ['Kd', 'Синтетический рейтинг', `ICR = EBIT / проценты, шкала малых компаний (лекция, сл. 38–39): капитализация ${n(V.mcap_usd, 1)} млн USD ≪ 5 млрд USD`],
  ['WACC', 'Два набора весов', 'Балансовые (МСФО) и рыночные (10,26 руб. × 90,5 млн акций в обращении); налоговый щит проверен отдельно'],
];
meth.forEach((m, i) => {
  const y = 1.25 + i * 1.75;
  card(s, 7.3, y, 5.5, 1.55);
  s.addShape(pres.shapes.OVAL, { x: 7.5, y: y + 0.4, w: 0.8, h: 0.8, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: 'Значок ' + m[0] });
  s.addText(m[0], { x: 7.5, y: y + 0.4, w: 0.8, h: 0.8, fontSize: m[0].length > 2 ? 12 : 16, bold: true, color: C.background1, align: 'center', valign: 'middle', isTextBox: true, margin: 0 });
  s.addText(m[1], { x: 8.5, y: y + 0.12, w: 4.15, h: 0.4, fontSize: 15, bold: true, color: C.text2, isTextBox: true, margin: 0 });
  s.addText(m[2], { x: 8.5, y: y + 0.52, w: 4.15, h: 0.95, fontSize: 12, color: C.text1, isTextBox: true, margin: 0, valign: 'top' });
});
src(s, 'Источники: МСФО группы «ДИОД» 2021–2025 (Excel этапа 2); Мосбиржа ISS; АО ДРТ «Анализ расчёта WACC для российского рынка», 2026; лекция «Затраты на капитал», сл. 38–39.');
s.addNotes(`ДИОД — небольшой производитель БАД, 80% выручки — добавки. По жизненному циклу компания в спаде: выручка за пять лет упала с 602 до 521 млн рублей, операционная прибыль с плюс 107 ушла в минус, в 2024 году был крупный убыток из-за списаний. Капитал по МСФО почти вдвое сократился — с 1,23 до 0,66 млрд. Поэтому методика такая: Ke по CAPM с бетой по зарубежным аналогам, потому что акция ДИОД малоликвидна и её собственная бета ненадёжна; Kd — синтетическим рейтингом по шкале малых компаний; WACC считаем по балансовым и рыночным весам.`);

// ---------------- Slide 2: analogs & unlevered beta ----------------
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'ДИОД: стоимость капитала' });
s.addText('Аналоги ДИОД: медианная безрычаговая бета 0,61', { placeholder: 'title' });
const hdr = ['Компания', 'Страна', 'βraw', 'βadj', 'D/E', 'T', 'βu'].map((t) => ({ text: t, options: { bold: true, color: 'FFFFFF', fill: { color: HEX.forest }, align: 'center' } }));
const rowsT = [hdr];
sm.forEach((a) => {
  const ex = a.inc !== 'Да';
  const o = { color: ex ? HEX.grey : HEX.text, italic: ex };
  rowsT.push([
    { text: a.name.replace(', Inc.', '').replace(' Inc.', '').replace(' Co., Ltd.', '').replace(' Corporation', '').replace(' plc', '').replace(' Ltd.', '') + (ex ? ' (выброс)' : ''), options: o },
    { text: a.country, options: { ...o, align: 'center' } },
    { text: n(a.braw, 2), options: { ...o, align: 'center' } },
    { text: n(a.badj, 2), options: { ...o, align: 'center' } },
    { text: pct(a.de, 1), options: { ...o, align: 'center' } },
    { text: pct(a.T, 1), options: { ...o, align: 'center' } },
    { text: n(a.bu, 2), options: { ...o, align: 'center', bold: !ex } },
  ]);
});
rowsT.push([{ text: 'Медиана (9 аналогов)', options: { bold: true } }, '', '', '', { text: pct(V.med_de, 1), options: { bold: true, align: 'center' } }, '', { text: n(V.med, 2), options: { bold: true, align: 'center', fill: { color: 'FFF2CC' } } }]);
s.addTable(rowsT, { x: 0.5, y: 1.25, w: 8.2, colW: [3.0, 1.0, 0.8, 0.8, 0.9, 0.8, 0.9], fontSize: 12, fontFace: 'Calibri', border: { type: 'solid', pt: 0.5, color: 'D9D9D9' }, rowH: 0.36, valign: 'middle', objectName: 'Таблица аналогов' });
card(s, 9.0, 1.25, 3.8, 5.2);
s.addText('Как считали', { x: 9.2, y: 1.4, w: 3.4, h: 0.4, fontSize: 16, bold: true, color: C.text2, isTextBox: true, margin: 0 });
s.addText([
  { text: '60 месячных лог-доходностей (01.2021–12.2025) против индекса своей биржи: S&P 500, S&P/TSX, ISEQ, Nikkei 225', options: { bullet: true, breakLine: true } },
  { text: 'βraw = COV / VAR, затем Блюм: 2/3·β + 1/3', options: { bullet: true, breakLine: true } },
  { text: 'Хамада: βu = βadj / [1 + (1 − T)·D/E], D — долг с арендой, E — капитализация на 31.12.2025', options: { bullet: true, breakLine: true } },
  { text: 'Kobayashi исключена: βraw −0,17 из-за скандала с БАД beni-koji (2024). С ней медиана 0,57', options: { bullet: true } },
], { x: 9.2, y: 1.85, w: 3.45, h: 4.5, fontSize: 13, color: C.text1, isTextBox: true, margin: 0, valign: 'top', paraSpaceAfter: 8 });
src(s, 'Источники: Yahoo Finance (котировки, долг и акции на 31.12.2025, 10-K/10-Q); налоги — IRC §11(b), KPMG Canada, PwC Tax Summaries, Revenue.ie. Расчёт — листы Raw Beta, Blume, Hamada.');
s.addNotes(`Аналоги — производители витаминов и БАД с развитых рынков: USANA, Nature's Sunshine, Jamieson, LifeVantage, плюс смежные — Nu Skin (БАД плюс косметика), Prestige (безрецептурка), Glanbia, Rohto. Для каждого посчитали 60 месячных логарифмических доходностей и бету против индекса своей биржи. Сырые беты ниже единицы — бизнес защитный. После Блюма и снятия рычага медиана 0,61. Kobayashi убрали: у неё отрицательная бета из-за отзыва БАД в 2024 году, это специфический, а не рыночный риск.`);

// ---------------- Slide 3: Hamada & Ke ----------------
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'ДИОД: стоимость капитала' });
s.addText(`Уравнение Хамады и Ke = ${pct(V.keb)}`, { placeholder: 'title' });
const steps = [
  ['βu', n(V.bu, 3), 'медиана аналогов'],
  ['D/E', pct(V.deb, 2), `${th(V.D)} / ${th(V.Eb)} тыс. руб.`],
  ['βlev', n(V.blb, 3), 'βu × [1 + 0,75 × D/E]'],
  ['Ke', pct(V.keb, 2), `13,91% + ${n(V.blb, 3)} × 5,24%`],
];
steps.forEach((st, i) => {
  const x = 0.5 + i * 3.15;
  card(s, x, 1.3, 2.85, 1.75, { fill: i === 3 ? C.accent1 : C.background2 });
  const col = i === 3 ? C.background1 : C.text2;
  s.addText(st[0], { x: x + 0.2, y: 1.4, w: 2.45, h: 0.35, fontSize: 14, color: col, bold: true, isTextBox: true, margin: 0 });
  s.addText(st[1], { x: x + 0.2, y: 1.75, w: 2.45, h: 0.7, fontSize: 32, color: i === 3 ? C.background1 : C.accent1, bold: true, fontFace: 'Cambria', isTextBox: true, margin: 0 });
  s.addText(st[2], { x: x + 0.2, y: 2.5, w: 2.45, h: 0.45, fontSize: 12, color: col, isTextBox: true, margin: 0 });
  if (i < 3) s.addShape(pres.shapes.RIGHT_TRIANGLE, { x: x + 2.92, y: 2.05, w: 0.18, h: 0.26, rotate: 90, fill: { color: C.accent2 }, line: { color: C.accent2 }, objectName: 'Стрелка' });
});
const scen = [
  ['Рыночная D/E (4,8%)', V.kem], ['База: балансовая D/E (6,8%)', V.keb], ['С Kobayashi (10 аналогов)', V.sc_all],
  ['Беты к S&P 500', V.sc_sp], ['Отраслевая D/E 27%', V.sc_ind], ['Собств. бета ДИОД к IMOEX', V.sc_own], ['База + SRP 4,37%', V.sc_srp],
];
s.addChart(pres.charts.BAR, [{ name: 'Ke', labels: scen.map((x) => x[0]), values: scen.map((x) => x[1]) }], {
  x: 0.5, y: 3.3, w: 7.6, h: 3.25, barDir: 'bar', ...chartBase(), title: 'Ke в базе и сценариях проверки', showValue: true, dataLabelPosition: 'outEnd',
  dataLabelFormatCode: '0.00%', valAxisLabelFormatCode: '0%', valAxisMinVal: 0.12, valAxisMaxVal: 0.24, showLegend: false,
  chartColors: [HEX.moss, HEX.forest, HEX.moss, HEX.moss, HEX.moss, HEX.slate, HEX.amber], catAxisOrientation: 'maxMin', barGapWidthPct: 40, objectName: 'График сценариев Ke' });
card(s, 8.4, 3.3, 4.4, 3.25);
s.addText([
  { text: 'Почему 17%: ', options: { bold: true } },
  { text: `премия к ОФЗ всего ${n(V.blb * 5.24, 2)} п.п. — спрос на БАД слабо зависит от цикла, а долга почти нет: рычаг поднимает бету лишь с ${n(V.bu, 2)} до ${n(V.blb, 2)}.`, options: { breakLine: true } },
  { text: ' ', options: { breakLine: true } },
  { text: 'Спад ≠ высокая бета: ', options: { bold: true } },
  { text: 'убытки и списания ДИОД — специфический риск, CAPM его не оценивает. SRP показана только как верхняя граница (21,6%).', options: {} },
], { x: 8.6, y: 3.45, w: 4.0, h: 3.0, fontSize: 13, color: C.text1, isTextBox: true, margin: 0, valign: 'top' });
src(s, 'Источники: лист Ke (Excel); Rf, ERP — задание преподавателя; SRP 10-го дециля 4,37% — ДРТ, сл. 29 (VSCPA 2022). Для рыночных весов Ke = ' + pct(V.kem) + ' (βlev ' + n(V.blm, 3) + ').');
s.addNotes(`Перерычаживаем медиану 0,609 на структуру ДИОД: долг 44,9 млн рублей, из них 30,8 — аренда земли, капитал по МСФО 664,5 млн, D/E 6,8%. Бета вырастает только до 0,64. Ke = 13,91 + 0,64 × 5,24 = 17,26%. По рыночной структуре — 17,22%. Важно, что результат устойчив: при других решениях по выборке и индексу Ke в диапазоне 16,8–17,8%. Собственная бета ДИОД дала бы 18,5%, но акция неликвидна. Премию за размер в базу не включаем, по ДРТ она спорна.`);

// ---------------- Slide 4: ICR, rating, Kd ----------------
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'ДИОД: стоимость капитала' });
s.addText('ICR, синтетический рейтинг и Kd', { placeholder: 'title' });
const h4 = ['Год', 'EBIT, тыс. руб.', 'Проценты, тыс. руб.', 'ICR', 'Рейтинг', 'Спред'].map((t) => ({ text: t, options: { bold: true, color: 'FFFFFF', fill: { color: HEX.forest }, align: 'center' } }));
const r4 = [h4];
V.icr.forEach((y) => {
  const bad = y.rt === 'D';
  r4.push([{ text: String(y.y), options: { align: 'center' } }, { text: th(y.ebit), options: { align: 'right', color: y.ebit < 0 ? HEX.red : HEX.text } },
    { text: th(y.int), options: { align: 'right' } }, { text: n(y.icr, 1), options: { align: 'right', color: y.icr < 0 ? HEX.red : HEX.text } },
    { text: y.rt, options: { align: 'center', bold: true, color: bad ? HEX.red : HEX.forest } }, { text: pct(y.sp, 2), options: { align: 'center' } }]);
});
s.addTable(r4, { x: 0.5, y: 1.25, w: 7.4, colW: [0.8, 1.6, 1.6, 1.2, 1.0, 1.2], fontSize: 13, fontFace: 'Calibri', border: { type: 'solid', pt: 0.5, color: 'D9D9D9' }, rowH: 0.4, valign: 'middle', objectName: 'Таблица ICR' });
s.addText([
  { text: 'Шкала малых компаний: ', options: { bold: true } },
  { text: `капитализация ${n(V.mcap_usd, 1)} млн USD, выручка ${n(V.rev_usd, 1)} млн USD. ICR < 0,5 → D, спред 20%. По шкале крупных — тот же результат. Это расчётная категория, а не официальный рейтинг: у ДИОД рейтинга нет.`, options: {} },
], { x: 0.5, y: 3.85, w: 7.4, h: 0.9, fontSize: 13, color: C.text1, isTextBox: true, margin: 0, valign: 'top' });
card(s, 0.5, 4.85, 7.4, 1.65);
s.addText([
  { text: 'Ограничение метода: ', options: { bold: true, color: HEX.red } },
  { text: `Kd по шкале выше Ke на ${n(V.kd_minus_ke * 100, 1)} п.п. Шкала видит только знак EBIT: компания без кредитов, но с убытком, попадает к банкротам. При этом проценты уплачены ${th(V.intpaid)} тыс. руб. при CFO 60,3 млн, а чистый долг — ${n(V.netdebt / 1000, 1)} млн руб.`, options: {} },
], { x: 0.7, y: 4.95, w: 7.0, h: 1.45, fontSize: 13, color: C.text1, isTextBox: true, margin: 0, valign: 'middle' });
card(s, 8.2, 1.25, 4.6, 2.4, { fill: C.accent1 });
s.addText('Kd по методике', { x: 8.4, y: 1.4, w: 4.2, h: 0.4, fontSize: 15, bold: true, color: C.background1, isTextBox: true, margin: 0 });
s.addText(pct(V.kd), { x: 8.4, y: 1.8, w: 4.2, h: 0.9, fontSize: 48, bold: true, color: C.background1, fontFace: 'Cambria', isTextBox: true, margin: 0 });
s.addText('13,91% + 20,00% (рейтинг D)', { x: 8.4, y: 2.8, w: 4.2, h: 0.4, fontSize: 14, color: C.background1, isTextBox: true, margin: 0 });
card(s, 8.2, 3.85, 4.6, 2.65);
s.addText('Альтернатива (справочно)', { x: 8.4, y: 3.95, w: 4.2, h: 0.4, fontSize: 15, bold: true, color: C.text2, isTextBox: true, margin: 0 });
s.addText([
  { text: `${pct(V.ibr, 1)} — ставка, по которой сама ДИОД дисконтировала новую аренду (МСФО 2025, прим. 5)`, options: { bullet: true, breakLine: true } },
  { text: `${pct(V.sme_lt, 1)} / ${pct(V.sme_st, 1)} — кредиты МСП свыше / до 1 года, ЦБ, декабрь 2025`, options: { bullet: true, breakLine: true } },
  { text: `Принято Kd = ${pct(V.kd_alt, 1)} (≈ B+)`, options: { bullet: true, bold: true } },
], { x: 8.4, y: 4.4, w: 4.25, h: 2.0, fontSize: 13, color: C.text1, isTextBox: true, margin: 0, valign: 'top', paraSpaceAfter: 6 });
src(s, 'Источники: МСФО 2021–2025; лекция «Затраты на капитал», сл. 39; Банк России, cbr.ru/statistics/bank_sector/int_rat/1225/; листы ICR 2021-2025, Рейтинги, Kd.');
s.addNotes(`В 2021–2022 годах ICR огромный — тысячи раз, потому что процентов почти не было, рейтинг AAA. С 2023 года EBIT отрицательный, ICR минус 27, минус 284, минус 22 — рейтинг D, спред 20%, Kd = 33,91%. Шкала малых компаний, потому что капитализация 12 млн долларов. Но результат абсурдный: долг дороже акций. Реально компания занимает по 20% — это её собственная ставка по аренде, а ЦБ даёт 16,6–18,8% по кредитам МСП. Основной расчёт оставляем по методике, альтернативу показываем отдельно.`);

// ---------------- Slide 5: WACC ----------------
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'ДИОД: стоимость капитала' });
s.addText(`WACC: ${pct(V.wb.wacc[0])} по балансу, ${pct(V.wm.wacc[0])} по рынку`, { placeholder: 'title' });
const h5 = ['', 'Балансовые веса', 'Рыночные веса'].map((t) => ({ text: t, options: { bold: true, color: 'FFFFFF', fill: { color: HEX.forest }, align: 'center' } }));
const r5 = [h5,
  ['E, тыс. руб.', th(V.wb.E[0]), th(V.wm.E[0])],
  ['D, тыс. руб.', th(V.wb.D[0]), th(V.wm.D[0])],
  ['We / Wd', `${pct(V.wb.we[0], 1)} / ${pct(V.wb.wd[0], 1)}`, `${pct(V.wm.we[0], 1)} / ${pct(V.wm.wd[0], 1)}`],
  ['Ke', pct(V.wb.ke[0]), pct(V.wm.ke[0])],
  ['Kd (методика) / T', `${pct(V.kd)} / 0%`, `${pct(V.kd)} / 0%`],
  [{ text: 'WACC — база', options: { bold: true } }, { text: pct(V.wb.wacc[0]), options: { bold: true, fill: { color: 'FFF2CC' } } }, { text: pct(V.wm.wacc[0]), options: { bold: true, fill: { color: 'FFF2CC' } } }],
  ['WACC, полный щит 25%', pct(V.wb.wacc[1]), pct(V.wm.wacc[1])],
  ['WACC, Kd 20%, без щита', pct(V.wb.wacc[2]), pct(V.wm.wacc[2])],
  ['WACC, Kd 20%, щит 25%', pct(V.wb.wacc[3]), pct(V.wm.wacc[3])],
].map((row, i) => i === 0 ? row : row.map((c, j) => typeof c === 'string' ? { text: c, options: { align: j ? 'center' : 'left' } } : { text: c.text, options: { ...c.options, align: j ? 'center' : 'left' } }));
s.addTable(r5, { x: 0.5, y: 1.25, w: 6.3, colW: [2.5, 1.9, 1.9], fontSize: 13, fontFace: 'Calibri', border: { type: 'solid', pt: 0.5, color: 'D9D9D9' }, rowH: 0.4, valign: 'middle', objectName: 'Таблица WACC' });
s.addChart(pres.charts.BAR, [
  { name: 'Балансовые веса', labels: ['База', 'Щит 25%', 'Kd 20%', 'Kd 20% + щит'], values: V.wb.wacc },
  { name: 'Рыночные веса', labels: ['База', 'Щит 25%', 'Kd 20%', 'Kd 20% + щит'], values: V.wm.wacc },
], { x: 7.1, y: 1.25, w: 5.7, h: 3.1, barDir: 'col', ...chartBase(), title: 'WACC по вариантам', showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '0.0%',
  valAxisLabelFormatCode: '0%', valAxisMinVal: 0.15, valAxisMaxVal: 0.19, chartColors: [HEX.forest, HEX.moss], showLegend: true, legendPos: 'b', legendFontSize: 11, barGapWidthPct: 50, objectName: 'График WACC' });
card(s, 7.1, 4.5, 5.7, 2.0);
s.addText([
  { text: 'Почему различаются: ', options: { bold: true } },
  { text: `рынок ценит капитал в ${n(V.Em / 1e6, 2)} млрд руб., баланс — в ${n(V.Eb / 1e6, 2)} (P/B ${n(V.Em / V.Eb, 2)}). Вес «дорогого» по рейтингу долга по рынку меньше — ${pct(V.wm.wd[0], 1)}, поэтому WACC ниже на ${n((V.wb.wacc[0] - V.wm.wacc[0]) * 100, 2)} п.п.`, options: { breakLine: true } },
  { text: 'Щит: ', options: { bold: true } },
  { text: 'при убытке экономии нет, в базе T = 0.', options: {} },
], { x: 7.3, y: 4.6, w: 5.3, h: 1.8, fontSize: 13, color: C.text1, isTextBox: true, margin: 0, valign: 'middle' });
src(s, 'Источники: листы WACC (Excel); МСФО 2025: D = займы 13 949 + фин. обязательства 30 962 тыс. руб. (аренда 30 763); E — 10,26 руб. × 90 515 488 акций (Мосбиржа).');
s.addNotes(`WACC = Ke × We + Kd × (1 − T) × Wd. Долг — займы дочерних обществ плюс аренда, кредиторку и отложенные налоги в долг не включаем. Для рыночных весов исключили 984 тысячи собственных акций. По балансу WACC 18,32%, по рынку 17,99%. Налоговый щит в базе не применяем: группа в 2025 году убыточна. Если взять реалистичный Kd 20%, WACC около 17,3–17,4%. Разница между вариантами небольшая, потому что доля долга всего 5–6%.`);

// ---------------- Slide 6: interpretation ----------------
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'ДИОД: стоимость капитала' });
s.addText('Что эти цифры говорят о ДИОД', { placeholder: 'title' });
const cards6 = [
  ['Стадия спада', `Капитал за 5 лет −46% (${n(V.eq[0] / 1e6, 2)} → ${n(V.eq[4] / 1e6, 2)} млрд руб.), деньги ${th(V.cash[0] / 1000)} → ${th(V.cash[4] / 1000)} млн. Дивиденды ~72 млн руб. в год платятся при убытках и «съедают» капитал.`],
  ['Ke ≈ 17%', 'Отрасль защитная (βu 0,61), рычага нет. Риск спада — специфический: он виден в убытках и в Kd, а не в бете.'],
  ['Kd: рейтинг D', `Отрицательный EBIT три года подряд (2023–2025) → D при любой шкале. Реальная стоимость нового долга ~20%: малый заёмщик без рейтинга и прибыли.`],
  ['Мало долга', 'D/E 6,8%: долг — аренда земли и займы «дочек». Брать кредит невыгодно: щита нет, ставка выше Ke. Низкий долг — не надёжность, а отсутствие дешёвых источников.'],
];
cards6.forEach((c6, i) => {
  const x = 0.5 + (i % 2) * 6.25, y = 1.25 + Math.floor(i / 2) * 1.75;
  card(s, x, y, 6.05, 1.55);
  s.addText(c6[0], { x: x + 0.25, y: y + 0.15, w: 5.6, h: 0.4, fontSize: 17, bold: true, color: C.text2, isTextBox: true, margin: 0 });
  s.addText(c6[1], { x: x + 0.25, y: y + 0.6, w: 5.6, h: 1.1, fontSize: 13, color: C.text1, isTextBox: true, margin: 0, valign: 'top' });
});
s.addChart(pres.charts.LINE, [{ name: 'EBIT', labels: ['2021', '2022', '2023', '2024', '2025'], values: V.ebit.map((e, i) => e / 1000) }], {
  x: 0.5, y: 4.85, w: 6.05, h: 1.6, ...chartBase(), showTitle: false, showValue: true, dataLabelPosition: 't', dataLabelFormatCode: '#,##0', chartColors: [HEX.red], lineSize: 2, lineDataSymbolSize: 6,
  valAxisHidden: true, valGridLine: { style: 'none' }, showLegend: false, objectName: 'Линия EBIT' });
s.addText('EBIT, млн руб.: из прибыли в убыток', { x: 6.75, y: 4.95, w: 6.05, h: 0.4, fontSize: 13, bold: true, color: C.text2, isTextBox: true, margin: 0 });
s.addText('Итог для политики: требуемая доходность проектов ~17–18%; новый долг не нужен, пока не восстановлен EBIT; дивиденды стоит привязать к денежному потоку.', { x: 6.75, y: 5.4, w: 6.05, h: 0.9, fontSize: 13, color: C.text1, isTextBox: true, margin: 0, valign: 'top' });
src(s, 'Источники: МСФО 2021–2025; лист «Итоги и выводы» (Excel).');
s.addNotes(`Главная мысль: CAPM даёт умеренный Ke, потому что бизнес БАД защитный и долга нет. А вот кредитный риск у ДИОД высокий — это видно по рейтингу D и по тому, что капитал за пять лет сократился почти вдвое. Долга мало не потому, что компания надёжна, а потому что занимать дорого и налогового щита нет. Для политики: проекты должны приносить больше 17–18%, долг сейчас не наращивать, дивиденды привязать к денежному потоку.`);

// ---------------- Slide 7: limitations ----------------
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'ДИОД: стоимость капитала' });
s.addText('Ограничения расчётов', { placeholder: 'title' });
const lim = [
  ['Синтетический рейтинг', 'Не работает при отрицательном EBIT и почти нулевых процентах: Kd 33,91% > Ke 17,26%. Показали альтернативу 20%, разница в WACC ~0,9 п.п.'],
  ['Аналоги', 'Все крупнее ДИОД (79 млн – 4,2 млрд USD против 12 млн) и не в спаде; R² регрессий 0,00–0,17 — беты оценены с большой ошибкой, поэтому медиана.'],
  ['Индексы и цены', 'Ценовые индексы и цены без дивидендов (одинаково для акции и рынка); для Японии — Nikkei 225 (TOPIX в источнике недоступен).'],
  ['Данные ДИОД', 'Состав процентных расходов (аренда/займы) в МСФО не раскрыт; аренда за 2021–2023 отдельно не раскрыта — РСБУ не подставляли.'],
  ['Премии', 'ERP России статистически неустойчива (ДРТ, сл. 20); SRP не включена — с ней Ke был бы 21,6%.'],
];
lim.forEach((l, i) => {
  const y = 1.25 + i * 1.05;
  card(s, 0.5, y, 12.3, 0.9);
  s.addShape(pres.shapes.OVAL, { x: 0.7, y: y + 0.2, w: 0.5, h: 0.5, fill: { color: C.accent2 }, line: { color: C.accent2 }, objectName: 'Номер ' + (i + 1) });
  s.addText(String(i + 1), { x: 0.7, y: y + 0.2, w: 0.5, h: 0.5, fontSize: 14, bold: true, color: C.background1, align: 'center', valign: 'middle', isTextBox: true, margin: 0 });
  s.addText(l[0], { x: 1.45, y: y + 0.1, w: 2.8, h: 0.7, fontSize: 15, bold: true, color: C.text2, isTextBox: true, margin: 0, valign: 'middle' });
  s.addText(l[1], { x: 4.3, y: y + 0.1, w: 8.3, h: 0.7, fontSize: 13, color: C.text1, isTextBox: true, margin: 0, valign: 'middle' });
});
src(s, 'Источники: листы Raw Beta, Hamada, Kd (Excel); АО ДРТ, сл. 20, 26–29; лекция, сл. 36 (налоговый щит при ухудшении бизнеса).');
s.addNotes(`Главное ограничение — синтетический рейтинг: при убытке он механически даёт D, и Kd оказывается выше Ke. Поэтому мы показываем и альтернативную оценку. Аналоги крупнее ДИОД, а беты статистически шумные — поэтому берём медиану. По ДИОД не раскрыт состав процентных расходов. Премию за размер в базу не включали, но если включить, Ke вырос бы до 21,6%.`);

pres.writeFile({ fileName: OUT }).then(async () => { await applyTheme(OUT, THEME); console.log('ok', OUT); });
