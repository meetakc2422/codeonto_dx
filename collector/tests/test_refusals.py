"""A login is called expired only when none of its stores answered, not because its first three stores in the list refused."""

import unittest
from unittest import mock

from core.refusals import Refusals


class RefusalsTests(unittest.TestCase):
    def setUp(self):
        self.mark = mock.patch("core.db.mark_session_expired").start()
        self.addCleanup(mock.patch.stopall)

    def run_stores(self, answers, account=7):
        """answers: one True (the login answered) or False (refused) per store, in order."""
        r = Refusals("zomato reviews")
        for i, ok in enumerate(answers):
            if r.is_dead(account):
                continue
            r.success(account) if ok else r.refused(account, f"store {i}", "Zomato session expired")
        r.summary()
        return r

    def test_three_refused_at_the_start_then_one_answers_is_not_expired(self):
        r = self.run_stores([False, False, False, True, True])
        self.mark.assert_not_called()
        self.assertFalse(r.is_dead(7))

    def test_every_store_refused_is_expired_at_the_end(self):
        r = self.run_stores([False] * 5)
        self.mark.assert_called_once()
        self.assertIn("5 refusals and no store answered", self.mark.call_args[0][1])
        self.assertTrue(r.is_dead(7))

    def test_a_long_run_of_refusals_with_no_answer_stops_the_login_early(self):
        r = self.run_stores([False] * 25)
        self.mark.assert_called_once()
        self.assertEqual(r.total[7], 10)  # the other 15 stores were skipped, not asked

    def test_one_or_two_refusals_alone_prove_nothing(self):
        self.run_stores([False, False])
        self.mark.assert_not_called()

    def test_each_login_is_judged_on_its_own(self):
        r = Refusals("zomato reviews")
        for _ in range(4):
            r.refused(1, "a store", "refused")  # login 1: nothing ever answers
        r.success(2)
        r.refused(2, "x", "refused"); r.refused(2, "y", "refused"); r.refused(2, "z", "refused")  # login 2: alive, three odd stores
        r.summary()
        self.mark.assert_called_once()
        self.assertEqual(self.mark.call_args[0][0], 1)

    def test_stores_no_login_owns_never_flag_a_login(self):
        r = Refusals("zomato reviews")
        for i in range(12):
            if not r.is_dead("unassigned"):
                r.refused("unassigned", f"orphan {i}", "refused")  # tried with the default login, but counted under "unassigned"
        r.summary()
        self.mark.assert_not_called()
        self.assertTrue(r.is_dead("unassigned"))  # still stops asking after a long run of refusals


if __name__ == "__main__":
    unittest.main()
