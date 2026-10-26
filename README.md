# Сканер новостей → Telegram

Следит за ~25 лентами (российские СМИ, рынки, центробанки, мировые СМИ, крупная крипта),
отбирает важное и сразу присылает в Telegram. Опционально читает Telegram-каналы
в реальном времени, а они обычно быстрее сайтов.

## Как он решает, что важно

1. **Ключевые слова с весами** (`config.yaml` → `keywords`): темы (Путин, санкции, ключевая ставка,
   Сбер, ФРС, нефть, Иран, Bitcoin ETF…) и действия (повысил, запретил, одобрил, обвал…).
   Действия добавляют баллы, только если тема уже найдена. Новость с суммой от `thresholds.send` (6) уходит в Telegram,
   с суммой от `thresholds.urgent` (10) помечается 🔴.
2. **Подтверждение несколькими источниками**: если одну историю за 6 часов опубликовали 3+ разных СМИ,
   она приходит, даже если ключевых слов мало. Одинаковые новости склеиваются, дублей нет.
3. **Чёрный список**: спорт, шоу-бизнес, погода и т.п. отбрасываются.
4. **Крипта**: из крипто-лент берутся только новости про BTC/ETH, ETF, SEC, регулирование и крупные события.
   Мемкоины, аирдропы, пресейлы и альткоины отбрасываются из любых лент.

## Быстрый старт

```bash
pip install -r requirements.txt
python -m scanner --once -v     # посмотреть, что прошло бы фильтр за последние 2 часа, с баллами
```

### Подключить Telegram-бота

1. Напишите [@BotFather](https://t.me/BotFather) → `/newbot` → получите токен.
2. Напишите своему боту любое сообщение (иначе он не сможет вам писать).
3. Узнайте свой chat id у [@userinfobot](https://t.me/userinfobot).
4. `cp .env.example .env` и впишите `BOT_TOKEN` и `CHAT_ID`.
5. `python -m scanner`

При первом запуске сканер запоминает всё, что уже есть в лентах, и присылает только новое.

### Telegram-каналы (быстрее всего)

Каналы вроде @markettwits публикуют новости раньше сайтов. Сканер читает их через ваш
аккаунт и пропускает через те же фильтры.

1. Получите `api_id` и `api_hash` на https://my.telegram.org → API development tools.
2. Впишите их в `.env` (`TG_API_ID`, `TG_API_HASH`), выполните `pip install telethon`.
3. Список каналов задаётся в `config.yaml` → `telegram_channels`.
4. При первом запуске Telethon спросит телефон и код. Сессия сохранится в `scanner.session`,
   никому этот файл не передавайте.

## Работа 24/7

Нужен любой VPS (от ~300 ₽/мес). Варианты запуска:

**Docker:**
```bash
mkdir -p data && sed -i 's|^db_path: scanner.db|db_path: data/scanner.db|' config.yaml
docker build -t news-scanner .
docker run -d --restart=always --env-file .env -v $PWD/data:/app/data --name news news-scanner
```

**systemd** (`/etc/systemd/system/news-scanner.service`):
```ini
[Service]
WorkingDirectory=/opt/news-scanner
ExecStart=/usr/bin/python3 -m scanner
Restart=always

[Install]
WantedBy=multi-user.target
```

## Настройка

Всё в `config.yaml`:
- слишком много уведомлений → поднимите `thresholds.send` или уберите общие слова;
- что-то важное не приходит → добавьте слово или источник;
- `python -m scanner --once -v` показывает баллы и найденные слова для каждой новости, этим удобно подбирать веса.

Тесты: `pytest`.
