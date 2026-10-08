"""
Shared privacy rule: what counts as a forbidden, identifier-like column
name. Used by both the data-privacy test (tests/test_data_privacy.py) and
the data-sync script (scripts/sync_app_data.py), so the two can never
drift apart - the sync script refuses to copy exactly what the test
would fail on.
"""

# Substrings checked case-insensitively against every column header.
FORBIDDEN_SUBSTRINGS = [
    "usi",
    "dob",
    "date_of_birth",
    "dateofbirth",
    "birth_date",
    "birthdate",
    "student_id",
    "studentid",
    "first_name",
    "firstname",
    "last_name",
    "lastname",
    "surname",
    "given_name",
    "address",
    "phone",
    "email",
    "tfn",
    "medicare",
]


def find_forbidden_columns(columns):
    """Return [(column, matched_substring), ...] for any column whose name
    (lowercased, spaces -> underscores) contains a forbidden substring."""
    offending = []
    for col in columns:
        col_lower = str(col).lower().replace(" ", "_")
        for forbidden in FORBIDDEN_SUBSTRINGS:
            if forbidden in col_lower:
                offending.append((col, forbidden))
    return offending
