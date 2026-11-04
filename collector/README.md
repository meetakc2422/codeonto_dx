# collector

Standalone project (not part of the Django app) for every job that talks to an external
platform: logging in, refreshing sessions, and later pulling outlets, reviews, orders and
metrics from Zomato, Swiggy, Google and others.

**Rule:** the collector makes every external API call and writes the results into the Codeonto
database (`CODEONTO_DATABASE_URL`). Django never calls the platforms; it reads those tables and
manages mappings.

| Task | Writes |
|---|---|
| `session` | `sessions/<platform>_<account>.json` (login sessions) |
| `outlets` | `zomato_outlets` / `swiggy_outlets` / `google_locations` rows, linked to the account, + `platform_accounts.last_synced_at` |

Accounts are rows in Codeonto admin → Platform accounts: **label = the collector account name**
(`main`, `mn`, `ggn`) and `credentials_ref = file:/path/to/session.json`.

No credentials live in code: every login comes from `.env` (git-ignored). Session files are
written atomically with owner-only permissions; OTPs and tokens are never logged.

## Layout

```
collector/
├── run.py            CLI: python run.py <platform|all> <task> [--account …]
├── core/             shared: config, logging, DB access, catalog writes, safe files, server push
├── zomato/           session.py, outlets.py   (later: reviews.py, orders.py …)
├── swiggy/           session.py, outlets.py
├── google_business/  session.py, outlets.py   (platform code: google; folder name avoids clashing with Google's own `google` package)
├── sessions/         output session files   (git-ignored)
└── logs/collector.log                        (git-ignored)
```

## Setup

```bash
cd collector
python3.13 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/playwright install chromium
cp .env.example .env     # fill in logins
./.venv/bin/python run.py all session --check
```

## Run

```bash
./.venv/bin/python run.py all session                       # refresh every account in ACCOUNTS
./.venv/bin/python run.py swiggy session --account mn       # one account
./.venv/bin/python run.py all outlets                       # accessible outlets -> catalog tables
./.venv/bin/python run.py swiggy outlets --account mn --account ggn
./.venv/bin/python run.py all session --daily-at 06:00      # stay running, repeat daily
./.venv/bin/python run.py zomato uptime                      # stay running: store online/offline every 5 min (--once for one pass)
./.venv/bin/python run.py zomato payouts --daily-at 06:00    # payout cycles, orders and reconciliation, once a day
./.venv/bin/python run.py swiggy payouts --daily-at 06:30    # the same for Swiggy
```

Add `--headless` on a server without a display.

### Outlets safety rules

- Each account is written in its own transaction: one expired session never undoes the others.
- Empty values never overwrite known ones (Swiggy sends no city).
- Ids no account returned are deactivated only when **every** active account of that platform was
  read in this run, and at most 20% of the catalog at once; `--force` lifts the limit after you checked.
- Deactivated ids keep their brand mapping (visible as inactive), nothing is silently unmapped.

## Google Business Profile

```bash
./.venv/bin/python run.py google session --account agency    # once: browser opens, log in with the Google
                                                              # account that manages the listings, click Allow
./.venv/bin/python run.py google outlets --account agency    # every Business account -> every location
```

- `GOOGLE_OAUTH_CLIENT_FILE` must be a **Desktop** ("installed") OAuth client JSON.
- The Google Cloud project behind it needs the *My Business Account Management API* and
  *My Business Business Information API* enabled (and Business Profile API access approved).
- After the first login the session refreshes itself; `session` only needs the browser again if access is revoked.
- Each client who gives you access through their own Google account becomes another account
  (`google:<name>` in `ACCOUNTS` + a Platform account row), logged in once the same way.

## Session files

| Platform | File | Shape |
|---|---|---|
| Zomato | `sessions/zomato_<account>.json` | flat cookie dict `{"name": "value"}` |
| Swiggy | `sessions/swiggy_<account>.json` | `{"access_token", "cookies", "outlets": [{rest_id, rest_name, area_name}], "updated_at"}` |
| Google | `sessions/google_<account>.json` | OAuth credentials with refresh token |

## Adding things

- **An account:** add `platform:name` to `ACCOUNTS` plus its `ZOMATO_<NAME>_*` / `SWIGGY_<NAME>_*`
  settings, run it once, then add a Platform account in Codeonto admin pointing at its session file.
- **A job:** add a module with `config(account)` and `run(account, headless)` (or
  `run_all(accounts, headless, force)` when it needs every account at once), e.g. `zomato/reviews.py`,
  and register it in `TASKS` in `run.py`.
- **A platform:** add a folder with its modules and a `TASKS` entry.

## Notes

- The Zomato login modal is clicked by screen position (selectors can't reach it). If Zomato
  changes the modal, update the `CLICK_*` coordinates in `zomato/session.py`.
