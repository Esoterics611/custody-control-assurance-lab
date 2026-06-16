"""Injectable clock.

Business logic NEVER reads the wall clock directly. Engines receive timestamps as
inputs (e.g. ``TransactionRequest.submitted_at``). This module provides the single
seam where real time enters the system, plus a deterministic ``FixedClock`` for
tests and simulations.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

# A Clock is any zero-arg callable returning a POSIX epoch timestamp (seconds).
Clock = Callable[[], float]


def system_clock() -> float:
    """The one sanctioned wall-clock read. Used only at the I/O edge (API)."""
    return time.time()


@dataclass
class FixedClock:
    """Deterministic clock for tests/sims. Never advances on its own."""

    now: float = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> float:
        """Move time forward explicitly and return the new value."""
        self.now += seconds
        return self.now
