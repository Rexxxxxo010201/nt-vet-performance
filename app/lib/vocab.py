"""
Shared funding-stream vocabulary: the plain-English name for each
Funding_Source code, taken from the data dictionary, and the one-line
stream-key caption shown under every table that lists a funding stream.
Not derived from the data (no lookup table for this ships in app/data/) -
this just supplies display names, so every chart names streams the same way.
"""

FUNDING_STREAM_NAMES = {
    "11J": "General Recurrent",
    "11K": "User Choice",
    "11N": "VET in Schools (Urban)",
    "11V": "VET in Schools (Remote)",
    "FFT": "Fee-Free TAFE",
}

STREAM_KEY_CAPTION = (
    "Funding streams: 11J General Recurrent, 11K User Choice, 11N and 11V VET in Schools, "
    "FFT Fee-Free TAFE."
)
