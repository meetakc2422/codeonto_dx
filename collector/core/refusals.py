"""When a platform refuses one store, skip it and carry on; only several refusals in a row on the same login mean the
session itself has expired. Before this, one store a login can't open stopped the whole run for every brand."""

from . import config as cfg
from .common import log


class Refusals:
    def __init__(self, job: str):
        self.job = job
        self.limit = cfg.integer("ZOMATO_REFUSALS_BEFORE_STOP", 3)
        self.in_a_row: dict = {}
        self.answered: dict = {}  # stores a login answered this run: proof the login itself is alive
        self.dead: set = set()
        self.skipped: list[str] = []

    def is_dead(self, account) -> bool:
        return account in self.dead

    def success(self, account) -> None:
        self.in_a_row[account] = 0
        self.answered[account] = self.answered.get(account, 0) + 1

    def refused(self, account, store: str, err) -> None:
        """Count a refusal. After `limit` in a row on one login, that login's remaining stores are skipped."""
        self.in_a_row[account] = self.in_a_row.get(account, 0) + 1
        self.skipped.append(store)
        log.warning("%s %s: refused, skipping (%s)", self.job, store, err)
        if self.in_a_row[account] >= self.limit and self.answered.get(account):
            # other stores of this login answered, so it is alive: these stores are ones it may not open (a wrong id, one added to another login)
            self.in_a_row[account] = 0
            log.warning("%s: login is fine (%s stores answered) but %s stores in a row were refused; check these ids: %s", self.job, self.answered[account],
                        self.limit, ", ".join(self.skipped[-self.limit:]))
        elif self.in_a_row[account] >= self.limit:
            self.dead.add(account)
            if isinstance(account, int):  # the platform_accounts id: show staff the login has expired
                from .db import mark_session_expired
                mark_session_expired(account, f"{self.job}: {self.in_a_row[account]} refusals in a row ({err})")
            log.error("%s: %s refusals in a row on this login; session probably expired, run `run.py zomato session`. "
                      "Its other stores are skipped this run.", self.job, self.in_a_row[account])

    def summary(self) -> None:
        if self.skipped:
            log.warning("%s: %s store(s) refused this run: %s", self.job, len(self.skipped), ", ".join(self.skipped))
