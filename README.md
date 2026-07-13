# Job Discovery Agent

Daily job alerts to Telegram. Pulls fresh listings (last 24h) from the Adzuna
API and from public Greenhouse / Lever / Ashby company job boards, filters to
entry/mid-level roles, scans descriptions for visa-sponsorship signals, detects
the application interface (Greenhouse, Lever, Workday, ...), dedupes against a
local SQLite database, and sends a grouped digest via a Telegram bot.

## Setup

### 1. Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Adzuna API (free)

Register at [developer.adzuna.com](https://developer.adzuna.com), create an app,
and copy the App ID and App Key into `.env`:

```
ADZUNA_APP_ID=...
ADZUNA_APP_KEY=...
```

### 3. Telegram

The bot token is already in `.env`. To find your chat id:

1. Open Telegram, find your bot, and send it any message (e.g. "hi").
2. Run `python get_chat_id.py` — it prints your chat id.
3. Paste it into `.env` as `TELEGRAM_CHAT_ID`.

### 4. Run

```bash
python main.py            # fetch + send digest to Telegram
python main.py --dry-run  # print jobs to terminal instead of sending
```

Every job that has been surfaced once is recorded in `jobs.db` (keyed by job
URL) and will never be sent again.

## Configuration (`config.yaml`)

- `keywords` — role titles to search for
- `exclude_title_terms` — seniority words that exclude a job (senior, staff, ...)
- `sponsorship` — positive/negative signal phrases scanned in descriptions
- `ats_boards` — company slugs polled directly on Greenhouse/Lever/Ashby;
  add any company here (slug is the last part of their job-board URL)
- `telegram.max_jobs_per_digest` — cap on messages per run

## GitHub Actions (daily at 8 AM ET)

The workflow in `.github/workflows/job-digest.yml` runs daily at 12:00 UTC
(8 AM EDT; 7 AM EST during winter since GitHub cron is UTC-only) and commits
`jobs.db` back to the repo so dedupe persists across runs.

1. Push this repo to GitHub.
2. In the repo: Settings -> Secrets and variables -> Actions -> New repository
   secret. Add: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ADZUNA_APP_ID`,
   `ADZUNA_APP_KEY`.
3. Trigger a test run: Actions tab -> Daily Job Digest -> Run workflow.

Note: `.env` is gitignored — never commit it. If the bot token ever leaks,
revoke it with @BotFather (`/revoke`) and update the secret.
