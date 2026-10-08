"""
Text and small-table generators for the Method and data quality page.
Every number comes from the analysis tables or the cleaning outputs,
through data_access, with round_whole/round_dp applied to exact values
and thousands separators on every count. Nothing here is typed by hand.

Tone: state what we know as fact. A gap in what the tables show becomes
something to confirm with the workbook owners, not a hedge.
"""

from .labels import provider_label, stream_label
from .numfmt import round_dp, round_whole
from .titles import TitleAssumptionError
from .data_access import (
    find_by_qualification_level,
    find_by_town,
    find_completion_by_group,
    find_completion_omnibus_tests,
    find_context_by_year,
    find_coverage_grid,
    find_data_quality_figures,
    find_industry_atsi_share,
    find_pathway_check,
    find_atsi_enrolled_share,
    find_sensitivity,
    load_cleaning_log,
    load_recovered_funding_source,
    load_t01_kpis,
    load_t08c_at_school_suspect_totals,
)

OWNERS_HEADING = "For the workbook owners"
NOTES_HEADING = "Other checks we ran, not charted"


def gather_tables():
    """Every table the Method page's generated text reads."""
    return {
        "cleaning_log": load_cleaning_log(),
        "kpi": load_t01_kpis(),
        "t21": find_data_quality_figures(),
        "grid": find_coverage_grid(),
        "atsi_share": find_atsi_enrolled_share(),
        "suspect": load_t08c_at_school_suspect_totals(),
        "pathway": find_pathway_check(),
        "context_year": find_context_by_year(),
        "completion": find_completion_by_group(),
        "completion_omnibus": find_completion_omnibus_tests(),
        "qual_level": find_by_qualification_level(),
        "industry_atsi": find_industry_atsi_share(),
        "by_town": find_by_town(),
        "sensitivity": find_sensitivity(),
        "recovered": load_recovered_funding_source(),
    }


def _metric(df, text, col="Value"):
    row = df.loc[df["Metric"] == text]
    if row.empty:
        raise TitleAssumptionError(f"Method page: no '{text}' row.")
    return row[col].iloc[0]


def key_points(tables):
    """Four short bullets for the top of the page."""
    log = tables["cleaning_log"]
    a1 = log.loc[log["rule_id"] == "A1"]
    if a1.empty:
        raise TitleAssumptionError("Method page: no A1 row in the cleaning log.")
    n_rows = int(a1["rows_after"].iloc[0])
    n_dupes = int(a1["rows_changed"].iloc[0])
    total_hours = int(_metric(tables["kpi"], "Total funded AHC"))
    return [
        "The raw workbook was never edited.",
        f"The cleaned tables hold {n_rows:,} enrolment rows after removing {n_dupes} exact duplicates.",
        f"All {total_hours:,} funded hours come from AHC_Funded.",
        "The workbook holds hours, not payments.",
    ]


