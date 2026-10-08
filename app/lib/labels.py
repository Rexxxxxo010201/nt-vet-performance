"""
Display-label helpers for provider and funding-stream codes shown in
app tables (never in charts, which keep the bare codes). Every table
that shows one of these codes goes through these two functions, so a
name or a stream label is never typed by hand at the call site.

provider_label() reads from the organisation-level T19 table (via
data_access), the only sanctioned source of provider names in the app;
stream_label() reads from the shared vocab lookup already used
elsewhere in the app.
"""

from .data_access import find_provider_names
from .titles import TitleAssumptionError
from .vocab import FUNDING_STREAM_NAMES


def provider_label(code: str) -> str:
    """'P002 TAFE NT' - raises if the code has no row, or a blank name,
    in the organisation table (T19)."""
    names = find_provider_names()
    row = names.loc[names["Provider_ID"] == code]
    if row.empty:
        raise TitleAssumptionError(f"labels.provider_label: no provider name found for code '{code}'.")
    name = str(row["Provider_Name"].iloc[0]).strip()
    if not name:
        raise TitleAssumptionError(f"labels.provider_label: provider '{code}' has a blank name.")
    return f"{code} {name}"


def stream_label(code: str) -> str:
    """'11J General Recurrent' - falls back to the bare code if it is
    not one of the five known funding streams."""
    return f"{code} {FUNDING_STREAM_NAMES.get(code, code)}"
