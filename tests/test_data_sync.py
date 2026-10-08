"""
app/data/ must be an exact, up-to-date copy of the whitelisted files in
outputs/ (see scripts/sync_app_data.py). This fails if a whitelisted
file has drifted from its source (meaning someone forgot to rerun the
sync after regenerating the analysis tables), or if app/data/ holds a
file that was never put there by the sync script.
"""

import filecmp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from sync_app_data import APP_DATA_DIR, FULL_WHITELIST, _source_path  # noqa: E402


def test_app_data_matches_whitelist_exactly():
    actual = set(p.name for p in APP_DATA_DIR.iterdir())
    whitelist = set(FULL_WHITELIST)
    extra = actual - whitelist
    missing = whitelist - actual
    assert not extra, f"app/data/ has file(s) not on the whitelist: {sorted(extra)}"
    assert not missing, f"app/data/ is missing whitelisted file(s) (run scripts/sync_app_data.py): {sorted(missing)}"


def test_app_data_files_match_their_source():
    stale = []
    for name in FULL_WHITELIST:
        src = _source_path(name)
        dst = APP_DATA_DIR / name
        if not dst.exists():
            continue  # reported by test_app_data_matches_whitelist_exactly
        if not src.exists() or not filecmp.cmp(src, dst, shallow=False):
            stale.append(name)
    assert not stale, f"app/data/ file(s) differ from their source in outputs/ (run scripts/sync_app_data.py): {stale}"