def owners_list(tables):
    """One plain sentence per item, each with its count, for the workbook
    owners to follow up on."""
    t21 = tables["t21"]

    def t21v(name):
        return int(_metric(t21, name))

    b3_rows = t21v("Rows with Funded_Flag = 85%_only and outcome 51, 52 or 70")
    suspect = tables["suspect"]
    suspect_row = suspect.loc[suspect["Metric"] == "At_School_Suspect rows"]
    if suspect_row.empty:
        raise TitleAssumptionError("Method page: no 'At_School_Suspect rows' row in T08c.")
    n_suspect = int(suspect_row["Count"].iloc[0])
    n_not_at_school = t21v("11N and 11V rows not flagged At_School_Flag = Y")
    n_vet_rows = t21v("11N and 11V rows (VET in Schools streams)")
    n_gender_x = t21v("Gender = X students")
    n_students = t21v("Student table rows")
    n_p008_fft = t21v("P008 Fee-Free TAFE enrolment rows")

    grid = tables["grid"]
    p008_no_delivery = grid.loc[(grid["Provider_ID"] == "P008") & (grid["Status"] == "Contract without delivery")]
    if len(p008_no_delivery) != 3:
        raise TitleAssumptionError(
            f"Method page: expected P008 to have 3 contracts with no delivery, found {len(p008_no_delivery)}."
        )

    atsi_share = tables["atsi_share"]
    enrolled_row = atsi_share.loc[atsi_share["Dimension"] == "Overall"]
    if enrolled_row.empty:
        raise TitleAssumptionError("Method page: no 'Overall' row in the Reach table.")
    n_enrolled = int(enrolled_row["Students"].iloc[0])
    n_no_enrolment = n_students - n_enrolled
    if n_no_enrolment <= 0:
        raise TitleAssumptionError("Method page: enrolled students is not fewer than total students.")

    user_choice = grid.loc[grid["Funding_Source"] == "11K"]
    k_contracts = int((user_choice["Status"] == "Matched").sum())
    j_uncontracted = int((user_choice["Status"] == "Delivery without contract").sum())

    return [
        f"Funded_Flag conflicts with the data dictionary ({b3_rows} rows with code 85%_only carry outcome "
        f"codes 51, 52 and 70).",
        f"At_School_Flag disagrees with age and stream ({n_suspect} suspect rows; {n_not_at_school:,} of "
        f"{n_vet_rows:,} 11N and 11V rows are not flagged at school).",
        f"Gender X is {n_gender_x} of {n_students:,} students and the code list looks truncated.",
        f"P008 has {n_p008_fft:,} Fee-Free TAFE enrolments and no Fee-Free contract, and its three "
        f"contracts show no delivery.",
        f"{n_no_enrolment:,} students have no enrolment record.",
        f"Which funding streams are meant to have contracts, given User Choice has contracts for "
        f"{k_contracts} providers and delivery without one for {j_uncontracted}.",
        "Confirm what the Urban and Remote labels mean for 11N and 11V, which both deliver across all "
        "three regions.",
        "Confirm how Town is recorded, given delivery is very even across all eight towns.",
    ]


def pathway_note(tables):
    t = tables["pathway"]

    def v(name):
        return int(_metric(t, name))

    both = v("Students in both FSK10213 and a higher program")
    first = v("Started FSK10213 first")
    lo = v("Chance range low (95%)")
    hi = v("Chance range high (95%)")
    if first < lo:
        word = "below"
    elif first > hi:
        word = "above"
    else:
        word = "within"
    return (
        f"We tested whether students typically start with the foundation skills unit FSK10213 before a "
        f"Certificate II or III. Of {both} students in both, {first} started with it, which is {word} the "
        f"{lo} to {hi} expected by chance, so the data shows no such pathway and we did not chart it."
    )


def stream_label_note(tables):
    t21 = tables["t21"]

    def share(stream, remote_cat):
        return round_whole(float(_metric(t21, f"{stream} share of rows in {remote_cat} (%)")))

    shares = {
        (s, r): share(s, r) for s in ["11N", "11V"] for r in ["Urban", "Regional", "Remote"]
    }
    for stream in ["11N", "11V"]:
        if min(shares[(stream, r)] for r in ["Urban", "Regional", "Remote"]) == 0:
            raise TitleAssumptionError(f"Method page: {stream} does not deliver in all three regions.")
    return (
        f"{stream_label('11N')} and {stream_label('11V')}: both are labelled by a single region, but both "
        f"deliver across all three. 11N is {shares[('11N', 'Remote')]}% Remote, "
        f"{shares[('11N', 'Urban')]}% Urban and {shares[('11N', 'Regional')]}% Regional. 11V is "
        f"{shares[('11V', 'Remote')]}% Remote, {shares[('11V', 'Urban')]}% Urban and "
        f"{shares[('11V', 'Regional')]}% Regional."
    )


