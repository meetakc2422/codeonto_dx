# Codeonto

Multi-industry reputation + marketplace intelligence dashboard (Django + Postgres).

## Setup

```bash
python3.13 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp .env.example .env              # fill in values
createdb codeonto_app
./.venv/bin/python manage.py migrate            # creates tables + starter master data
./.venv/bin/python manage.py createsuperuser    # your admin login
./.venv/bin/python manage.py sync_catalog       # Zomato / Swiggy / Google ids from the pipeline (read-only)
```

## Run

```bash
./.venv/bin/python manage.py runserver 8010
```

- Dashboard: http://localhost:8010/
- Admin (clients, brands, outlet mapping, masters): http://localhost:8010/admin/

## Data model

```
platforms, industries, modules, kpis     masters (data, edited in admin; starter rows from a migration)

platform_accounts                        platform logins: Codeonto master accounts (client empty)
                                         or a client's own login (client set)
zomato_outlets     (res_id)              catalogs: every outlet id those logins can access, filled by the
swiggy_outlets     (swiggy_id)           collector; each id has an OWNER client
google_locations   (location_id)

clients -> brands                        the paying company and its brands (custom names)
client_users                             which login (Django user) belongs to which client, and its role
brand_outlets                            THE MAPPING, made by the client: one row = one store with its
                                         zomato_res_id / swiggy_id / google_location_id (each used once)
```

## Who can do what

| | Codeonto staff | Client admin / manager | Client viewer |
|---|---|---|---|
| See clients / brands | all | own client only | own client only |
| Assign catalog ids to a client | ✅ admin → catalog list → *Assign selected ids to a client…* | ❌ | ❌ |
| Create brands, map stores, bulk CSV | ✅ | ✅ own brands, own ids only | ❌ read only |

**How a client gets ids:** staff assign them (from Codeonto's master accounts), or the client's own
login is added as a Platform account with that client set; `collector/run.py <platform> outlets` then gives
every id it finds to that client (never taking ids another client already owns).

**Rules on every mapping save** (dashboard, CSV, admin): the id exists in the catalog, is active, belongs to
the brand's client, and is used by one store only.

## Onboarding a client

1. Admin → **Clients** → add the client.
2. Dashboard → **Clients** → the client → **Manage team** → add a login (owner, outlet manager or viewer).
   Owners add their own logins on the same **Team** page: a manager sees only the outlets assigned there, across any of the client's brands; a viewer reads the whole client. Staff can also delete logins there.
3. Admin → **Zomato outlets / Swiggy outlets / Google locations** → filter, tick their ids → *Assign selected ids to a client…*
4. The client logs in to the dashboard → **Brands & Outlets** → creates brands, then maps stores manually
   (*+ Pick*, *Add from catalog*) or with **Bulk upload CSV**
   (`store_name, area, city, zomato_res_id, swiggy_id, google_location_id`; checked row by row, saved all-or-nothing).

## Apps

| App | Contents |
|---|---|
| `apps.masters` | Platform, Industry, Module, Kpi |
| `apps.outlets` | PlatformAccount, catalogs, Client, ClientUser, Brand, BrandOutlet; access rules, mapping service, CSV import, login API |
| `apps.reviews` | Review, ReviewReply |
| `apps.metrics` | MetricDaily, KPI aggregation API, rollups |
| `apps.integrations` | Platform connectors (Google, Zomato, Swiggy) |

## Commands

| Command | What it does |
|---|---|
| `manage.py sync_catalog [--platform zomato]` | One-off bootstrap of catalog tables from the pipeline DB (`PIPELINE_DATABASE_URL`). Live catalogs come from `collector/run.py all outlets` |

## External platforms

Everything that calls Zomato / Swiggy / Google lives in [`collector/`](collector/README.md), a separate
project in this repo. It writes sessions and outlet catalogs; Django reads them. Master accounts are
rows in Admin → Platform accounts (label = collector account name, `credentials_ref` = session file).
