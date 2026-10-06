import concurrent.futures
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from zeroagent.budget import BudgetBlocked, BudgetController, money


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "budget.sqlite"
        self.budget = BudgetController(self.path, margin="0")

    def reserve(self, amount, **kwargs):
        return self.budget.reserve(task="t", provider="p", model="m", estimate=amount, **kwargs)

    def test_decimal_and_rounding(self):
        self.assertEqual(money("0.1"), 100000)
        self.assertEqual(money("0.0000001"), 1)
        self.assertEqual(money("2", "5.12"), 10240000)
        for value in ("-1", "NaN", "Infinity", 0.1):
            with self.assertRaises(ValueError):
                money(value)

    def test_hard_stop_at_exactly_fifty(self):
        reservation = self.reserve("50")
        self.budget.reconcile(reservation, "50")
        self.assertEqual(self.budget.snapshot()["state"], "HARD_STOP")
        with self.assertRaises(BudgetBlocked):
            self.reserve("0.000001", essential=True, escalated=True, advantage=True)

    def test_margin(self):
        budget = BudgetController(self.path)
        with self.assertRaises(BudgetBlocked):
            budget.reserve(task="t", provider="p", model="m", estimate="49.51")

    def test_reconciliation_and_idempotency(self):
        key = self.reserve("4", currency="USD", fx="5")
        self.budget.reconcile(key, "2")
        self.budget.reconcile(key, "2")
        self.assertEqual(self.budget.snapshot()["used_micro_brl"], 10000000)
        with self.assertRaises(ValueError):
            self.budget.reconcile(key, "3")

    def test_unexpected_charge_trips_and_records(self):
        key = self.reserve("1")
        self.budget.reconcile(key, "2")
        self.assertEqual(self.budget.snapshot(), {"state": "HARD_STOP", "used_micro_brl": 2000000})
        with self.assertRaises(BudgetBlocked):
            self.reserve("1")

    def test_restart_and_month_rollover_hold_ambiguous_reservations(self):
        with patch("zeroagent.budget.month", return_value="2026-09"):
            self.reserve("49")
        recovered = BudgetController(self.path, margin="0")
        self.assertEqual(recovered.snapshot()["used_micro_brl"], 49000000)
        with self.assertRaises(BudgetBlocked):
            recovered.reserve(task="next", provider="p", model="m", estimate="2", essential=True)

    def test_settled_prior_month_not_counted(self):
        with patch("zeroagent.budget.month", return_value="2026-09"):
            key = self.reserve("49")
            self.budget.reconcile(key, "49")
        self.assertEqual(self.budget.snapshot()["used_micro_brl"], 0)

    def test_transitions(self):
        for amount, state in [(0,"GREEN"), (10,"YELLOW"), (25,"RED"), (40,"EMERGENCY"), (50,"HARD_STOP")]:
            self.assertEqual(BudgetController.state_for(amount * 1000000), state)
        self.reserve("10")
        with self.assertRaises(BudgetBlocked):
            self.reserve("1")
        self.reserve("15", advantage=True)
        with self.assertRaises(BudgetBlocked):
            self.reserve("1", advantage=True)
        self.reserve("15", escalated=True)
        with self.assertRaises(BudgetBlocked):
            self.reserve("1", escalated=True)
        self.reserve("1", essential=True)

    def test_concurrent_reservations_cannot_overspend(self):
        def reserve(_):
            try:
                return self.reserve("3", advantage=True, escalated=True, essential=True)
            except BudgetBlocked:
                return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            reservations = list(pool.map(reserve, range(40)))
        self.assertEqual(sum(x is not None for x in reservations), 16)
        self.assertEqual(self.budget.snapshot()["used_micro_brl"], 48000000)

    def test_attribution(self):
        self.reserve("1")
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT task,provider,model,currency,fx FROM ledger").fetchone(),
                             ("t", "p", "m", "BRL", "1"))