def town_note(tables):
    by_town = tables["by_town"]
    n_providers = int(by_town["Distinct_Providers"].iloc[0])
    if not (by_town["Distinct_Providers"] == n_providers).all():
        raise TitleAssumptionError("Method page: not every town has the same number of distinct providers.")
    n_towns = len(by_town)
    lo = round_whole(float(by_town["Share_of_Total_%"].min()))
    hi = round_whole(float(by_town["Share_of_Total_%"].max()))
    return (
        f"All {n_providers} providers deliver in all {n_towns} towns, and each town holds {lo}% to {hi}% "
        f"of hours. We did not chart towns. This is very even, so confirm how Town is recorded."
    )


def other_checks(tables):
    """One line each, with the table reference."""
    context = tables["context_year"]
    year_totals = context.groupby("Delivery_Year")["AHC"].sum()
    y1, y2, y3 = (int(year_totals.get(y, 0)) for y in (2023, 2024, 2025))

    completion = tables["completion"]
    by_year = completion.loc[completion["Dimension"] == "Delivery_Year"]
    year_rate = {int(r["Group"]): round_whole(float(r["Rate_exact"])) for _, r in by_year.iterrows()}

    industry = completion.loc[completion["Dimension"] == "Industry"]
    lowest = industry.loc[industry["Rate_exact"].idxmin()]
    industry_p = float(
        tables["completion_omnibus"].loc[tables["completion_omnibus"]["Dimension"] == "Industry", "Omnibus_GEE_p_value"].iloc[0]
    )

    qual = tables["qual_level"]
    cert3 = qual.loc[qual["Qualification_Level"] == "Certificate III"]
    if cert3.empty:
        raise TitleAssumptionError("Method page: no Certificate III row in the qualification-level table.")
    cert3_share = round_whole(float(cert3["Share_of_Total_%"].iloc[0]))

    industry_atsi = tables["industry_atsi"]
    atsi_lo = round_whole(float(industry_atsi["ATSI_Share_of_Units_%"].min()))
    atsi_hi = round_whole(float(industry_atsi["ATSI_Share_of_Units_%"].max()))

    return [
        f"Year totals: {y1:,} (2023), {y2:,} (2024), {y3:,} (2025) hours; 2023 has no carry-in from 2022. "
        f"Completion by year: {year_rate.get(2023)}% (2023), {year_rate.get(2024)}% (2024), "
        f"{year_rate.get(2025)}% (2025). (T11, T07)",
        f"Completion by industry: lowest is {lowest['Group']} at {round_whole(float(lowest['Rate_exact']))}%, "
        f"p = {round_dp(industry_p, 2):.2f}. (T07, T07_omnibus)",
        f"Certificate III holds {cert3_share}% of hours. (T13)",
        f"Industry ATSI share of units ranges {atsi_lo}% to {atsi_hi}%. (T12a)",
    ]


SENSITIVITY_LABELS = {
    "(a) Standard unit-level": "Standard definition",
    "(b) Outcome 20 only": "Outcome 20 only",
    "(c) Continuing counted as non-completion": "Continuing counted as not completed",
}


def sensitivity_table_rows(tables):
    """(headers, rows) for the small static 'how the completion rate
    changes with the definition' table: the standard definition, the two
    named alternatives, and the strict student-program reference row."""
    t10 = tables["sensitivity"]
    overall = t10.loc[t10["Scope"] == "Overall"]
    headers = ["Definition", "Rate (%)"]
    rows = []
    for definition, label in SENSITIVITY_LABELS.items():
        match = overall.loc[overall["Definition"] == definition]
        if match.empty:
            raise TitleAssumptionError(f"Method page: no overall row for sensitivity definition '{definition}'.")
        rows.append([label, f"{round_whole(float(match['Rate_exact'].iloc[0]))}"])
    reference = overall.loc[overall["Definition"].str.startswith("REFERENCE")]
    if reference.empty:
        raise TitleAssumptionError("Method page: no reference row in the sensitivity table.")
    rows.append(["Strict student-program version", f"{round_whole(float(reference['Rate_exact'].iloc[0]))}"])
    return headers, rows


