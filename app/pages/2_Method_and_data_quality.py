"""
Method and data quality page: what we did to the data, what we checked,
and what to raise with the workbook owners. Renders the cleaning and
analysis documentation written during the cleaning and analysis phases,
plus the cleaning log as a table, so a reader can check sources without
leaving the app.

Heading levels: one H1 (the page title, via st.title), every section
below it H2, and the individual cleaning-rule headings inside the
closed expanders H3 - so the page never carries two H1s, even though
the generated markdown documents each start with their own "# ..." line
(stripped here) and headings that would otherwise collide.
"""

import streamlit as st

from lib.data_access import (
    load_analysis_methods_text,
    load_data_quality_summary_text,
)
from lib.method_page import (
    CLEANING_STEP_GROUPS,
    NOTES_HEADING,
    OWNERS_HEADING,
    cleaning_log_table_html,
    gather_tables,
    key_points,
    other_checks,
    owners_list,
    parse_cleaning_sections,
    pathway_note,
    recovered_rows_table_html,
    sensitivity_table_rows,
    split_markdown_sections,
    stream_label_note,
    town_note,
)
from lib.theme import configure_page

configure_page("NT VET Performance - Method and data quality")

st.title("Method and data quality")
st.caption("What we did to the data, what we checked, and what to raise with the workbook owners.")

tables = gather_tables()

# ----------------------------------------------------------------------
# 1. Key points
# ----------------------------------------------------------------------
st.markdown("## Key points")
st.markdown("\n".join(f"- {point}" for point in key_points(tables)))

# ----------------------------------------------------------------------
# 2. For the workbook owners
# ----------------------------------------------------------------------
st.markdown(f"## {OWNERS_HEADING}")
st.markdown("\n".join(f"{i}. {item}" for i, item in enumerate(owners_list(tables), start=1)))

# ----------------------------------------------------------------------
# 3. Notes moved from the briefing (round 2 section, edited in place)
# ----------------------------------------------------------------------
st.markdown("## Notes moved from the briefing")
st.markdown(
    "- Results are for the data as supplied.\n"
    "- The workbook may not hold every contract.\n"
    "- ATSI means Aboriginal and Torres Strait Islander. Status is as recorded in the workbook, after "
    "standardising the codes in cleaning.\n"
    "- Each student counts once within a group, so one student can appear in several groups."
)

# ----------------------------------------------------------------------
# 4. Definitions used throughout, in plain words
# ----------------------------------------------------------------------
methods_sections = split_markdown_sections(load_analysis_methods_text())

st.markdown("## Definitions used throughout")
st.markdown(methods_sections["Core definitions (apply to every table)"])

# ----------------------------------------------------------------------
# 5. How the completion rate changes with the definition
# ----------------------------------------------------------------------
st.markdown("## How the completion rate changes with the definition")
st.markdown(
    "The standard definition is used throughout; the table shows how much the choice matters."
)
headers, rows = sensitivity_table_rows(tables)
_th = "".join(f"<th style='text-align:left;padding:6px 10px;border-bottom:1px solid #D9DCE0;'>{h}</th>" for h in headers)
_rows_html = "".join(
    "<tr>" + "".join(f"<td style='padding:6px 10px;'>{c}</td>" for c in r) + "</tr>" for r in rows
)
st.markdown(
    f"<table style='width:100%;border-collapse:collapse;font-size:14px;color:#1F2933;'>"
    f"<tr>{_th}</tr>{_rows_html}</table>",
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# 6. Other checks we ran, not charted
# ----------------------------------------------------------------------
st.markdown(f"## {NOTES_HEADING}")
st.markdown(pathway_note(tables))
st.markdown(stream_label_note(tables))
st.markdown(town_note(tables))
st.markdown("\n".join(f"- {line}" for line in other_checks(tables)))

# ----------------------------------------------------------------------
# 7. Statistical methods in plain words
# ----------------------------------------------------------------------
st.markdown("## Statistical methods in plain words")
st.markdown(methods_sections["Statistical methods in plain words"], unsafe_allow_html=True)

# ----------------------------------------------------------------------
# 8. Judgement calls
# ----------------------------------------------------------------------
st.markdown("## Judgement calls")
st.markdown(methods_sections["Judgement calls (stated, not silently assumed)"])

# ----------------------------------------------------------------------
# 9. Cleaning steps, grouped into three closed expanders
# ----------------------------------------------------------------------
st.markdown("## Cleaning steps")
cleaning_sections = parse_cleaning_sections(load_data_quality_summary_text())

for group_title, rule_ids in CLEANING_STEP_GROUPS:
    with st.expander(group_title, expanded=False):
        for rule_id in rule_ids:
            st.markdown(f"### {rule_id}")
            st.markdown(cleaning_sections[rule_id])
            if rule_id == "B2":
                st.markdown("**Recovered rows**")
                st.markdown(recovered_rows_table_html(tables), unsafe_allow_html=True)

# ----------------------------------------------------------------------
# 10. Cleaning log
# ----------------------------------------------------------------------
st.markdown("## Cleaning log")
with st.expander("Show the cleaning log", expanded=False):
    st.markdown(cleaning_log_table_html(tables), unsafe_allow_html=True)
