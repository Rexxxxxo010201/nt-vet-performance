"""
Shared rounding for the app. round_whole() must be the only way any
module in app/lib turns a table value into a whole-number figure for a
title, caption, chart label or annotation (tests/test_titles.py
enforces this by scanning every module's source). round_dp() is the
same rule generalised to n decimal places, for the cases where the
writing standard calls for one decimal place instead of a whole
number (CLAUDE.md: "Where a difference between two figures is the
point of the chart... show those figures to one decimal place so the
displayed numbers add up").

round_whole() rounds half up on the value given to it (using Decimal
with ROUND_HALF_UP), but that is secondary to the real fix: every
caller must pass the full-precision ("exact") value from the source
table, never an already-rounded one-decimal display value. Rounding a
one-decimal display value again, even with a half-up rule, still gives
the wrong answer whenever the true value sits on the other side of
.5 from where the one-decimal rounding happened to land it - for
example a true rate of 59.4988% is stored as the one-decimal display
value 59.5, and 59.5 rounds up to 60 under any half-up rule, but the
true value rounds down to 59. There is no rounding rule that fixes
this after the fact; it has to be rounded from the original value.
"""

from decimal import ROUND_HALF_UP, Decimal


def round_whole(x):
    """Round x to the nearest whole number, half up, from whatever
    precision x is given at. Always pass the most precise value
    available (an *_exact column, or a value computed fresh from exact
    source data), never an already-rounded one-decimal display value."""
    return int(Decimal(str(float(x))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def round_dp(x, n):
    """Round x to n decimal places, half up, from whatever precision x
    is given at. Same rule as round_whole, generalised to n decimals:
    always pass the most precise value available, never an
    already-rounded display value at coarser precision than n."""
    quantum = Decimal("1").scaleb(-n)
    return float(Decimal(str(float(x))).quantize(quantum, rounding=ROUND_HALF_UP))