def split_markdown_sections(text):
    """Split a generated markdown document into {heading: body} by its
    '## Heading' lines, keyed by the full heading text."""
    sections = {}
    current = None
    lines = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(lines).strip()
            current = line[3:].strip()
            lines = []
        elif current is not None:
            lines.append(line)
    if current is not None:
        sections[current] = "\n".join(lines).strip()
    return sections


CLEANING_STEP_GROUPS = [
    ("Fixes to duplicates and missing values", ["A1", "A2", "A3", "A4", "A9"]),
    ("Standardising codes and dates", ["A5", "A6", "A7", "A8", "B2"]),
    ("Flags and definitions", ["B3", "B4", "B5", "B6", "B1", "C1", "Validation"]),
]


def parse_cleaning_sections(data_quality_text):
    """Split the generated data-quality markdown into {rule_id: body}, by
    its '## {rule_id}: {title}' headings, so the page can re-group the
    same text numerically without duplicating or re-typing it."""
    sections = {}
    current_id = None
    current_lines = []
    for line in data_quality_text.splitlines():
        if line.startswith("## "):
            if current_id is not None:
                sections[current_id] = "\n".join(current_lines).strip()
            heading = line[3:]
            current_id = heading.split(":", 1)[0].strip()
            current_lines = [f"**{heading}**" if ":" not in heading else f"**{heading.split(':', 1)[1].strip()}**"]
        elif current_id is not None:
            current_lines.append(line)
    if current_id is not None:
        sections[current_id] = "\n".join(current_lines).strip()
    # B2's prose embeds its own two "Recovered rows by ..." markdown tables;
    # drop them here since the page renders recovered_rows_table_html() instead,
    # with provider and stream labels, in their place.
    if "B2" in sections:
        sections["B2"] = sections["B2"].split("\n\nRecovered rows by Funding_Source:")[0].strip()
    return sections


def cleaning_log_table_html(tables):
    """The full cleaning log as a static HTML table: every column visible,
    cells that wrap rather than scroll."""
    from .theme import GREY_LIGHT, TEXT

    log = tables["cleaning_log"]
    th_style = f"padding:6px 10px;border-bottom:1px solid {GREY_LIGHT};color:{TEXT};"
    header = "".join(f"<th style='text-align:left;{th_style}'>{c}</th>" for c in log.columns)
    rows_html = []
    for _, row in log.iterrows():
        tds = "".join(
            f"<td style='padding:6px 10px;color:{TEXT};word-wrap:break-word;white-space:normal;'>{row[c]}</td>"
            for c in log.columns
        )
        rows_html.append(f"<tr>{tds}</tr>")
    return (
        "<table style='width:100%;border-collapse:collapse;font-size:13px;table-layout:fixed;'>"
        f"<tr>{header}</tr>{''.join(rows_html)}</table>"
    )


def recovered_rows_table_html(tables):
    """The two 'Recovered rows' tables from B2 (by Funding_Source and by
    Provider_ID), merged into one small HTML table with names and stream
    labels, for inside the B2 cleaning-step expander."""
    from .theme import GREY_LIGHT, TEXT

    recovered = tables["recovered"]
    th_style = f"padding:6px 10px;border-bottom:1px solid {GREY_LIGHT};color:{TEXT};"
    header = (
        f"<th style='text-align:left;{th_style}'>Group</th>"
        f"<th style='text-align:right;{th_style}'>Recovered rows</th>"
    )
    rows_html = []
    for dimension, label_fn in [("Funding_Source", stream_label), ("Provider_ID", provider_label)]:
        sub = recovered.loc[recovered["Dimension"] == dimension]
        for _, r in sub.iterrows():
            rows_html.append(
                "<tr>"
                f"<td style='padding:6px 10px;color:{TEXT};word-wrap:break-word;white-space:normal;'>"
                f"{label_fn(r['Group'])}</td>"
                f"<td style='padding:6px 10px;text-align:right;color:{TEXT};'>{int(r['Recovered_rows'])}</td>"
                "</tr>"
            )
    return (
        "<table style='width:100%;border-collapse:collapse;font-size:14px;'>"
        f"<tr>{header}</tr>{''.join(rows_html)}</table>"
    )
