"""
NT VET Performance project - feasibility checks (read-only).

Reads data/clean/*.csv (never modifies them) and writes
outputs/feasibility_checks.md. Every check is numbers-only: counts, shares,
means/medians/maxes. No conclusions beyond the numbers, and every section
states the assumption it relies on where one was needed.

Privacy: this script never prints or writes USI, DOB, or any other
student-level row - only aggregate counts and derived statistics.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CLEAN_DIR = ROOT / "data" / "clean"
OUTPUTS_DIR = ROOT / "outputs"
OUT_PATH = OUTPUTS_DIR / "feasibility_checks.md"

LINES = []


def h1(text):
    LINES.append(f"# {text}")
    LINES.append("")


def h2(text):
    LINES.append(f"## {text}")
    LINES.append("")


def para(text):
    LINES.append(text)
    LINES.append("")


def assumption(text):
    LINES.append(f"*Assumption: {text}*")
    LINES.append("")


def means(text):
    LINES.append(f"**What this means for the analysis:** {text}")
    LINES.append("")


def table(headers, rows):
    LINES.append("| " + " | ".join(headers) + " |")
    LINES.append("|" + "|".join(["---"] * len(headers)) + "|")
    for r in rows:
        LINES.append("| " + " | ".join(str(c) for c in r) + " |")
    LINES.append("")


def fmt_num(x):
    if x is None or pd.isna(x):
        return "-"
    x = float(x)
    if abs(x - round(x)) < 1e-6:
        return f"{round(x):,}"
    return f"{x:,.1f}"


def fmt_pct(x):
    if pd.isna(x):
        return "-"
    return f"{x:.1f}%"


def student_program_key(df):
    return list(zip(df["Student_ID"], df["Provider_ID"], df["Program_ID"]))


def main():
    enr = pd.read_csv(CLEAN_DIR / "enrolment.csv")
    stu = pd.read_csv(CLEAN_DIR / "student.csv")
    recon = pd.read_csv(CLEAN_DIR / "contract_delivery_recon.csv")

    enr["_sp_key"] = student_program_key(enr)
    enr["_valid_start"] = pd.to_datetime(enr["Enrol_Start_Date"], errors="coerce")
    # Start_Date_Invalid rows already have a null Enrol_Start_Date (A7), so
    # _valid_start is null for them automatically; no extra filtering needed.

    eligible = enr[enr["In_Completion_Rate"] == True].copy()  # noqa: E712

    h1("Feasibility checks")
    para(
        "Read-only checks against `data/clean/`. No cleaned file is modified. No USI, DOB, or other "
        "student-level rows are shown below - every number is an aggregate count or statistic. "
        "\"Student-program\" means a distinct Student_ID + Provider_ID + Program_ID combination, as "
        "defined in the brief."
    )

    # ==================================================================
    # 1. Unit of analysis and cluster size
    # ==================================================================
    h2("1. Unit of analysis and cluster size")

    n_rows = len(enr)
    n_students = enr["Student_ID"].nunique()
    n_sp = enr["_sp_key"].nunique()
    table(
        ["Metric", "Count"],
        [
            ["Enrolment rows", fmt_num(n_rows)],
            ["Distinct students (with >=1 enrolment)", fmt_num(n_students)],
            ["Distinct student-programs", fmt_num(n_sp)],
        ],
    )

    rows_per_student = enr.groupby("Student_ID").size()
    rows_per_sp = enr.groupby("_sp_key").size()
    table(
        ["Distribution", "Mean", "Median", "Max"],
        [
            [
                "Rows per student",
                fmt_num(rows_per_student.mean()),
                fmt_num(rows_per_student.median()),
                fmt_num(rows_per_student.max()),
            ],
            [
                "Rows per student-program",
                fmt_num(rows_per_sp.mean()),
                fmt_num(rows_per_sp.median()),
                fmt_num(rows_per_sp.max()),
            ],
        ],
    )

    sp_outcome_nunique = eligible.groupby("_sp_key")["Outcome_Group"].nunique()
    n_sp_with_eligible = len(sp_outcome_nunique)
    n_sp_same_group = int((sp_outcome_nunique == 1).sum())
    share_same = 100 * n_sp_same_group / n_sp_with_eligible if n_sp_with_eligible else float("nan")
    table(
        ["Metric", "Count"],
        [
            ["Student-programs with >=1 completion-eligible unit", fmt_num(n_sp_with_eligible)],
            [
                "...of which every completion-eligible unit shares the same Outcome_Group",
                f"{fmt_num(n_sp_same_group)} ({fmt_pct(share_same)})",
            ],
        ],
    )
    assumption(
        "the share is computed over student-programs that have at least one completion-eligible unit "
        "(In_Completion_Rate = True); student-programs with zero completion-eligible units are excluded "
        "from this share rather than counted as vacuously consistent."
    )
    means(
        "Most student-programs have very few rows (see median above), so later checks that treat a "
        "student-program as one unit are not dominated by a handful of large clusters; where the same-"
        "Outcome_Group share is well below 100%, student-program-level completion needs the explicit "
        "\"all completion-eligible units Achieved\" rule used in sections 6 and 8, not a single row's "
        "Outcome_Group."
    )

    # ==================================================================
    # 2. Is 2025 a complete year?
    # ==================================================================
    h2("2. Is 2025 a complete year?")

    by_year = enr.groupby("Delivery_Year").agg(Rows=("Delivery_Year", "size"), AHC_Funded=("AHC_Funded", "sum"))
    by_year = by_year.reindex(sorted(by_year.index))
    table(
        ["Delivery_Year", "Rows", "AHC_Funded"],
        [[int(y), fmt_num(r["Rows"]), fmt_num(r["AHC_Funded"])] for y, r in by_year.iterrows()],
    )

    valid = enr[enr["_valid_start"].notna()].copy()
    valid["_year"] = valid["_valid_start"].dt.year
    valid["_month"] = valid["_valid_start"].dt.month
    month_year = (
        valid[valid["_year"].isin([2023, 2024, 2025])]
        .groupby(["_month", "_year"])
        .size()
        .unstack("_year", fill_value=0)
        .reindex(range(1, 13), fill_value=0)
    )
    month_year = month_year.reindex(columns=[y for y in [2023, 2024, 2025] if y in month_year.columns], fill_value=0)
    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    table(
        ["Start month"] + [str(y) for y in month_year.columns],
        [[month_names[m - 1]] + [fmt_num(month_year.loc[m, y]) for y in month_year.columns] for m in range(1, 13)],
    )

    max_valid_start = enr["_valid_start"].max()
    para(f"Max valid Enrol_Start_Date overall: **{max_valid_start.date().isoformat()}**")
    means(
        "If 2025's monthly start counts drop to (near) zero before December, or AHC_Funded for 2025 is "
        "noticeably lower than 2023/2024, any 2025 figure is an in-progress partial year and should be "
        "labelled as such rather than compared directly to the two completed years."
    )

    # ==================================================================
    # 3. Cell sizes for comparisons
    # ==================================================================
    h2("3. Cell sizes for comparisons")
    para(
        "All counts below are distinct student-programs among completion-eligible rows (In_Completion_Rate "
        "= True) only."
    )
    assumption(
        "Provider_ID is part of the student-program key, so its counts cannot double-count. "
        "Funding_Source, Remoteness, Industry and Delivery_Year are row-level attributes: if a single "
        "student-program has rows with more than one value of a given attribute, it is counted once in "
        "each value's cell for that attribute, so a column's cell counts can sum to more than the total "
        "number of distinct student-programs. ATSI is a student-level attribute (one value per student) "
        "so it does not have this issue."
    )

    elig_with_atsi = eligible.merge(stu[["Student_ID", "ATSI"]], on="Student_ID", how="left")

    def sp_counts_by(df, col):
        return df.drop_duplicates(subset=["_sp_key", col]).groupby(col)["_sp_key"].nunique().sort_index()

    univariate_specs = [
        ("Provider_ID", eligible),
        ("Funding_Source", eligible),
        ("Remoteness", eligible),
        ("Industry", eligible),
        ("ATSI", elig_with_atsi),
        ("Delivery_Year", eligible),
    ]

    for col, df in univariate_specs:
        counts = sp_counts_by(df, col)
        table(
            [col, "Student-programs"],
            [[val, fmt_num(c)] for val, c in counts.items()],
        )
        under_30 = int((counts < 30).sum())
        para(f"Cells with fewer than 30 student-programs: **{under_30}** of {len(counts)}.")

    def sp_counts_by_pair(df, col_a, col_b):
        dedup = df.drop_duplicates(subset=["_sp_key", col_a, col_b])
        return dedup.groupby([col_a, col_b])["_sp_key"].nunique()

    pair_specs = [
        ("Provider_ID", "Funding_Source", eligible),
        ("Remoteness", "ATSI", elig_with_atsi),
        ("Industry", "ATSI", elig_with_atsi),
    ]

    for col_a, col_b, df in pair_specs:
        counts = sp_counts_by_pair(df, col_a, col_b)
        pivot = counts.unstack(col_b, fill_value=0)
        table(
            [f"{col_a} \\ {col_b}"] + [str(c) for c in pivot.columns],
            [[idx] + [fmt_num(v) for v in row] for idx, row in pivot.iterrows()],
        )
        n_cells = pivot.shape[0] * pivot.shape[1]
        under_30 = int((pivot.values < 30).sum())
        n_zero = n_cells - counts.shape[0]
        para(
            f"Cells with fewer than 30 student-programs: **{under_30}** of {n_cells} possible combinations "
            f"(includes {n_zero} combination(s) with zero student-programs; {counts.shape[0]} combinations "
            f"actually occur in the data)."
        )

    means(
        "Any comparison that conditions on a cell flagged below 30 student-programs is working with a "
        "small-sample cell; stream-level and intersectional (pairwise) breakdowns have far more such "
        "cells than single-dimension breakdowns, which limits how finely results can be sliced."
    )

    # ==================================================================
    # 4. Funded hours by outcome
    # ==================================================================
    h2("4. Funded hours by outcome")

    overall_outcome = enr.groupby("Outcome_Group")["AHC_Funded"].sum().sort_values(ascending=False)
    overall_total = overall_outcome.sum()
    table(
        ["Outcome_Group", "AHC_Funded", "Share of total"],
        [
            [g, fmt_num(v), fmt_pct(100 * v / overall_total)]
            for g, v in overall_outcome.items()
        ],
    )

    by_fs_outcome = enr.groupby(["Funding_Source", "Outcome_Group"])["AHC_Funded"].sum()
    fs_totals = enr.groupby("Funding_Source")["AHC_Funded"].sum()
    rows = []
    for (fs, g), v in by_fs_outcome.items():
        rows.append([fs, g, fmt_num(v), fmt_pct(100 * v / fs_totals[fs])])
    rows.sort(key=lambda r: (r[0], -float(r[2].replace(",", ""))))
    table(["Funding_Source", "Outcome_Group", "AHC_Funded", "Share within Funding_Source"], rows)

    bad_funded_mask = enr["Outcome_Group"].isin(["Withdrawn", "Not achieved"]) & (enr["Funded_Flag"] == "Y")
    bad_rows = int(bad_funded_mask.sum())
    bad_ahc = int(enr.loc[bad_funded_mask, "AHC_Funded"].sum())
    table(
        ["Metric", "Value"],
        [
            ["Rows: Outcome_Group in (Withdrawn, Not achieved) AND Funded_Flag = Y", fmt_num(bad_rows)],
            ["AHC_Funded for those rows", fmt_num(bad_ahc)],
        ],
    )
    means(
        "AHC_Funded is concentrated in Achieved rows as expected; the rows flagged in the last table are "
        "where the funding-timing flag (Funded_Flag = Y, fully funded) and the training outcome "
        "(Withdrawn/Not achieved) point in different directions, so any funding-vs-outcome narrative "
        "should check this group rather than assume Funded_Flag tracks success."
    )

    # ==================================================================
    # 5. Delivery mix vs contract mix
    # ==================================================================
    h2("5. Delivery mix vs contract mix")

    matched = recon[(recon["Status"] == "Matched") & (recon["Target_Status"] != "No target set")].copy()
    assumption(
        "\"matched Provider_ID + Funding_Source pairs\" means Status = 'Matched' in "
        "contract_delivery_recon.csv, excluding the one pair with Target_Status = 'No target set' "
        "(DCVT-2020 / P007-11V), which has no usable target."
    )

    for col in ["Target_AHC_Urban", "Target_AHC_Regional", "Target_AHC_Remote", "Target_AHC_Total",
                "Delivered_AHC_Urban", "Delivered_AHC_Regional", "Delivered_AHC_Remote", "Delivered_AHC_2023_2025"]:
        matched[col] = pd.to_numeric(matched[col], errors="coerce")

    matched["Target_Urban_%"] = 100 * matched["Target_AHC_Urban"] / matched["Target_AHC_Total"]
    matched["Target_Regional_%"] = 100 * matched["Target_AHC_Regional"] / matched["Target_AHC_Total"]
    matched["Target_Remote_%"] = 100 * matched["Target_AHC_Remote"] / matched["Target_AHC_Total"]
    matched["Delivered_Urban_%"] = 100 * matched["Delivered_AHC_Urban"] / matched["Delivered_AHC_2023_2025"]
    matched["Delivered_Regional_%"] = 100 * matched["Delivered_AHC_Regional"] / matched["Delivered_AHC_2023_2025"]
    matched["Delivered_Remote_%"] = 100 * matched["Delivered_AHC_Remote"] / matched["Delivered_AHC_2023_2025"]
    matched["Delivered_pct_of_Target"] = 100 * matched["Delivered_AHC_2023_2025"] / matched["Target_AHC_Total"]

    table(
        ["Provider_ID", "Funding_Source", "Target Urban%", "Delivered Urban%", "Target Regional%",
         "Delivered Regional%", "Target Remote%", "Delivered Remote%"],
        [
            [
                r["Provider_ID"], r["Funding_Source"],
                fmt_pct(r["Target_Urban_%"]), fmt_pct(r["Delivered_Urban_%"]),
                fmt_pct(r["Target_Regional_%"]), fmt_pct(r["Delivered_Regional_%"]),
                fmt_pct(r["Target_Remote_%"]), fmt_pct(r["Delivered_Remote_%"]),
            ]
            for _, r in matched.sort_values(["Provider_ID", "Funding_Source"]).iterrows()
        ],
    )

    table(
        ["Provider_ID", "Funding_Source", "Delivered AHC as % of Target_AHC_Total"],
        [
            [r["Provider_ID"], r["Funding_Source"], fmt_pct(r["Delivered_pct_of_Target"])]
            for _, r in matched.sort_values(["Provider_ID", "Funding_Source"]).iterrows()
        ],
    )
    table(
        ["Statistic", "Delivered AHC as % of Target_AHC_Total"],
        [
            ["Min across matched pairs", fmt_pct(matched["Delivered_pct_of_Target"].min())],
            ["Median across matched pairs", fmt_pct(matched["Delivered_pct_of_Target"].median())],
            ["Max across matched pairs", fmt_pct(matched["Delivered_pct_of_Target"].max())],
        ],
    )

    matched_delivered_total = matched["Delivered_AHC_2023_2025"].sum()
    matched_target_total = matched["Target_AHC_Total"].sum()
    all_delivered_total = pd.to_numeric(recon["Delivered_AHC_2023_2025"], errors="coerce").sum()
    all_target_total = pd.to_numeric(recon["Target_AHC_Total"], errors="coerce").sum()
    table(
        ["Scope", "Total delivered AHC", "Total target AHC", "Delivered as % of target"],
        [
            [
                "Matched pairs only",
                fmt_num(matched_delivered_total),
                fmt_num(matched_target_total),
                fmt_pct(100 * matched_delivered_total / matched_target_total),
            ],
            [
                "All delivery vs all targets (every pair in the recon table)",
                fmt_num(all_delivered_total),
                fmt_num(all_target_total),
                fmt_pct(100 * all_delivered_total / all_target_total),
            ],
        ],
    )
    assumption(
        "\"all delivery vs all targets\" sums Delivered_AHC_2023_2025 and Target_AHC_Total across every "
        "row of contract_delivery_recon.csv, including 'Delivery without contract' and 'Contract without "
        "delivery' rows (nulls contribute 0 to the respective sum), not only matched pairs."
    )

    low_cell_mask = (
        (matched["Delivered_AHC_Urban"] < 100)
        | (matched["Delivered_AHC_Regional"] < 100)
        | (matched["Delivered_AHC_Remote"] < 100)
    )
    n_low_cell = int(low_cell_mask.sum())
    para(
        f"Matched pairs where at least one remoteness cell has Delivered AHC below 100 hours: "
        f"**{n_low_cell}** of {len(matched)}."
    )
    means(
        "Where the delivered-as-%-of-target figure is far from 100% or a remoteness cell has very few "
        "delivered hours, a provider/stream-level comparison of delivery against target is being driven "
        "by a thin slice of hours rather than a full year's activity."
    )

    # ==================================================================
    # 6. Adjusted equity gap feasibility
    # ==================================================================
    h2("6. Adjusted equity gap feasibility")

    sp_group = eligible.groupby("_sp_key").agg(
        n_eligible=("Outcome_Group", "size"),
        n_achieved=("Outcome_Group", lambda s: (s == "Achieved").sum()),
        Student_ID=("Student_ID", "first"),
    ).reset_index()
    sp_group["completed"] = sp_group["n_achieved"] == sp_group["n_eligible"]
    sp_group = sp_group.merge(stu[["Student_ID", "ATSI"]], on="Student_ID", how="left")

    by_atsi = sp_group.groupby("ATSI")["completed"].agg(
        Completed=lambda s: int(s.sum()), Non_completed=lambda s: int((~s).sum())
    )
    table(
        ["ATSI", "Completed student-programs", "Non-completed student-programs"],
        [[a, fmt_num(r["Completed"]), fmt_num(r["Non_completed"])] for a, r in by_atsi.iterrows()],
    )

    total_non_completions = int((~sp_group["completed"]).sum())
    para(
        f"Total non-completions (student-programs with >=1 completion-eligible unit, not all Achieved): "
        f"**{fmt_num(total_non_completions)}**."
    )
    assumption(
        "rule-of-thumb guidance of ~10 non-completion events per predictor is applied to the rarer "
        "outcome class (non-completion) since it is smaller than the completion class here."
    )

    def qualifies(df, key_col):
        counts = df.groupby([key_col, "ATSI"]).size().unstack("ATSI", fill_value=0)
        if "Y" not in counts.columns or "N" not in counts.columns:
            return 0
        return int(((counts.get("Y", 0) >= 30) & (counts.get("N", 0) >= 30)).sum())

    sp_group_with_program = eligible.drop_duplicates(subset=["_sp_key"])[["_sp_key", "Program_ID", "Provider_ID"]]
    sp_full = sp_group.merge(sp_group_with_program, on="_sp_key", how="left")

    n_programs_ok = qualifies(sp_full, "Program_ID")
    n_providers_ok = qualifies(sp_full, "Provider_ID")
    table(
        ["Grouping", "Qualifying groups (ATSI=Y and ATSI=N both >=30 student-programs)"],
        [
            ["Program_ID", fmt_num(n_programs_ok)],
            ["Provider_ID", fmt_num(n_providers_ok)],
        ],
    )
    means(
        "An ATSI-adjusted completion comparison is only statistically meaningful where both the event "
        "count (non-completions) and the group cell sizes above clear usual minimums; the qualifying-"
        "group counts above show how many programs/providers that applies to, not whether a gap exists."
    )

    # ==================================================================
    # 7. Pathways
    # ==================================================================
    h2("7. Pathways")

    def pathway_check(lower_ids, higher_ids, label):
        lower_ids = set(lower_ids)
        higher_ids = set(higher_ids)
        lower_rows = enr[enr["Program_ID"].isin(lower_ids)]
        higher_rows = enr[enr["Program_ID"].isin(higher_ids)]
        lower_students = set(lower_rows["Student_ID"])
        higher_students = set(higher_rows["Student_ID"])
        both = lower_students & higher_students
        n_both = len(both)

        lower_start = lower_rows[lower_rows["Student_ID"].isin(both)].groupby("Student_ID")["_valid_start"].min()
        higher_start = higher_rows[higher_rows["Student_ID"].isin(both)].groupby("Student_ID")["_valid_start"].min()
        start_df = pd.DataFrame({"lower": lower_start, "higher": higher_start}).dropna()
        n_lower_before_higher = int((start_df["lower"] < start_df["higher"]).sum())

        lower_achieved_students = set(
            lower_rows[(lower_rows["Student_ID"].isin(both)) & (lower_rows["Outcome_Group"] == "Achieved")][
                "Student_ID"
            ]
        )
        n_with_achieved_lower = len(lower_achieved_students & both)

        return n_both, len(start_df), n_lower_before_higher, n_with_achieved_lower

    cert2_3_pattern = r"Certificate (?:II|III)\b"
    cert2_3_programs = set(
        enr.loc[enr["Program_Name"].str.contains(cert2_3_pattern, regex=True, na=False), "Program_ID"].unique()
    )

    pathway_specs = [
        ("BSB20120 -> BSB30120", ["BSB20120"], ["BSB30120"]),
        ("CER30115 -> CER40115", ["CER30115"], ["CER40115"]),
        ("FSK10213 -> any Certificate II or III", ["FSK10213"], sorted(cert2_3_programs - {"FSK10213"})),
    ]

    rows = []
    for label, lower_ids, higher_ids in pathway_specs:
        n_both, n_with_dates, n_before, n_achieved = pathway_check(lower_ids, higher_ids, label)
        rows.append([label, fmt_num(n_both), f"{fmt_num(n_before)} (of {fmt_num(n_with_dates)} with valid dates)", fmt_num(n_achieved)])
    table(
        ["Pathway", "Students in both programs", "Lower started before higher", "...with >=1 Achieved unit in lower"],
        rows,
    )
    assumption(
        "\"started before\" compares each student's earliest valid Enrol_Start_Date in the lower program "
        "against their earliest valid Enrol_Start_Date in the higher program; students missing a valid "
        "start date in either program are excluded from that count (denominator shown in parentheses). "
        "For the FSK10213 pathway, 'any Certificate II or III' is identified from Program_Name containing "
        "'Certificate II' or 'Certificate III' and excludes FSK10213 itself (a Certificate I)."
    )
    para(f"Certificate II/III programs identified for the FSK10213 pathway: {', '.join(sorted(cert2_3_programs - {'FSK10213'}))}.")

    sp_by_student = enr.groupby("Student_ID")["Program_ID"].nunique()
    multi_program_students = sp_by_student[sp_by_student > 1].index
    n_multi_program = len(multi_program_students)
    providers_per_multi_student = enr[enr["Student_ID"].isin(multi_program_students)].groupby("Student_ID")[
        "Provider_ID"
    ].nunique()
    n_multi_program_multi_provider = int((providers_per_multi_student > 1).sum())
    table(
        ["Metric", "Count"],
        [
            ["Students with more than one distinct Program_ID", fmt_num(n_multi_program)],
            ["...of which span more than one Provider_ID", fmt_num(n_multi_program_multi_provider)],
        ],
    )
    means(
        "Low counts of students in both programs of a pair mean a pathway progression analysis for that "
        "pair would rest on a small sample; the multi-program/multi-provider counts show how often "
        "enrolment history is genuinely cross-program or cross-provider at all."
    )

    # ==================================================================
    # 8. Sensitivity of the completion rate
    # ==================================================================
    h2("8. Sensitivity of the completion rate")
    para(
        "Student-program level completion, for every definition below, uses the rule in the brief: a "
        "student-program counts as completed if ALL of its eligible units (as defined for that variant) "
        "are Achieved, and it must have at least one eligible unit to be in the population."
    )

    def completion_rate_table(eligible_mask_fn, achieved_mask_fn, df, label):
        d = df.copy()
        d["_eligible"] = eligible_mask_fn(d)
        d["_achieved"] = achieved_mask_fn(d) & d["_eligible"]

        rows_out = []

        def rate_for(subset, name):
            sub = subset[subset["_eligible"]]
            n_elig_units = len(sub)
            n_ach_units = int(sub["_achieved"].sum())
            unit_rate = 100 * n_ach_units / n_elig_units if n_elig_units else float("nan")

            sp = subset.groupby("_sp_key").agg(
                n_eligible=("_eligible", "sum"), n_achieved=("_achieved", "sum")
            )
            sp = sp[sp["n_eligible"] > 0]
            n_sp_pop = len(sp)
            n_sp_completed = int((sp["n_achieved"] == sp["n_eligible"]).sum())
            sp_rate = 100 * n_sp_completed / n_sp_pop if n_sp_pop else float("nan")

            rows_out.append(
                [name, fmt_pct(unit_rate), fmt_num(n_elig_units), fmt_pct(sp_rate), fmt_num(n_sp_pop)]
            )

        rate_for(d, "Overall")
        for fs in sorted(d["Funding_Source"].unique()):
            rate_for(d[d["Funding_Source"] == fs], fs)

        h2(f"8{label}")
        table(
            ["Scope", "Unit-level completion rate", "Eligible units", "Student-program-level completion rate",
             "Eligible student-programs"],
            rows_out,
        )

    # (a) standard
    completion_rate_table(
        eligible_mask_fn=lambda d: d["Outcome_Group"].isin(["Achieved", "Not achieved", "Withdrawn"]),
        achieved_mask_fn=lambda d: d["Outcome_Group"] == "Achieved",
        df=enr,
        label=" (a) Standard: Achieved / (Achieved + Not achieved + Withdrawn)",
    )
    assumption("\"Achieved\" uses Outcome_Group = 'Achieved', which already covers outcome codes 20, 51 and 52.")

    # (b) outcome 20 only, 51/52 excluded from both numerator and denominator
    completion_rate_table(
        eligible_mask_fn=lambda d: d["Outcome"].isin([20, 30, 40]),
        achieved_mask_fn=lambda d: d["Outcome"] == 20,
        df=enr,
        label=" (b) Outcome 20 only (RPL/credit transfer excluded from both numerator and denominator)",
    )

    # (c) Continuing included in denominator as non-completion
    completion_rate_table(
        eligible_mask_fn=lambda d: d["Outcome_Group"].isin(["Achieved", "Not achieved", "Withdrawn", "Continuing"]),
        achieved_mask_fn=lambda d: d["Outcome_Group"] == "Achieved",
        df=enr,
        label=" (c) Continuing included in the denominator as non-completion",
    )

    # (d) exclude Unknown and Funding_Source_Recovered rows, standard definition otherwise
    n_unknown = int((enr["Funding_Source"] == "Unknown").sum())
    n_recovered = int((enr["Funding_Source_Recovered"] == True).sum())  # noqa: E712
    df_d = enr[(enr["Funding_Source"] != "Unknown") & (enr["Funding_Source_Recovered"] != True)]  # noqa: E712
    completion_rate_table(
        eligible_mask_fn=lambda d: d["Outcome_Group"].isin(["Achieved", "Not achieved", "Withdrawn"]),
        achieved_mask_fn=lambda d: d["Outcome_Group"] == "Achieved",
        df=df_d,
        label=f" (d) Excluding Funding_Source = Unknown ({n_unknown} rows) and Funding_Source_Recovered rows ({n_recovered} rows)",
    )
    means(
        "Comparing (a) to (b)-(d) shows how much the headline completion rate moves under alternative, "
        "equally defensible definitions; if a Funding_Source's rate shifts by more than a point or two "
        "between variants, that stream's headline number is sensitive to the definition choice and "
        "should be reported with the definition stated explicitly."
    )

    # ==================================================================
    # Checks that could not be run
    # ==================================================================
    h2("Checks that could not be run")
    para("None. Every check specified in the brief was run against `data/clean/` as described above.")

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(LINES))
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
