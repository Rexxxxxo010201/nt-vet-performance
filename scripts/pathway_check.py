"""
NT VET Performance project - pathway verification (read-only).

Recomputes the FSK10213 -> higher-qualification pathway analysis entirely
from scratch against data/clean/enrolment.csv, without reusing any number
from earlier reports (feasibility_checks.md, analysis_summary.md, etc).
Writes outputs/pathway_check.md.

Privacy: every output is an aggregate count or a program-level list
(Program_ID/Program_Name are not student identifiers). No Student_ID,
USI, or other per-student row is printed or written anywhere.
"""

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CLEAN_DIR = ROOT / "data" / "clean"
OUTPUTS_DIR = ROOT / "outputs"
TABLES_DIR = OUTPUTS_DIR / "analysis_tables"

SEED = 42
N_PERMUTATIONS = 10000
LOWER_PROGRAM = "FSK10213"

LINES = []


def h(level, text):
    LINES.append(f"{'#' * level} {text}")
    LINES.append("")


def p(text):
    LINES.append(text)
    LINES.append("")


def table(headers, rows):
    LINES.append("| " + " | ".join(headers) + " |")
    LINES.append("|" + "|".join(["---"] * len(headers)) + "|")
    for r in rows:
        LINES.append("| " + " | ".join(str(c) for c in r) + " |")
    LINES.append("")


def earliest_start_per_student(df, student_col="Student_ID", date_col="_valid_start"):
    """Earliest valid start date per student, for rows already filtered to
    one program (or program group). Students with no valid date at all in
    these rows do not appear in the result (their earliest is undefined)."""
    valid = df[df[date_col].notna()]
    return valid.groupby(student_col)[date_col].min()


def earliest_start_row_per_student(df, student_col="Student_ID", date_col="_valid_start"):
    """Return, for each student, the row(s) matching their earliest valid
    start date in these (already program-filtered) rows. Used to resolve
    which provider a student's 'start' belongs to; ties are broken by the
    lexicographically smallest Provider_ID, stated as an assumption."""
    valid = df[df[date_col].notna()].copy()
    mins = valid.groupby(student_col)[date_col].min()
    valid = valid.merge(mins.rename("_min_date"), on=student_col)
    at_min = valid[valid[date_col] == valid["_min_date"]]
    # Deterministic tie-break: smallest Provider_ID.
    chosen = at_min.sort_values([student_col, "Provider_ID"]).groupby(student_col).first()
    return chosen


def pathway_block(enr, lower_ids, higher_ids, label, lines_out):
    """Computes items 2-3 (counts only, used for section 7's two extra
    pathways) and returns the key sets/series needed by callers that need
    more detail (the main FSK10213 pathway)."""
    lower_rows = enr[enr["Program_ID"].isin(lower_ids)]
    higher_rows = enr[enr["Program_ID"].isin(higher_ids)]

    lower_students = set(lower_rows["Student_ID"])
    higher_students = set(higher_rows["Student_ID"])
    both_students = lower_students & higher_students

    lower_start_all = earliest_start_per_student(lower_rows)
    higher_start_all = earliest_start_per_student(higher_rows)

    both_list = sorted(both_students)
    n_both = len(both_list)
    n_missing_lower_date = sum(1 for s in both_list if s not in lower_start_all.index)
    n_missing_higher_date = sum(1 for s in both_list if s not in higher_start_all.index)
    n_missing_either = sum(
        1 for s in both_list if s not in lower_start_all.index or s not in higher_start_all.index
    )

    both_with_dates = [s for s in both_list if s in lower_start_all.index and s in higher_start_all.index]
    lower_dates = lower_start_all.reindex(both_with_dates)
    higher_dates = higher_start_all.reindex(both_with_dates)

    n_lower_first = int((lower_dates < higher_dates).sum())
    n_same_date = int((lower_dates == higher_dates).sum())
    n_higher_first = int((lower_dates > higher_dates).sum())

    # Alternative definition: any higher-program row (not just the earliest)
    # starting after the student's lower-program start. Evaluated over
    # students-in-both who have a valid lower-program start date (needed as
    # the reference point); if all their higher-program dates are invalid,
    # the answer is "no" (not excluded), since there's no confirmed later row.
    alt_eligible = [s for s in both_list if s in lower_start_all.index]
    n_alt_missing_lower_date = n_both - len(alt_eligible)
    higher_rows_valid = higher_rows[higher_rows["_valid_start"].notna()]
    n_alt_after = 0
    for s in alt_eligible:
        ref = lower_start_all.loc[s]
        this_student_higher_dates = higher_rows_valid.loc[higher_rows_valid["Student_ID"] == s, "_valid_start"]
        if (this_student_higher_dates > ref).any():
            n_alt_after += 1

    h(3, label)
    table(
        ["Metric", "Count"],
        [
            [f"Distinct students with any {'/'.join(lower_ids)} enrolment", len(lower_students)],
            ["...of whom also have any enrolment in a higher program", f"{n_both} ({100*n_both/len(lower_students):.1f}% of lower-program learners)"],
        ],
    )
    table(
        ["Metric", "Count"],
        [
            ["Students in both, excluded from order comparison (missing valid date, either side)", n_missing_either],
            ["  - missing valid lower-program date", n_missing_lower_date],
            ["  - missing valid higher-program date", n_missing_higher_date],
            ["Students in both with valid dates on both sides (order comparison population)", len(both_with_dates)],
            ["Started lower program strictly first", n_lower_first],
            ["Started both on the same date", n_same_date],
            ["Started a higher program strictly first", n_higher_first],
        ],
    )
    table(
        ["Alternative definition", "Count"],
        [
            ["Students in both, excluded (missing valid lower-program date)", n_alt_missing_lower_date],
            ["Eligible for alternative check", len(alt_eligible)],
            ["...with any higher-program enrolment starting after their lower-program start", n_alt_after],
        ],
    )

    return {
        "lower_students": lower_students,
        "higher_students": higher_students,
        "both_students": both_students,
        "both_with_dates": both_with_dates,
        "lower_dates": lower_dates,
        "higher_dates": higher_dates,
        "n_lower_first": n_lower_first,
        "n_same_date": n_same_date,
        "n_higher_first": n_higher_first,
    }


