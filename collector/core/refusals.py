"""When a platform refuses one store, skip it and carry on. A login is only called expired when NONE of its stores answered:
either a long run of refusals with no answer at all, or, at the end of the run, refusals and no answer. Three refusals at the start
used to be enough, so a login whose first stores in the list were ones it can't open (a wrong id, a store added under another login)
was flagged expired every run even though its session was fine and its other stores would have answered."""

from . import config as cfg
from .common import log


class Refusals:
    def __init__(self, job: str):
        self.job = job
        self.limit = cfg.integer("ZOMATO_REFUSALS_BEFORE_STOP", 3)
        self.dead_after = cfg.integer("ZOMATO_REFUSALS_BEFORE_DEAD", 10)  # refusals in a row, with no store answering, before the rest are skipped
        self.in_a_row: dict = {}
        self.total: dict = {}  # refusals per login this run
        self.last_error: dict = {}
        self.answered: dict = {}  # stores a login answered this run: proof the login itself is alive
        self.dead: set = set()
        self.skipped: list[str] = []

    def is_dead(self, account) -> bool:
        return account in self.dead

    def success(self, account) -> None:
        self.in_a_row[account] = 0
        self.answered[account] = self.answered.get(account, 0) + 1

    def refused(self, account, store: str, err) -> None:
        """Count a refusal. A login that has answered for other stores is alive: the refused ones are stores it may not open."""
        self.in_a_row[account] = self.in_a_row.get(account, 0) + 1
        self.total[account] = self.total.get(account, 0) + 1
        self.last_error[account] = err
        self.skipped.append(store)
        log.warning("%s %s: refused, skipping (%s)", self.job, store, err)
        if self.in_a_row[account] >= self.limit and self.answered.get(account):
            # other stores of this login answered, so it is alive: these stores are ones it may not open (a wrong id, one added to another login)
            self.in_a_row[account] = 0
            log.warning("%s: login is fine (%s stores answered) but %s stores in a row were refused; check these ids: %s", self.job, self.answered[account],
                        self.limit, ", ".join(self.skipped[-self.limit:]))
        elif self.in_a_row[account] == self.limit:
            log.warning("%s: %s refusals in a row and no store of this login has answered yet; trying its next stores before calling it expired", self.job, self.limit)
        elif self.in_a_row[account] >= self.dead_after:
            self._expire(account, err, f"{self.in_a_row[account]} refusals in a row")

    def _expire(self, account, err, what: str) -> None:
        if account in self.dead:
            return
        self.dead.add(account)
        if isinstance(account, int):  # the platform_accounts id: show staff the login has expired
            from .db import mark_session_expired
            mark_session_expired(account, f"{self.job}: {what} ({err})")
        log.error("%s: %s on this login and none of its stores answered; session probably expired, run `run.py zomato session`. "
                  "Its other stores are skipped this run.", self.job, what)

    def summary(self) -> None:
        # a login that was refused at least `limit` times and answered nothing all run is expired: that is only known at the end
        for account, n in self.total.items():
            if n >= self.limit and not self.answered.get(account):
                self._expire(account, self.last_error.get(account, ""), f"{n} refusals and no store answered")
        if self.skipped:
            log.warning("%s: %s store(s) refused this run: %s", self.job, len(self.skipped), ", ".join(self.skipped))
