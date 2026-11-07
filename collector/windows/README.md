# Collector services on Windows

Everything the live collector machine runs, in one place. The collector folder is a clone of this repo's
`collector/`, with its own `.venv`, `.env` and `logs/`. Logs for every job go to `logs/collector.log`.

| What | File | How it runs |
|---|---|---|
| Login refresh worker: does the **Log in again** clicks from the site's Sessions page | `run.py worker` | at logon, keeps running |
| Zomato menu proxy: competitor menus for the site (Zomato blocks cloud IPs) | `menu_proxy.py` | at logon, keeps running, port 5000 |
| Live monitors: uptime, stock-outs, alerts, reviews, complaints | `run.py … --every N` | at logon, keep running |
| Daily jobs: logins, outlets, business, item sales, timings, payouts, ratings, Google | `run.py …` | once a day |

The full list and times are in `register_tasks.ps1` (`$Jobs`); edit it and run the script again to change them.

## First time on a new machine

1. Install Python 3.12+ (tick "Add to PATH") and Git.
2. Clone the repo, then in PowerShell from the `collector` folder:
   ```
   powershell -ExecutionPolicy Bypass -File windows\setup.ps1
   ```
3. Fill in `collector\.env`: the database URL (`CODEONTO_DATABASE_URL`), `GOOGLE_TOKEN_KEY` (same as the site), the
   login emails and IMAP passwords, and `MENU_PROXY_SECRET` (same value as `ZOMATO_MENU_PROXY_SECRET` on the site).
4. Check it without calling any platform: `.venv\Scripts\python run.py all session --check`
5. Register everything in Task Scheduler (as the user that stays logged in on the server):
   ```
   powershell -ExecutionPolicy Bypass -File windows\register_tasks.ps1
   ```
6. Windows Firewall: allow inbound TCP 5000 **only from the site server's IP** (for the menu proxy):
   ```
   New-NetFirewallRule -DisplayName "Menu proxy from site" -Direction Inbound -Protocol TCP -LocalPort 5000 -RemoteAddress <site-ip> -Action Allow
   ```
7. On the site's `.env`: `ZOMATO_MENU_PROXY_URL=http://<this machine's IP>:5000` and `ZOMATO_MENU_PROXY_SECRET`.

Stop running the same jobs anywhere else (e.g. a Mac), so two machines don't write at once. Remove every task with
`register_tasks.ps1 -Remove`.

## Day to day

- **A login expired**: the site shows a red banner to staff. Open **Sessions → Log in again**; this machine's worker
  logs in (browser + email OTP) within a minute or two and the button shows Done or the reason it failed.
- **Is it running?** Task Scheduler → `Codeonto collector`, or the end of `logs\collector.log`.
- **Update the code**: `git pull` in the repo folder, then restart the logon tasks (or log off and on).
