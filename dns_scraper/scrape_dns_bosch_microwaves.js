// Сбор цен и характеристик микроволновок Bosch с dns-shop.ru.
// Запуск (на своём компьютере):
//   npm i playwright && npx playwright install chromium
//   node scrape_dns_bosch_microwaves.js
// Браузер открывается видимым: если DNS покажет проверку/капчу — пройдите её вручную,
// скрипт подождёт. Результат: bosch_microwaves.json и bosch_microwaves.csv.
const fs = require('fs');
const { chromium } = require('playwright');

const SEARCH_URL = 'https://www.dns-shop.ru/search/?q=' +
  encodeURIComponent('микроволновая печь bosch');
const MAX_PAGES = 10;

async function waitForCatalog(page) {
  // Даём время на прохождение антибот-проверки вручную (до 3 минут).
  await page.waitForSelector('.catalog-product, .product-card-top', { timeout: 180000 });
}

async function collectLinks(page) {
  const links = new Map();
  for (let n = 1; n <= MAX_PAGES; n++) {
    const url = n === 1 ? page.url() : page.url().replace(/([?&])p=\d+/, '$1') + `&p=${n}`;
    if (n > 1) await page.goto(url, { waitUntil: 'domcontentloaded' });
    try { await waitForCatalog(page); } catch { break; }
    await page.waitForTimeout(2500); // цены подгружаются отдельным запросом
    const items = await page.$$eval('.catalog-product', cards => cards.map(c => {
      const a = c.querySelector('a.catalog-product__name');
      const price = c.querySelector('.product-buy__price');
      return a && {
        name: a.textContent.trim(),
        url: a.href,
        listPrice: price ? price.textContent.replace(/\s+/g, ' ').trim() : '',
      };
    }).filter(Boolean));
    const before = links.size;
    for (const it of items) if (/bosch/i.test(it.name)) links.set(it.url, it);
    if (items.length === 0 || links.size === before) break;
  }
  return [...links.values()];
}

async function scrapeProduct(page, item) {
  const base = item.url.replace(/\/?$/, '/').replace(/characteristics\/$/, '');
  await page.goto(base + 'characteristics/', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.product-characteristics__spec, .product-card-top', { timeout: 180000 });
  await page.waitForTimeout(2000);
  return page.evaluate(() => {
    const txt = s => (document.querySelector(s)?.textContent || '').replace(/\s+/g, ' ').trim();
    const specs = {};
    document.querySelectorAll('.product-characteristics__spec').forEach(row => {
      const k = row.querySelector('.product-characteristics__spec-title')?.textContent.trim();
      const v = row.querySelector('.product-characteristics__spec-value')?.textContent.trim();
      if (k) specs[k] = v || '';
    });
    return {
      title: txt('.product-card-top__title') || txt('h1'),
      price: txt('.product-buy__price'),
      code: txt('.product-card-top__code'),
      specs,
    };
  });
}

function toCsv(rows) {
  const keys = [...new Set(rows.flatMap(r => Object.keys(r.specs)))];
  const head = ['Название', 'Цена', 'Код', 'URL', ...keys];
  const esc = v => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const lines = rows.map(r => [r.title, r.price, r.code, r.url, ...keys.map(k => r.specs[k])].map(esc).join(';'));
  return '﻿' + [head.map(esc).join(';'), ...lines].join('\n');
}

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await (await browser.newContext({ locale: 'ru-RU' })).newPage();
  await page.goto(SEARCH_URL, { waitUntil: 'domcontentloaded' });
  await waitForCatalog(page);
  const items = await collectLinks(page);
  console.log(`Найдено товаров Bosch: ${items.length}`);

  const rows = [];
  for (const [i, item] of items.entries()) {
    try {
      const d = await scrapeProduct(page, item);
      rows.push({ ...d, title: d.title || item.name, price: d.price || item.listPrice, url: item.url });
      console.log(`[${i + 1}/${items.length}] ${d.title || item.name} — ${d.price || item.listPrice}`);
    } catch (e) {
      console.warn(`Не удалось: ${item.url} (${e.message})`);
    }
    await page.waitForTimeout(1500 + Math.random() * 1500); // не нагружаем сайт
  }

  fs.writeFileSync('bosch_microwaves.json', JSON.stringify(rows, null, 2));
  fs.writeFileSync('bosch_microwaves.csv', toCsv(rows));
  console.log('Готово: bosch_microwaves.json, bosch_microwaves.csv');
  await browser.close();
})();
