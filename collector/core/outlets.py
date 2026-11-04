"""Shared 'outlets' job: ask each account which outlets it can access and update the catalog."""

from collections.abc import Callable

from . import catalog, db
from .common import ConfigError, log, require_env

Fetch = Callable[[dict], list[catalog.Outlet]]  # credentials -> outlets


def config(account: str) -> dict:
    return require_env("CODEONTO_DATABASE_URL")


def sync(platform: str, accounts: list[str], fetch: Fetch, force: bool = False) -> bool:
    """Each account in its own transaction, so one expired session doesn't undo the others.

    Ids no account returned are deactivated only when every active account of the platform
    was read successfully in this run (otherwise we can't know they're really gone)."""
    try:
        config("")
    except ConfigError as e:
        log.error("%s outlets: %s", platform, e)
        return False

    seen: set[str] = set()
    synced_ids, failed = set(), []
    for label in accounts:
        try:
            with db.transaction() as cur:
                account = db.get_account(cur, platform, label)
                outlets = fetch(db.load_credentials(account))
                if account.get("only_ids"):  # a login that sees more outlets than we serve: keep just ours
                    keep = {str(i) for i in account["only_ids"]}
                    outlets = [o for o in outlets if str(o.external_id) in keep]
                stats = catalog.upsert(cur, platform, outlets, account["id"], account["client_id"])
                db.mark_account_synced(cur, account["id"])
            seen |= {o.external_id for o in outlets}
            synced_ids.add(account["id"])
            log.info("%s outlets %s: %s", platform, label, stats)
        except (ConfigError, PermissionError) as e:
            log.error("%s outlets %s: %s", platform, label, e)
            failed.append(label)
        except Exception as e:
            log.exception("%s outlets %s failed: %s", platform, label, e)
            failed.append(label)

    with db.transaction() as cur:
        missing_accounts = db.active_account_ids(cur, platform) - synced_ids
        if failed or missing_accounts or not seen:
            log.info("%s: deactivation skipped (not every active account was read this run)", platform)
        else:
            log.info("%s: %s", platform, catalog.deactivate_missing(cur, platform, seen, force))
    return not failed
