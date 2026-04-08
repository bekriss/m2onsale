# 🏠 Apartment Listings Telegram Bot

Monitors **Otodom** and **OLX** for new apartment sale listings and sends matching ones to your Telegram chat or channel.

## Features

- 🔍 Scrapes Otodom & OLX automatically (every 5 minutes by default)
- 🔔 Sends new matching listings directly to Telegram
- 🚫 Deduplication — never sends the same listing twice
- ⚙️ Per-chat filters: location, rooms, price range, apartment size
- 💾 Persistent SQLite storage — survives restarts
- 🐳 Docker-ready for easy deployment

## Quick Start

### 1. Create a Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the **bot token** you receive

### 2. Install dependencies

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env and set TELEGRAM_BOT_TOKEN=your_token_here
export $(cat .env | xargs)
```

### 4. Run

```bash
python bot.py
```

---

## Docker Deployment (Recommended)

```bash
cp .env.example .env
# Edit .env with your token

docker compose up -d
docker compose logs -f   # watch logs
```

---

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message & main menu |
| `/menu` | Show main menu |
| `/stop` | Pause notifications |
| `/status` | Show current filters & status |

## Filter Options

All filters are optional. Set them via the ⚙️ **Set Filters** menu:

| Filter | Example values |
|--------|---------------|
| Location | `Warszawa`, `Kraków Śródmieście`, `Mokotów` |
| Rooms | `2`, `3`, `2,3` (multiple), `2-4` (range) |
| Min price | `300000` |
| Max price | `800000` |
| Min size | `40` (m²) |
| Max size | `90` (m²) |

Type `any` to clear a filter.

---

## Using with a Channel

1. Add your bot to the channel as an **administrator**
2. Send `/start` in the channel
3. Configure filters via the menu
4. Enable notifications

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | *required* | Your bot token from BotFather |
| `CHECK_INTERVAL_SECONDS` | `300` | How often to check for new listings |
| `DB_PATH` | `listings.db` | SQLite database path |

---

## Architecture

```
bot.py          — Telegram bot, command handlers, job scheduler
scraper.py      — Async HTTP scraper for Otodom & OLX
storage.py      — SQLite persistence (seen listings, chat configs, filters)
filters.py      — Filter matching logic
listings.db     — Auto-created SQLite database
```

## Notes

- Both Otodom and OLX use dynamic JavaScript rendering for some content. The scraper handles both HTML parsing and JSON extraction from embedded script tags.
- If a site changes its HTML structure, the scraper may need updating. Check `bot.log` for errors.
- Be respectful of rate limits — the default 5-minute interval is reasonable.

## Troubleshooting

**Bot not responding**: Make sure `TELEGRAM_BOT_TOKEN` is set correctly.

**No listings coming through**: 
- Use `/status` to check filters aren't too restrictive
- Use 🔍 **Fetch Now** to trigger an immediate check
- Check `bot.log` for scraper errors

**Otodom/OLX changed their layout**: The scraper may need updating. Open an issue or adjust the selectors in `scraper.py`.