def main():
    enr = pd.read_csv(CLEAN_DIR / "enrolment.csv")
    enr["_valid_start"] = pd.to_datetime(enr["Enrol_Start_Date"], errors="coerce")

    n_invalid_dates = int(enr["_valid_start"].isna().sum())

    h(1, "Pathway check: FSK10213 to higher qualifications")
    p(
        "Read-only verification against `data/clean/enrolment.csv` only, recomputed from scratch - no number "
        "here is taken from any earlier report. Every number below is an aggregate count; no Student_ID, USI, "
        "or other per-student row appears anywhere in this document."
    )

    h(2, "Definitions")
    p(
        "Work is at student level. Lower program = FSK10213. Higher programs = every Program_ID whose "
        "Program_Name contains 'Certificate II' or 'Certificate III' (matched with a word-boundary regex, so "
        "'Certificate III' is never counted as also matching 'Certificate II'). Only rows with a valid "
        "Enrol_Start_Date are used for any timing comparison; the 8 rows with an invalid (2030) start date "
        "are excluded from timing, same as in the cleaning step (A7), where they already carry a null "
        "Enrol_Start_Date. A student's start in a program is their earliest valid start date in that program."
    )
    p(f"Rows excluded from all timing comparisons for an invalid or missing Enrol_Start_Date: **{n_invalid_dates}**.")

    # ------------------------------------------------------------------
    # Higher-program identification
    # ------------------------------------------------------------------
    cert23_pattern = r"Certificate (?:II|III)\b"
    program_lookup = enr[["Program_ID", "Program_Name"]].drop_duplicates()
    higher_programs = program_lookup[
        program_lookup["Program_Name"].str.contains(cert23_pattern, regex=True, na=False)
    ].sort_values("Program_ID")
    higher_ids = sorted(set(higher_programs["Program_ID"]) - {LOWER_PROGRAM})

    if LOWER_PROGRAM in set(higher_programs["Program_ID"]):
        fsk_name = program_lookup.loc[program_lookup["Program_ID"] == LOWER_PROGRAM, "Program_Name"].iloc[0]
        p(
            f"Unexpected: {LOWER_PROGRAM} ('{fsk_name}') itself matched the Certificate II/III pattern and "
            f"was removed from the higher-program list; check this manually."
        )

    h(2, "Higher programs identified (Certificate II or III)")
    table(["Program_ID", "Program_Name"], higher_programs[["Program_ID", "Program_Name"]].values.tolist())

    # ------------------------------------------------------------------
    # Item 1: distinct FSK10213 students
    # ------------------------------------------------------------------
    fsk_rows = enr[enr["Program_ID"] == LOWER_PROGRAM]
    fsk_students = set(fsk_rows["Student_ID"])
    n_fsk_students = len(fsk_students)

    h(2, "1. FSK10213 learners")
    table(["Metric", "Count"], [["Distinct students with any FSK10213 enrolment", n_fsk_students]])

    # ------------------------------------------------------------------
    # Items 2-3: main FSK10213 -> Cert II/III pathway
    # ------------------------------------------------------------------
    h(2, "2-3. FSK10213 to any Certificate II or III")
    main = pathway_block(enr, [LOWER_PROGRAM], higher_ids, "FSK10213 -> any Certificate II or III", LINES)

    both_students = main["both_students"]
    n_both = len(both_students)
    share_both = 100 * n_both / n_fsk_students if n_fsk_students else float("nan")
    p(f"Students in both as a share of all FSK10213 learners: **{n_both} / {n_fsk_students} = {share_both:.1f}%**.")

    # ------------------------------------------------------------------
    # Item 4: achievement among FSK-first students
    # ------------------------------------------------------------------
    both_with_dates = main["both_with_dates"]
    lower_dates = main["lower_dates"]
    higher_dates = main["higher_dates"]
    fsk_first_students = set(s for s in both_with_dates if lower_dates.loc[s] < higher_dates.loc[s])

    fsk_rows_achieved = fsk_rows[(fsk_rows["Outcome_Group"] == "Achieved")]
    higher_rows_all = enr[enr["Program_ID"].isin(higher_ids)]
    higher_rows_achieved = higher_rows_all[(higher_rows_all["Outcome_Group"] == "Achieved")]

    fsk_achieved_students = set(fsk_rows_achieved["Student_ID"])
    higher_achieved_students = set(higher_rows_achieved["Student_ID"])

    n_fskfirst_achieved_lower = len(fsk_first_students & fsk_achieved_students)
    n_fskfirst_achieved_higher = len(fsk_first_students & higher_achieved_students)
    n_fskfirst_achieved_both = len(fsk_first_students & fsk_achieved_students & higher_achieved_students)

    h(2, "4. Achievement among students who started FSK10213 first")
    table(
        ["Metric", "Count", "Of"],
        [
            ["Started FSK10213 strictly first", len(fsk_first_students), len(fsk_first_students)],
            ["...with >=1 Achieved unit in FSK10213", n_fskfirst_achieved_lower, len(fsk_first_students)],
            ["...with >=1 Achieved unit in a higher program", n_fskfirst_achieved_higher, len(fsk_first_students)],
            ["...with >=1 Achieved unit in both", n_fskfirst_achieved_both, len(fsk_first_students)],
        ],
    )

    # ------------------------------------------------------------------
    # Item 5: achievement among all students in both (regardless of order)
    # ------------------------------------------------------------------
    n_both_achieved_lower = len(both_students & fsk_achieved_students)
    n_both_achieved_higher = len(both_students & higher_achieved_students)

    h(2, "5. Achievement among all students in both programs (regardless of order)")
    table(
        ["Metric", "Count", "Of"],
        [
            ["Students in both programs", n_both, n_both],
            ["...with >=1 Achieved unit in FSK10213", n_both_achieved_lower, n_both],
            ["...with >=1 Achieved unit in a higher program", n_both_achieved_higher, n_both],
        ],
    )

    # ------------------------------------------------------------------
    # Item 6: chance benchmark (permutation of start-date labels)
    # ------------------------------------------------------------------
    n_lower_first_obs = main["n_lower_first"]
    n_same_obs = main["n_same_date"]
    n_higher_first_obs = main["n_higher_first"]
    n_order_pop = len(both_with_dates)

    diffs_days = (lower_dates - higher_dates).dt.days.to_numpy()  # negative => lower (FSK) started first

    rng = np.random.default_rng(SEED)
    signs = rng.choice([-1, 1], size=(N_PERMUTATIONS, len(diffs_days)))
    permuted = signs * diffs_days
    counts_lower_first = (permuted < 0).sum(axis=1)

    exp_mean = float(counts_lower_first.mean())
    exp_lo, exp_hi = np.percentile(counts_lower_first, [2.5, 97.5])

    h(2, "6. Chance benchmark: random order of FSK10213 vs higher-program start")
    p(
        f"Among the {n_order_pop} students in both programs with a valid start date on each side, each "
        f"student's two actual start dates are kept, but which one is labelled 'FSK10213' and which is "
        f"labelled 'higher program' is randomised with a fair coin, independently per student per "
        f"permutation ({N_PERMUTATIONS:,} permutations, seed {SEED}). Same-date students never count as "
        f"'FSK first' under any labelling, since swapping identical dates changes nothing."
    )
    table(
        ["Metric", "Value"],
        [
            ["Observed: started FSK10213 strictly first", n_lower_first_obs],
            ["Observed: started both on the same date", n_same_obs],
            ["Observed: started a higher program strictly first", n_higher_first_obs],
            ["Expected FSK-first under random order (mean)", f"{exp_mean:.1f}"],
            ["Expected FSK-first under random order (95% range)", f"{exp_lo:.0f} to {exp_hi:.0f}"],
        ],
    )
    chance_conclusion = (
        "above" if n_lower_first_obs > exp_hi else ("below" if n_lower_first_obs < exp_lo else "within")
    )
    p(
        f"The observed count ({n_lower_first_obs}) sits **{chance_conclusion}** the 95% range expected under "
        f"random ordering ({exp_lo:.0f} to {exp_hi:.0f})."
    )

    # ------------------------------------------------------------------
    # Item 7: BSB20120 -> BSB30120 and CER30115 -> CER40115
    # ------------------------------------------------------------------
    h(2, "7. BSB20120 to BSB30120, and CER30115 to CER40115")
    pathway_block(enr, ["BSB20120"], ["BSB30120"], "BSB20120 -> BSB30120", LINES)
    pathway_block(enr, ["CER30115"], ["CER40115"], "CER30115 -> CER40115", LINES)

    # ------------------------------------------------------------------
    # Item 8: same provider vs different provider, FSK-first students
    # ------------------------------------------------------------------
    fsk_first_rows_lower = fsk_rows[fsk_rows["Student_ID"].isin(fsk_first_students)]
    higher_rows_for_fskfirst = higher_rows_all[higher_rows_all["Student_ID"].isin(fsk_first_students)]

    lower_provider_row = earliest_start_row_per_student(fsk_first_rows_lower)
    higher_provider_row = earliest_start_row_per_student(higher_rows_for_fskfirst)

    both_providers = lower_provider_row[["Provider_ID"]].join(
        higher_provider_row[["Provider_ID"]], lsuffix="_lower", rsuffix="_higher", how="inner"
    )
    n_same_provider = int((both_providers["Provider_ID_lower"] == both_providers["Provider_ID_higher"]).sum())
    n_diff_provider = int((both_providers["Provider_ID_lower"] != both_providers["Provider_ID_higher"]).sum())

    h(2, "8. FSK-first students: same provider or different provider for the higher program")
    p(
        "Provider is taken from the specific enrolment row that set each student's earliest valid start date "
        "in that program; where more than one row is tied for the earliest date, the smallest Provider_ID is "
        "used as a deterministic tie-break (stated as an assumption, not silently applied)."
    )
    table(
        ["Metric", "Count"],
        [
            ["FSK-first students resolved to a provider on both sides", len(both_providers)],
            ["...same provider for both FSK10213 and the higher program", n_same_provider],
            ["...different provider for the higher program", n_diff_provider],
        ],
    )

    # ------------------------------------------------------------------
    # Claims
    # ------------------------------------------------------------------
    h(2, "Claim checks")

    def claim(letter, text, numbers, verdict):
        h(3, f"{letter}. \"{text}\"")
        p(numbers)
        p(f"**Verdict: {verdict}**")

    claim(
        "A",
        "102 is the number of students enrolled in FSK10213.",
        f"Distinct students with any FSK10213 enrolment (item 1): {n_fsk_students}. 102 is the number of "
        f"students in BOTH FSK10213 and a higher program (item 2), a different and smaller population - it "
        f"is not the count this statement describes.",
        "FALSE" if n_fsk_students != 102 else "TRUE",
    )

    claim(
        "B",
        "89 is the number of students who achieved units in the higher qualification.",
        f"Students in both programs with >=1 Achieved unit in a higher program (item 5): {n_both_achieved_higher}. "
        f"Students in both programs with >=1 Achieved unit in FSK10213 (item 5): {n_both_achieved_lower}. "
        f"89 does not match the higher-program figure; among students in both programs, 89 is instead very close "
        f"to (or equal to) the FSK10213 (lower-program) achievement figure, not the higher-qualification one.",
        "FALSE" if n_both_achieved_higher != 89 else "TRUE",
    )

    majority_lower_first = n_lower_first_obs > n_order_pop / 2
    claim(
        "C",
        "Most students enrolled in both programs started FSK10213 first.",
        f"Of the {n_order_pop} students in both programs with a valid date on each side: {n_lower_first_obs} "
        f"started FSK10213 first, {n_same_obs} started both on the same date, {n_higher_first_obs} started a "
        f"higher program first. {n_lower_first_obs} of {n_order_pop} is "
        f"{100*n_lower_first_obs/n_order_pop:.1f}% ({'a majority' if majority_lower_first else 'not a majority'}).",
        "TRUE" if majority_lower_first else ("PARTLY" if n_lower_first_obs >= n_higher_first_obs else "FALSE"),
    )

    claim(
        "D",
        "The data shows more movement from FSK10213 into higher programs than random ordering would produce.",
        f"Observed FSK-first count: {n_lower_first_obs}. Expected under random order: mean {exp_mean:.1f}, "
        f"95% range {exp_lo:.0f} to {exp_hi:.0f}. The observed count sits {chance_conclusion} that range.",
        "TRUE" if chance_conclusion == "above" else ("FALSE" if chance_conclusion == "below" else "PARTLY"),
    )

    h(2, "Unexpected findings and assumptions")
    p(
        f"- Unexpected: of the {n_order_pop} students in both FSK10213 and a higher program, more started a "
        f"higher program first ({n_higher_first_obs}) than started FSK10213 first ({n_lower_first_obs}). This "
        f"is not just a failure to confirm claim D ('more movement than chance') - the observed FSK-first "
        f"count sits below the 95% chance range, meaning the data shows less FSK-to-higher ordering than "
        f"random chance would produce, the opposite of what claim D asserts."
    )
    p(
        f"- Unexpected: among the {len(fsk_first_students)} FSK-first students, only {n_same_provider} stayed "
        f"with the same provider for their higher-program enrolment; {n_diff_provider} moved to a different "
        f"provider. Provider-switching is close to universal in this (small) group, not an occasional pattern."
    )
    p(
        "- Assumption: for item 3's alternative definition, a student whose higher-program rows all lack a "
        "valid start date is scored as 'no' (not excluded), since there is no confirmed later-starting row to "
        "point to; only a missing lower-program start date excludes a student from that check."
    )
    p(
        "- Assumption: item 8's provider attribution uses the single row that set a student's earliest valid "
        "start date in each program; a tie between providers on the exact same earliest date is broken by the "
        "smallest Provider_ID."
    )
    p(
        "- Claims A and B both reuse a number from an earlier report (102 students in both programs, and an "
        "achievement count) but misattribute what population or program that number described; recomputing "
        "from scratch here is what surfaces the misattribution rather than confirming the claim."
    )

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "pathway_check.md").write_text("\n".join(LINES))

    # Small additive aggregate table (counts only, no student-level rows),
    # so the Method page can show these four figures without re-deriving
    # them or reading this script's markdown.
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    t20 = pd.DataFrame(
        [
            ["FSK10213 students", n_fsk_students],
            ["Students in both FSK10213 and a higher program", n_both],
            ["Started FSK10213 first", n_lower_first_obs],
            ["Started the higher program first", n_higher_first_obs],
            ["Chance range low (95%)", round(float(exp_lo))],
            ["Chance range high (95%)", round(float(exp_hi))],
        ],
        columns=["Metric", "Value"],
    )
    t20.to_csv(TABLES_DIR / "t20_pathway_check.csv", index=False)
    print("Wrote outputs/pathway_check.md")
    print("Wrote outputs/analysis_tables/t20_pathway_check.csv")
    print(f"FSK10213 learners: {n_fsk_students}")
    print(f"Students in both (FSK10213 + Cert II/III): {n_both}")
    print(f"Achieved-in-lower among both: {n_both_achieved_lower}")
    print(f"Achieved-in-higher among both: {n_both_achieved_higher}")
    print(f"FSK-first observed: {n_lower_first_obs}, same-date: {n_same_obs}, higher-first: {n_higher_first_obs}")
    print(f"Chance benchmark mean {exp_mean:.1f}, 95% range {exp_lo:.0f}-{exp_hi:.0f}")


if __name__ == "__main__":
    main()
