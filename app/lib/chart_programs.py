"""
Chart 4: What is being delivered. Two panels sharing one set of 10
program rows, ordered by funded hours (largest at the top): student
counts on the left, share of funded hours on the right. The three
Community Services programs are ochre in both panels; the rest are mid
grey, so the same colour carries the same meaning in both panels.

Row labels (the short label in dark text, the industry beneath in
smaller grey text, with CER40115's short label in bold) are built as
annotations, not native y-axis tick labels, because a single tick
label cannot carry two different text styles or a one-off bold -
native tick labels only take one font/colour for the whole axis.

The program intensity table (t15) also carries two summary rows
("Community Services (3 programs)" and "Other 7 programs combined").
Those are told apart from the 10 real program rows by the one
structural fact that is actually true of the data: a real Program_ID
is a single code with no spaces, while both summary rows are written
as short phrases. Every number is pulled from app/data/ at call time.
The app is laptop-only: one fixed desktop layout.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .numfmt import round_dp, round_whole
from .theme import GREY_LIGHT, GREY_MID, OCHRE, OCHRE_LIGHT_TINT, TEXT
from .titles import TitleAssumptionError

CS_INDUSTRY = "Community Services"
CER40115_PROGRAM_ID = "CER40115"

# How close the nominal-hours-per-unit ratio must sit to the AHC-per-unit
# ratio, and how close the two groups' funded fractions must sit to each
# other, for the caption's "because the units are longer, not because of
# a higher funding rate" clause to be included (see build_caption).
CLAUSE_RATIO_RELATIVE_TOLERANCE = 0.15
CLAUSE_FRACTION_TOLERANCE_PP = 5

ROW_HEIGHT = 45  # about 40% taller than the original 32, so each row's
# two-line label (program name, industry beneath) has clear space above
# and below it before the next row's label starts.
BAR_GAP = 0.35  # fraction of each row's band left empty between bars
TOP_MARGIN = 40  # room for the two panel headers (Plotly subplot titles)
BOTTOM_MARGIN = 10
LEFT_MARGIN = 190  # room for the two-line row label (short label + industry)
RIGHT_MARGIN = 20
HORIZONTAL_SPACING = 0.14
AXIS_HEADROOM = 1.4  # extra range beyond the largest bar, for the outside end label


def _program_rows(t15):
    """The 10 individual program rows, told apart from the 2 summary
    rows by Program_ID having no space in it (see module docstring)."""
    programs = t15.loc[~t15["Program_ID"].astype(str).str.contains(" ")].copy()
    if len(programs) != 10:
        raise TitleAssumptionError(
            f"What is being delivered: expected 10 individual program rows in the intensity table; "
            f"got {len(programs)}."
        )
    return programs


def _summary_rows(t15):
    """The 2 summary rows, split into the Community Services summary
    and the 'other programs' summary."""
    summary = t15.loc[t15["Program_ID"].astype(str).str.contains(" ")]
    if len(summary) != 2:
        raise TitleAssumptionError(
            f"What is being delivered: expected 2 summary rows in the intensity table; got {len(summary)}."
        )
    cs = summary.loc[summary["Industry"] == CS_INDUSTRY]
    other = summary.loc[summary["Industry"] != CS_INDUSTRY]
    if len(cs) != 1 or len(other) != 1:
        raise TitleAssumptionError(
            "What is being delivered: could not identify exactly one Community Services summary row "
            "and one 'other programs' summary row."
        )
    return cs.iloc[0], other.iloc[0]


def _top3_by_funded_hours(t15):
    programs = _program_rows(t15)
    return programs.sort_values("AHC_Funded", ascending=False).head(3)


def _rows(t15, program_labels_df=None):
    """One dict per program, in funded-hours order (largest first) -
    the single row order shared by both panels."""
    programs = _program_rows(t15).sort_values("AHC_Funded", ascending=False)
    total_ahc = float(programs["AHC_Funded"].sum())
    full_labels = {}
    if program_labels_df is not None:
        full_labels = program_labels_df.set_index("Program_ID")["Full_Label"].to_dict()
    rows = []
    for _, r in programs.iterrows():
        rows.append(
            {
                "program_id": r["Program_ID"],
                "short_label": r["Short_Label"],
                "full_label": full_labels.get(r["Program_ID"], r["Short_Label"]),
                "industry": r["Industry"],
                "students": int(r["Distinct_Students"]),
                "units": int(r["Units"]),
                "ahc_funded": int(r["AHC_Funded"]),
                "share": float(r["Share_of_Total_%"]),
                # AHC_Funded is an exact integer, so the share is recomputed fresh from it
                # rather than rounding the one-decimal Share_of_Total_% column.
                "share_exact": 100 * float(r["AHC_Funded"]) / total_ahc,
                "is_cs": r["Industry"] == CS_INDUSTRY,
            }
        )
    return rows


def _row_label_html(row):
    short = f"<b>{row['short_label']}</b>" if row["program_id"] == CER40115_PROGRAM_ID else row["short_label"]
    return f"{short}<br><span style='color:{GREY_MID};font-size:11px'>{row['industry']}</span>"


def build_figure(t15, program_labels_df=None):
    """Build the two-panel figure (one fixed desktop layout)."""
    rows = _rows(t15, program_labels_df)
    labels = [r["short_label"] for r in rows]
    colors = [OCHRE if r["is_cs"] else GREY_MID for r in rows]

    fig = make_subplots(
        rows=1,
        cols=2,
        shared_yaxes=True,
        horizontal_spacing=HORIZONTAL_SPACING,
        subplot_titles=("Students", "Share of funded hours"),
    )

    hover_customdata = [
        [r["full_label"], r["industry"], r["students"], r["units"], r["ahc_funded"], round_whole(r["share_exact"])]
        for r in rows
    ]
    hovertemplate = (
        "<b>%{customdata[0]}</b><br>%{customdata[1]}<br>%{customdata[2]:,} students, %{customdata[3]:,} units"
        "<br>%{customdata[4]:,} funded hours (%{customdata[5]}% of the total)<extra></extra>"
    )

    fig.add_trace(
        go.Bar(
            x=[r["students"] for r in rows],
            y=labels,
            orientation="h",
            marker_color=colors,
            marker_line_width=0,
            text=[f"{r['students']}" for r in rows],
            textposition="outside",
            textfont=dict(color=TEXT, size=12),
            cliponaxis=False,
            customdata=hover_customdata,
            hovertemplate=hovertemplate,
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=[r["share"] for r in rows],
            y=labels,
            orientation="h",
            marker_color=colors,
            marker_line_width=0,
            text=[f"{round_whole(r['share_exact'])}%" for r in rows],
            textposition="outside",
            textfont=dict(color=TEXT, size=12),
            cliponaxis=False,
            customdata=hover_customdata,
            hovertemplate=hovertemplate,
            showlegend=False,
        ),
        row=1,
        col=2,
    )

    # Row labels: one annotation per row, anchored at x=0 (the bars'
    # start) on the left panel's own x-axis so the text sits in the
    # reserved left margin, flush right against the bars.
    for r in rows:
        fig.add_annotation(
            x=0,
            y=r["short_label"],
            xref="x",
            yref="y",
            xanchor="right",
            yanchor="middle",
            xshift=-10,
            align="right",
            showarrow=False,
            text=_row_label_html(r),
            font=dict(size=13, color=TEXT),
        )

    max_students = max(r["students"] for r in rows)
    max_share = max(r["share"] for r in rows)

    fig.update_xaxes(visible=False, range=[0, max_students * AXIS_HEADROOM], fixedrange=True, row=1, col=1)
    fig.update_xaxes(visible=False, range=[0, max_share * AXIS_HEADROOM], fixedrange=True, row=1, col=2)
    fig.update_yaxes(
        visible=False,
        autorange="reversed",
        categoryorder="array",
        categoryarray=labels,
        fixedrange=True,
        row=1,
        col=1,
    )
    # yaxis2 "matches" yaxis (set by shared_yaxes=True) for range and
    # category order, but "visible" is not one of the matched
    # properties, so it must be hidden here too.
    fig.update_yaxes(visible=False, fixedrange=True, row=1, col=2)

    # The two subplot-title annotations that make_subplots added
    # ("Students", "Share of funded hours") get the small-header
    # treatment; row-label annotations are left untouched.
    for ann in fig.layout.annotations:
        if ann.text in ("Students", "Share of funded hours"):
            ann.font = dict(size=13, color=TEXT)

    fig.update_layout(
        height=TOP_MARGIN + ROW_HEIGHT * len(rows) + BOTTOM_MARGIN,
        margin=dict(l=LEFT_MARGIN, r=RIGHT_MARGIN, t=TOP_MARGIN, b=BOTTOM_MARGIN),
        bargap=BAR_GAP,
        showlegend=False,
    )
    return fig


def build_caption(t15, t16):
    """Build the two-paragraph caption (what we see, what it could
    mean). The caveat (how sure) is a fixed line rendered separately by
    chart_card, since that is where the muted-grey caveat style lives.

    The "because the units are longer, not because of a higher funding
    rate" clause, and the closing "so funded hours follow the length of
    the units delivered" sentence, are only included if the two
    groups' funded fractions differ by no more than 5 percentage
    points and the nominal-hours-per-unit ratio sits within 15% of the
    AHC-per-unit ratio; otherwise the paragraph states only the
    observed numbers and says the data cannot say why."""
    top3 = _top3_by_funded_hours(t15)
    # AHC_Funded is an exact integer, so the combined share is recomputed fresh from it
    # rather than summing the three rounded one-decimal Share_of_Total_% values.
    total_ahc = float(_program_rows(t15)["AHC_Funded"].sum())
    pct_exact = 100 * float(top3["AHC_Funded"].sum()) / total_ahc
    pct = round_whole(pct_exact)

    min_row = t16.loc[t16["Metric"].str.contains("minimum", case=False, regex=False)]
    max_row = t16.loc[t16["Metric"].str.contains("maximum", case=False, regex=False)]
    if min_row.empty or max_row.empty:
        raise TitleAssumptionError(
            "What is being delivered caption: the chance-check table is missing the observed "
            "minimum/maximum student-count row."
        )
    min_students = int(min_row["Value"].iloc[0])
    max_students = int(max_row["Value"].iloc[0])

    p_row = t16.loc[t16["Metric"].str.contains("Two-sided", case=False, regex=False)]
    if p_row.empty:
        raise TitleAssumptionError("What is being delivered caption: the chance-check table has no two-sided p-value row.")
    chance_p = float(p_row["Value"].iloc[0])
    chance_p_dp = round_dp(chance_p, 2)
    chance_n_in_100 = round_whole(chance_p * 100)

    paragraph1 = (
        f"**Student numbers are similar across the ten programs ({min_students} to {max_students} students "
        f"each).**"
    )
    stats_line = (
        f"For readers who want the statistics: p = {chance_p_dp:.2f}. If program size did not vary beyond "
        f"chance, a spread this wide would turn up about {chance_n_in_100} times in 100."
    )

    cs, other = _summary_rows(t15)
    # AHC_per_Unit is a one-decimal display column; the ratio and the two
    # per-unit figures shown below are recomputed fresh from the exact
    # AHC_Funded/Units integers, not from that already-rounded column.
    cs_ahc_per_unit_exact = float(cs["AHC_Funded"]) / float(cs["Units"])
    other_ahc_per_unit_exact = float(other["AHC_Funded"]) / float(other["Units"])
    ahc_ratio = cs_ahc_per_unit_exact / other_ahc_per_unit_exact
    ratio_phrase = "about twice" if 1.75 <= ahc_ratio <= 2.25 else f"{ahc_ratio:.1f} times"
    a = round_dp(cs_ahc_per_unit_exact, 1)
    b = round_dp(other_ahc_per_unit_exact, 1)

    nominal_ratio = float(cs["Mean_Nominal_Hours_per_Unit"]) / float(other["Mean_Nominal_Hours_per_Unit"])
    cs_fraction_pct = float(cs["Mean_Funded_Fraction"]) * 100
    other_fraction_pct = float(other["Mean_Funded_Fraction"]) * 100
    fraction_diff_pp = abs(cs_fraction_pct - other_fraction_pct)
    ratio_relative_diff = abs(nominal_ratio - ahc_ratio) / ahc_ratio
    explain_included = bool(
        fraction_diff_pp <= CLAUSE_FRACTION_TOLERANCE_PP and ratio_relative_diff <= CLAUSE_RATIO_RELATIVE_TOLERANCE
    )

    # Mean_Nominal_Hours_per_Unit and Mean_Funded_Fraction are rounded display
    # columns; the whole-number figures below round the *_exact companions once,
    # instead of rounding those already-rounded display values a second time.
    cs_hours = round_whole(float(cs["Mean_Nominal_Hours_per_Unit_exact"]))
    other_hours = round_whole(float(other["Mean_Nominal_Hours_per_Unit_exact"]))
    cs_fraction = round_whole(float(cs["Mean_Funded_Fraction_exact"]) * 100)
    other_fraction = round_whole(float(other["Mean_Funded_Fraction_exact"]) * 100)

    if explain_included:
        paragraph2 = (
            f"Community Services units carry {ratio_phrase} the funded hours of other units ({a:.1f} "
            f"against {b:.1f} funded hours per unit), because they are longer: about {cs_hours} nominal "
            f"hours against {other_hours} for other industries. This describes the hours and does not say "
            f"why units differ. The extra hours come from longer units, not from more students."
        )
    else:
        paragraph2 = (
            f"Their units carry {ratio_phrase} the funded hours of units in other programs (about "
            f"{cs_hours} hours against {other_hours} per unit, funded at {cs_fraction}% against "
            f"{other_fraction}% of scheduled hours). Why is not confirmed."
        )

    caption = f"{paragraph1}\n\n{paragraph2}"

    return caption, {
        "pct": pct,
        "min_students": min_students,
        "max_students": max_students,
        "ratio_phrase": ratio_phrase,
        "ahc_ratio": ahc_ratio,
        "explain_included": explain_included,
        "cs_hours": cs_hours,
        "other_hours": other_hours,
        "cs_fraction": cs_fraction,
        "other_fraction": other_fraction,
        "stats_line": stats_line,
    }


def build_table_takeaway(t15):
    """The lead line above the 'Show all 10 programs' table: the shading
    rule plus the funded-hours-per-unit range for the three Community
    Services programs against the other seven, from the table's own
    one-decimal AHC_per_Unit column."""
    programs = _program_rows(t15)
    cs_rows = programs.loc[programs["Industry"] == CS_INDUSTRY]
    other_rows = programs.loc[programs["Industry"] != CS_INDUSTRY]
    if len(cs_rows) != 3 or len(other_rows) != 7:
        raise TitleAssumptionError(
            f"What is being delivered table: expected 3 Community Services and 7 other programs; got "
            f"{len(cs_rows)} and {len(other_rows)}."
        )
    lo, hi = float(cs_rows["AHC_per_Unit"].min()), float(cs_rows["AHC_per_Unit"].max())
    lo2, hi2 = float(other_rows["AHC_per_Unit"].min()), float(other_rows["AHC_per_Unit"].max())
    return (
        f"Shaded: the three Community Services programs, with {lo:.1f} to {hi:.1f} funded hours per unit; "
        f"all other programs have {lo2:.1f} to {hi2:.1f}. Whole-number figures in the chart are rounded "
        f"from unrounded values, so they can differ slightly from the one-decimal figures here."
    )


def build_unit_length_note(t15):
    """Replaces the old fixed 'about three per program' caveat: the
    average distinct units per program, computed fresh from the table,
    not assumed to be three."""
    programs = _program_rows(t15)
    n = round_whole(float(programs["Distinct_Unit_IDs"].mean()))
    return (
        f"Unit lengths are averaged over the units delivered in the data (about {n} distinct units per "
        f"program), so they are not full qualification lengths."
    )


def build_cer40115_note(t15, program_labels_df):
    """The small-grey one-line note shown under the chart, before the
    caption: CER40115's full qualification name (from the program
    labels table), its student count and its share of funded hours
    (from the intensity table) - the row shown bold in the figure."""
    row = t15.loc[t15["Program_ID"] == CER40115_PROGRAM_ID]
    if row.empty:
        raise TitleAssumptionError("What is being delivered note: no CER40115 row in the program intensity table.")
    label_row = program_labels_df.loc[program_labels_df["Program_ID"] == CER40115_PROGRAM_ID]
    if label_row.empty:
        raise TitleAssumptionError("What is being delivered note: no CER40115 row in the program labels table.")

    students = int(row["Distinct_Students"].iloc[0])
    # AHC_Funded is an exact integer, so the share is recomputed fresh from it rather
    # than rounding the one-decimal Share_of_Total_% column.
    total_ahc = float(_program_rows(t15)["AHC_Funded"].sum())
    share_exact = 100 * float(row["AHC_Funded"].iloc[0]) / total_ahc
    share = round_whole(share_exact)
    full_label = label_row["Full_Label"].iloc[0]
    return f"Bold row: {full_label}, {students} students and {share}% of funded hours."


TABLE_HEADERS = [
    "Program",
    "Industry",
    "Students",
    "Units",
    "Funded hours",
    "Share of funded hours (%)",
    "Funded hours per unit",
]
TABLE_ALIGN = ["left", "left", "right", "right", "right", "right", "right"]


SHADING_TAKEAWAY = "Shaded: the three Community Services programs."


BAR_CELL_BAR_WIDTH_PCT = 60  # the bar's own block, as a share of the cell width


def _bar_cell(share_pct, max_share_pct, bar_color):
    """A two-part cell: the bar in its own fixed-width block (60% of the
    cell), proportional to share_pct on a fixed scale from zero to
    max_share_pct, then the number in a separate right-aligned span
    after it - so the number never sits on top of the bar, in any row."""
    width_pct = 100 * share_pct / max_share_pct if max_share_pct > 0 else 0
    return (
        "<div style='display:flex;align-items:center;'>"
        f"<div style='width:{BAR_CELL_BAR_WIDTH_PCT}%;'>"
        f"<div style='height:10px;width:{width_pct:.1f}%;background-color:{bar_color};"
        "border-radius:2px;'></div></div>"
        f"<span style='flex:1;text-align:right;color:{TEXT};'>{share_pct:.1f}</span>"
        "</div>"
    )


def build_table_html(t15, program_labels_df):
    """All 10 programs, sorted by funded hours, as a static HTML table
    for the 'Show all 10 programs' expander, with the three Community
    Services rows tinted light ochre (the stated rule) and a data bar in
    the share column - no inner scroll, so all 10 rows always show."""
    programs = _program_rows(t15).merge(
        program_labels_df[["Program_ID", "Full_Label"]], on="Program_ID", how="left", validate="one_to_one"
    )
    if programs["Full_Label"].isna().any():
        raise TitleAssumptionError("What is being delivered table: some programs have no matching Full_Label.")
    programs = programs.sort_values("AHC_Funded", ascending=False)
    max_share = float(programs["Share_of_Total_%"].max())

    th_style = f"padding:6px 10px;border-bottom:1px solid {GREY_LIGHT};color:{TEXT};"
    header_html = "".join(
        f"<th style='text-align:{align};{th_style}'>{h}</th>" for h, align in zip(TABLE_HEADERS, TABLE_ALIGN)
    )

    rows_html = []
    for _, row in programs.iterrows():
        is_cs = row["Industry"] == CS_INDUSTRY
        bg = f"background-color:{OCHRE_LIGHT_TINT};" if is_cs else ""
        bar_color = OCHRE if is_cs else GREY_LIGHT
        cells = [
            row["Full_Label"],
            row["Industry"],
            f"{int(row['Distinct_Students']):,}",
            f"{int(row['Units']):,}",
            f"{int(row['AHC_Funded']):,}",
            _bar_cell(float(row["Share_of_Total_%"]), max_share, bar_color),
            f"{row['AHC_per_Unit']:.1f}",
        ]
        tds = "".join(
            f"<td style='padding:6px 10px;text-align:{align};color:{TEXT};'>{cell}</td>"
            for cell, align in zip(cells, TABLE_ALIGN)
        )
        rows_html.append(f"<tr style='{bg}'>{tds}</tr>")

    return (
        "<table style='width:100%;border-collapse:collapse;font-size:14px;'>"
        f"<tr>{header_html}</tr>{''.join(rows_html)}</table>"
    )
