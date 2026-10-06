"""Durable, conservative monthly accounting in integer micro-BRL."""
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
from zoneinfo import ZoneInfo


class BudgetBlocked(RuntimeError):
    pass


def money(value: str, fx: str = "1") -> int:
    if not isinstance(value, str) or not isinstance(fx, str):
        raise ValueError("Money and FX must be decimal strings")
    amount, rate = Decimal(value), Decimal(fx)
    if not amount.is_finite() or not rate.is_finite() or amount < 0 or rate <= 0:
        raise ValueError("Invalid money or FX")
    return int((amount * rate * 1_000_000).to_integral_value(rounding=ROUND_CEILING))


def month() -> str:
    return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m")


class BudgetController:
    LIMIT = 50_000_000

    def __init__(self, path: Path, margin: str = "0.50"):
        self.path = path
        self.margin = money(margin)
        if self.margin >= self.LIMIT:
            raise ValueError("Margin must be below limit")
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS ledger (
                    id TEXT PRIMARY KEY, month TEXT NOT NULL, task TEXT NOT NULL,
                    provider TEXT NOT NULL, model TEXT NOT NULL,
                    currency TEXT NOT NULL, fx TEXT NOT NULL,
                    estimate INTEGER NOT NULL, actual INTEGER,
                    original_actual TEXT, status TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS controls (
                    name TEXT PRIMARY KEY, value INTEGER NOT NULL);
                INSERT OR IGNORE INTO controls VALUES ('tripped', 0);
            """)

    def connect(self):
        return sqlite3.connect(self.path, timeout=30, isolation_level=None)

    def _used(self, db):
        # Unresolved requests survive month rollover and process crashes.
        return db.execute("""SELECT COALESCE(SUM(CASE WHEN actual IS NULL
            THEN estimate ELSE actual END),0) FROM ledger
            WHERE month=? OR actual IS NULL""", (month(),)).fetchone()[0]

    @staticmethod
    def state_for(used: int) -> str:
        for threshold, state in [(50, "HARD_STOP"), (40, "EMERGENCY"),
                                 (25, "RED"), (10, "YELLOW")]:
            if used >= threshold * 1_000_000:
                return state
        return "GREEN"

    def snapshot(self):
        with closing(self.connect()) as db:
            used = self._used(db)
            tripped = bool(db.execute("SELECT value FROM controls").fetchone()[0])
            return {"used_micro_brl": used, "state": "HARD_STOP" if tripped else self.state_for(used)}

    def reserve(self, *, task: str, provider: str, model: str, estimate: str,
                currency: str = "BRL", fx: str = "1", essential=False,
                escalated=False, advantage=False) -> str:
        if currency == "BRL" and Decimal(fx) != 1:
            raise ValueError("BRL requires FX=1")
        units = money(estimate, fx)
        if units == 0:
            raise ValueError("Paid reservations require a positive upper bound")
        with closing(self.connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                used = self._used(db)
                state = self.state_for(used)
                if db.execute("SELECT value FROM controls").fetchone()[0]:
                    raise BudgetBlocked("Ledger tripped")
                if used + units + self.margin > self.LIMIT:
                    raise BudgetBlocked("Monthly hard ceiling or safety margin")
                if (state == "EMERGENCY" and not essential or
                    state == "RED" and not escalated or
                    state == "YELLOW" and not advantage):
                    raise BudgetBlocked(f"{state} policy")
                key = uuid.uuid4().hex
                db.execute("INSERT INTO ledger VALUES (?,?,?,?,?,?,?,?,NULL,NULL,'reserved')",
                           (key, month(), task, provider, model, currency, fx, units))
                db.commit()
                return key
            except BaseException:
                db.rollback()
                raise

    def reconcile(self, key: str, actual: str):
        with closing(self.connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = db.execute("SELECT estimate,fx,actual FROM ledger WHERE id=?", (key,)).fetchone()
                if row is None:
                    raise KeyError(key)
                units = money(actual, row[1])
                if row[2] is not None:
                    if row[2] != units:
                        raise ValueError("Conflicting reconciliation")
                else:
                    db.execute("UPDATE ledger SET actual=?,original_actual=?,status='settled' WHERE id=?",
                               (units, actual, key))
                    if units > row[0]:
                        db.execute("UPDATE controls SET value=1 WHERE name='tripped'")
                db.commit()
            except BaseException:
                db.rollback()
                raise
