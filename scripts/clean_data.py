"""
NT VET Performance project - cleaning phase.

Reads data/raw/VET_Data_Task1.xlsx (never modified) and writes cleaned tables
to data/clean/, a rule-by-rule change log to outputs/cleaning_log.csv, and a
plain-English summary to outputs/data_quality_summary.md.

Rerun safety: this script is deterministic and can be run any number of
times against the same raw file for the same result.

Privacy: USI and DOB values are never printed or logged, only counts and
aggregates. data/ is gitignored; this script never sends data anywhere.
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "raw" / "VET_Data_Task1.xlsx"
CLEAN_DIR = ROOT / "data" / "clean"
OUTPUTS_DIR = ROOT / "outputs"

CLEAN_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# Collected as the script runs: one dict per rule, written to cleaning_log.csv
LOG_ROWS = []

# Plain-English notes collected as the script runs, written to
# data_quality_summary.md at the end.
SUMMARY_NOTES = []


def log_rule(rule_id, description, table, rows_before, rows_after, rows_changed, change_type):
    # change_type: "modified" (existing values changed in place), "dropped"
    # (rows removed), or "derived" (new column(s) added / new table built,
    # no existing values changed).
    if change_type not in {"modified", "dropped", "derived"}:
        raise ValueError(f"Invalid change_type: {change_type!r}")
    LOG_ROWS.append(
        {
            "rule_id": rule_id,
            "description": description,
            "table": table,
            "rows_before": rows_before,
            "rows_after": rows_after,
            "rows_changed": rows_changed,
            "change_type": change_type,
        }
    )


def note(rule_id, title, text):
    SUMMARY_NOTES.append((rule_id, title, text))


def fail(message):
    print(f"VALIDATION FAILED: {message}", file=sys.stderr)
    sys.exit(1)


def main():
    if not RAW_PATH.exists():
        fail(f"Raw workbook not found at {RAW_PATH}")

    xl = pd.ExcelFile(RAW_PATH)
    organisation = xl.parse("Organisation")
    contract = xl.parse("Contract")
    student = xl.parse("Student")
    enrolment = xl.parse("Enrolment")

    raw_total_ahc_funded = int(enrolment["AHC_Funded"].sum())

    # ------------------------------------------------------------------
    # A3. Organisation duplicates: raw 10 rows -> 8, one per Provider_ID,
    # keeping the first-listed name per Provider_ID.
    # ------------------------------------------------------------------
    rows_before = len(organisation)
    organisation_clean = organisation.drop_duplicates(subset=["Provider_ID"], keep="first").reset_index(drop=True)
    rows_after = len(organisation_clean)
    if rows_after != 8:
        fail(f"A3: expected 8 Organisation rows after dedup, got {rows_after}")
    log_rule(
        "A3",
        "Drop Organisation duplicates, keep first-listed name per Provider_ID",
        "Organisation",
        rows_before,
        rows_after,
        rows_before - rows_after,
        "dropped",
    )
    note(
        "A3",
        "Organisation duplicates",
        "The Organisation table had 10 rows for 8 providers. P001 and P003 each appeared twice with "
        "slightly different names. We kept the first-listed name for each: 'Charles Darwin University' "
        "for P001 and 'NT Skills & Training Pty Ltd' for P003.",
    )

    # ------------------------------------------------------------------
    # A1. Enrolment duplicates: drop the 5 exact duplicate rows, keep the first.
    # ------------------------------------------------------------------
    rows_before = len(enrolment)
    dup_mask = enrolment.duplicated(keep="first")
    dropped_dup_ahc = int(enrolment.loc[dup_mask, "AHC_Funded"].sum())
    enrolment_clean = enrolment.loc[~dup_mask].reset_index(drop=True)
    rows_after = len(enrolment_clean)
    if rows_before != 5505:
        fail(f"A1: expected 5,505 raw Enrolment rows, got {rows_before}")
    if rows_after != 5500:
        fail(f"A1: expected 5,500 Enrolment rows after dedup, got {rows_after}")
    log_rule(
        "A1",
        "Drop exact duplicate Enrolment rows, keep first",
        "Enrolment",
        rows_before,
        rows_after,
        rows_before - rows_after,
        "dropped",
    )
    note(
        "A1",
        "Enrolment duplicates",
        f"5 rows in Enrolment were exact duplicates of other rows. We kept the first occurrence of each "
        f"and dropped the other {int(dup_mask.sum())}, reducing 5,505 rows to 5,500.",
    )

    # ------------------------------------------------------------------
    # A2. Missing Provider_Name: fill from Provider_ID using the
    # Organisation table (RTO_Name is consistent per Provider_ID).
    # ------------------------------------------------------------------
    name_lookup = organisation_clean.set_index("Provider_ID")["RTO_Name"].to_dict()
    missing_before = int(enrolment_clean["Provider_Name"].isna().sum())
    if missing_before != 328:
        fail(f"A2: expected 328 missing Provider_Name values, got {missing_before}")
    fill_mask = enrolment_clean["Provider_Name"].isna()
    enrolment_clean.loc[fill_mask, "Provider_Name"] = enrolment_clean.loc[fill_mask, "Provider_ID"].map(name_lookup)
    missing_after = int(enrolment_clean["Provider_Name"].isna().sum())
    log_rule(
        "A2",
        "Fill missing Provider_Name from Organisation table via Provider_ID",
        "Enrolment",
        len(enrolment_clean),
        len(enrolment_clean),
        int(fill_mask.sum()),
        "modified",
    )
    note(
        "A2",
        "Missing provider names",
        f"328 Enrolment rows had a blank Provider_Name. Each Provider_ID has exactly one organisation "
        f"name, so we filled the blanks from the Organisation table. {missing_after} rows remain blank "
        f"after this fix.",
    )
    if missing_after > 0:
        note(
            "A2",
            "Missing provider names - unresolved",
            f"{missing_after} rows could not be filled because their Provider_ID was not found in the "
            f"Organisation table. Left as-is; do not guess.",
        )

    # ------------------------------------------------------------------
    # A4. Nominal_Hours: stored as text. Convert to numeric; rebuild
    # blanks and unparseable values from a Unit_ID lookup (each Unit_ID
    # has exactly one valid value in the data).
    # ------------------------------------------------------------------
    rows_before = len(enrolment_clean)
    numeric_hours = pd.to_numeric(enrolment_clean["Nominal_Hours"], errors="coerce")
    bad_mask = numeric_hours.isna()
    bad_count = int(bad_mask.sum())

    unit_lookup = (
        enrolment_clean.loc[~bad_mask]
        .assign(_hours=numeric_hours[~bad_mask])
        .groupby("Unit_ID")["_hours"]
        .agg(lambda s: s.iloc[0] if s.nunique() == 1 else None)
        .to_dict()
    )

    enrolment_clean["Nominal_Hours_Raw"] = enrolment_clean["Nominal_Hours"]
    enrolment_clean["Nominal_Hours"] = numeric_hours
    recovered_mask = bad_mask & enrolment_clean["Unit_ID"].map(lambda u: unit_lookup.get(u) is not None)
    enrolment_clean.loc[recovered_mask, "Nominal_Hours"] = enrolment_clean.loc[recovered_mask, "Unit_ID"].map(unit_lookup)

    still_bad_mask = enrolment_clean["Nominal_Hours"].isna()
    still_bad_units = sorted(enrolment_clean.loc[still_bad_mask, "Unit_ID"].unique().tolist())

    log_rule(
        "A4",
        "Convert Nominal_Hours to numeric; rebuild blanks/unparseable values from Unit_ID lookup",
        "Enrolment",
        rows_before,
        len(enrolment_clean),
        bad_count,
        "modified",
    )
    note(
        "A4",
        "Nominal_Hours text values",
        f"Nominal_Hours was stored as text. {bad_count} rows were blank or unparseable (for example "
        f"'thirty', '-', 'TBD', 'unknown'). Each Unit_ID has exactly one valid hours value elsewhere in "
        f"the data, so we converted the column to numeric and rebuilt the {int(recovered_mask.sum())} "
        f"bad values from that lookup. The original text is kept in Nominal_Hours_Raw for traceability.",
    )
    if still_bad_units:
        note(
            "A4",
            "Nominal_Hours - unresolved",
            f"Unit_ID(s) with no recoverable value anywhere in the data: {still_bad_units}. Left as null; "
            f"do not guess.",
        )

    # ------------------------------------------------------------------
    # A5. Gender: standardise case variants.
    # ------------------------------------------------------------------
    gender_map = {"male": "M", "Male": "M", "FEMALE": "F", "female": "F"}
    before_counts = student["Gender"].value_counts(dropna=False).to_dict()
    changed_mask = student["Gender"].isin(gender_map.keys())
    student_clean = student.copy()
    student_clean["Gender"] = student_clean["Gender"].replace(gender_map)
    after_counts = student_clean["Gender"].value_counts(dropna=False).to_dict()
    expected_gender = {"F": 670, "M": 647, "X": 657}
    if after_counts != expected_gender:
        fail(f"A5: expected Gender counts {expected_gender}, got {after_counts}")
    log_rule(
        "A5",
        "Standardise Gender case variants to M/F (X unchanged)",
        "Student",
        len(student),
        len(student_clean),
        int(changed_mask.sum()),
        "modified",
    )
    note(
        "A5",
        "Gender standardisation",
        f"Gender had case-variant spellings ('Male', 'male', 'FEMALE', 'female'). We standardised these "
        f"to M/F. Final counts: F 670, M 647, X 657.",
    )

    # ------------------------------------------------------------------
    # A6. ATSI: standardise case/word variants of yes to Y.
    # ------------------------------------------------------------------
    atsi_map = {"y": "Y", "yes": "Y", "Yes": "Y", "YES": "Y"}
    changed_mask = student_clean["ATSI"].isin(atsi_map.keys())
    student_clean["ATSI"] = student_clean["ATSI"].replace(atsi_map)
    after_counts = student_clean["ATSI"].value_counts(dropna=False).to_dict()
    expected_atsi = {"Y": 702, "N": 1272}
    if after_counts != expected_atsi:
        fail(f"A6: expected ATSI counts {expected_atsi}, got {after_counts}")
    log_rule(
        "A6",
        "Standardise ATSI 'y'/'yes'/'Yes'/'YES' to Y",
        "Student",
        len(student_clean),
        len(student_clean),
        int(changed_mask.sum()),
        "modified",
    )
    note(
        "A6",
        "ATSI standardisation",
        "ATSI had several variants of 'yes' ('y', 'yes', 'Yes', 'YES'). We standardised these to Y. "
        "Final counts: Y 702, N 1,272.",
    )

    # ------------------------------------------------------------------
    # A7. Invalid start dates: 2030 is invalid. Null the date, flag it.
    # Delivery_Year remains the reporting year regardless.
    # ------------------------------------------------------------------
    invalid_start_mask = enrolment_clean["Enrol_Start_Date"].dt.year == 2030
    invalid_count = int(invalid_start_mask.sum())
    if invalid_count != 8:
        fail(f"A7: expected 8 rows with Enrol_Start_Date in 2030, got {invalid_count}")
    enrolment_clean["Start_Date_Invalid"] = invalid_start_mask
    enrolment_clean.loc[invalid_start_mask, "Enrol_Start_Date"] = pd.NaT
    log_rule(
        "A7",
        "Null Enrol_Start_Date for 2030 rows, add Start_Date_Invalid flag",
        "Enrolment",
        len(enrolment_clean),
        len(enrolment_clean),
        invalid_count,
        "modified",
    )
    note(
        "A7",
        "Invalid start dates",
        "8 rows had an Enrol_Start_Date in 2030, which is not a valid training date in this dataset. "
        "We set the date to null and added Start_Date_Invalid = True for these rows. Delivery_Year is "
        "unaffected and remains the reporting year.",
    )

    # ------------------------------------------------------------------
    # A8. Contract totals.
    # ------------------------------------------------------------------
    contract_clean = contract.copy()
    contract_clean["Target_Total_Source"] = "as given"
    contract_clean["Target_Status"] = "Target set"

    parts_sum = (
        contract_clean["Target_AHC_Urban"] + contract_clean["Target_AHC_Regional"] + contract_clean["Target_AHC_Remote"]
    )
    zero_total_mask = contract_clean["Target_AHC_Total"] == 0
    all_zero_mask = zero_total_mask & (parts_sum == 0)
    rebuild_mask = zero_total_mask & (parts_sum != 0)

    rebuilt_contracts = contract_clean.loc[rebuild_mask, "Contract_Number"].tolist()
    if sorted(rebuilt_contracts) != ["DCVT-2008", "DCVT-2021"]:
        fail(f"A8: expected DCVT-2008 and DCVT-2021 to need rebuilding, got {rebuilt_contracts}")
    no_target_contracts = contract_clean.loc[all_zero_mask, "Contract_Number"].tolist()
    if no_target_contracts != ["DCVT-2020"]:
        fail(f"A8: expected only DCVT-2020 to have no target, got {no_target_contracts}")

    contract_clean.loc[rebuild_mask, "Target_AHC_Total"] = parts_sum[rebuild_mask]
    contract_clean.loc[rebuild_mask, "Target_Total_Source"] = "rebuilt from parts"

    contract_clean.loc[all_zero_mask, "Target_AHC_Total"] = pd.NA
    contract_clean.loc[all_zero_mask, "Target_Status"] = "No target set"

    dcvt_2008_total = contract_clean.loc[contract_clean["Contract_Number"] == "DCVT-2008", "Target_AHC_Total"].iloc[0]
    dcvt_2021_total = contract_clean.loc[contract_clean["Contract_Number"] == "DCVT-2021", "Target_AHC_Total"].iloc[0]
    if dcvt_2008_total != 24870:
        fail(f"A8: expected DCVT-2008 rebuilt total 24,870, got {dcvt_2008_total}")
    if dcvt_2021_total != 43440:
        fail(f"A8: expected DCVT-2021 rebuilt total 43,440, got {dcvt_2021_total}")

    # Contracts where Target_AHC_Total is non-zero but off by +/-1 against the
    # sum of its three parts. Per the brief these are rounding differences,
    # not data errors, and are kept "as given".
    rounding_mask = ~zero_total_mask & (contract_clean["Target_AHC_Total"] != parts_sum)
    rounding_diffs = (
        (contract_clean.loc[rounding_mask, "Target_AHC_Total"] - parts_sum[rounding_mask]).astype(int).tolist()
    )
    rounding_contracts = contract_clean.loc[rounding_mask, "Contract_Number"].tolist()
    if len(rounding_contracts) != 5:
        fail(f"A8: expected 5 contracts with +/-1 rounding differences, got {len(rounding_contracts)}")
    rounding_detail = ", ".join(
        f"{c} ({d:+d})" for c, d in sorted(zip(rounding_contracts, rounding_diffs))
    )

    log_rule(
        "A8",
        "Rebuild zero Target_AHC_Total from parts where real targets exist; null true zero-target rows",
        "Contract",
        len(contract),
        len(contract_clean),
        int(rebuild_mask.sum() + all_zero_mask.sum()),
        "modified",
    )
    note(
        "A8",
        "Contract totals",
        "Target_AHC_Total was 0 for three contracts. DCVT-2008 and DCVT-2021 had real regional targets "
        "(Urban + Regional + Remote), so we rebuilt their totals from those parts (24,870 and 43,440). "
        "DCVT-2020 had all-zero values everywhere, so we set its target to null and Target_Status = "
        "'No target set' rather than treating it as a target of zero. Target_Total_Source records "
        "whether each total is 'as given' or 'rebuilt from parts'. Separately, five contracts have a "
        f"+/-1 difference between Target_AHC_Total and the sum of its three parts - "
        f"{rounding_detail}. These are treated as rounding differences, not data errors, and are "
        "left as given (Target_Total_Source = 'as given').",
    )

    # ------------------------------------------------------------------
    # B2. Unknown funding source: try to recover from Student_ID +
    # Provider_ID + Program_ID; otherwise set to "Unknown".
    # ------------------------------------------------------------------
    unk_mask = enrolment_clean["Funding_Source"] == "UNK"
    unk_count = int(unk_mask.sum())
    if unk_count != 30:
        fail(f"B2: expected 30 UNK rows, got {unk_count}")

    non_unk = enrolment_clean.loc[~unk_mask, ["Student_ID", "Provider_ID", "Program_ID", "Funding_Source"]].drop_duplicates()
    fs_lookup = (
        non_unk.groupby(["Student_ID", "Provider_ID", "Program_ID"])["Funding_Source"]
        .agg(lambda s: s.iloc[0] if s.nunique() == 1 else None)
        .to_dict()
    )

    enrolment_clean["Funding_Source_Recovered"] = False
    unk_keys = list(
        zip(
            enrolment_clean.loc[unk_mask, "Student_ID"],
            enrolment_clean.loc[unk_mask, "Provider_ID"],
            enrolment_clean.loc[unk_mask, "Program_ID"],
        )
    )
    recovered_values = [fs_lookup.get(k) for k in unk_keys]
    recovered_count = sum(1 for v in recovered_values if v is not None)

    unk_idx = enrolment_clean.index[unk_mask]
    recovery_breakdown = pd.DataFrame(
        {
            "Provider_ID": enrolment_clean.loc[unk_idx, "Provider_ID"].values,
            "Recovered_Funding_Source": recovered_values,
        }
    )
    recovery_breakdown = recovery_breakdown[recovery_breakdown["Recovered_Funding_Source"].notna()]
    by_funding_source = recovery_breakdown["Recovered_Funding_Source"].value_counts().sort_index()
    by_provider = recovery_breakdown["Provider_ID"].value_counts().sort_index()

    for idx, new_fs in zip(unk_idx, recovered_values):
        if new_fs is not None:
            enrolment_clean.loc[idx, "Funding_Source"] = new_fs
            enrolment_clean.loc[idx, "Funding_Source_Recovered"] = True
        else:
            enrolment_clean.loc[idx, "Funding_Source"] = "Unknown"

    log_rule(
        "B2",
        "Recover UNK Funding_Source from Student_ID+Provider_ID+Program_ID where unambiguous; else 'Unknown'",
        "Enrolment",
        len(enrolment_clean),
        len(enrolment_clean),
        unk_count,
        "modified",
    )
    recovered_breakdown_rows = (
        [["Funding_Source", fs, int(count)] for fs, count in by_funding_source.items()]
        + [["Provider_ID", pid, int(count)] for pid, count in by_provider.items()]
    )
    pd.DataFrame(recovered_breakdown_rows, columns=["Dimension", "Group", "Recovered_rows"]).to_csv(
        OUTPUTS_DIR / "recovered_funding_source.csv", index=False
    )
    fs_table = "\n".join(
        ["| Funding_Source | Recovered rows |", "|---|---|"]
        + [f"| {fs} | {count} |" for fs, count in by_funding_source.items()]
    )
    provider_table = "\n".join(
        ["| Provider_ID | Recovered rows |", "|---|---|"]
        + [f"| {pid} | {count} |" for pid, count in by_provider.items()]
    )
    note(
        "B2",
        "Unknown funding source",
        f"30 rows had Funding_Source = 'UNK'. {recovered_count} of these were recovered because the "
        f"same student, provider and program had exactly one other, known funding source elsewhere in "
        f"the data (Funding_Source_Recovered = True). The remaining {unk_count - recovered_count} were "
        f"set to 'Unknown'. These rows stay in overall totals but are excluded from stream-level and "
        f"contract comparisons.\n\n"
        f"Recovered rows by Funding_Source:\n\n{fs_table}\n\n"
        f"Recovered rows by Provider_ID:\n\n{provider_table}",
    )

    # ------------------------------------------------------------------
    # A9. Students with no enrolments: keep, flag Has_Enrolment.
    # ------------------------------------------------------------------
    enrolled_ids = set(enrolment_clean["Student_ID"])
    student_clean["Has_Enrolment"] = student_clean["Student_ID"].isin(enrolled_ids)
    no_enrolment_count = int((~student_clean["Has_Enrolment"]).sum())
    if no_enrolment_count != 771:
        fail(f"A9: expected 771 students with no enrolment, got {no_enrolment_count}")
    log_rule(
        "A9",
        "Add Has_Enrolment flag; keep students with no enrolment",
        "Student",
        len(student_clean),
        len(student_clean),
        len(student_clean),
        "derived",
    )
    note(
        "A9",
        "Students with no enrolments",
        f"771 of {len(student_clean):,} students have no enrolment record. These are kept in the Student "
        f"table with Has_Enrolment = False. Participation analysis later should use only the "
        f"{len(student_clean) - no_enrolment_count:,} students with Has_Enrolment = True.",
    )

    # ------------------------------------------------------------------
    # B3. Funded_Flag: not changed/re-derived. Carry_Over_Flag added.
    # ------------------------------------------------------------------
    valid_start = enrolment_clean["Enrol_Start_Date"].notna()
    carry_over_mask = valid_start & (enrolment_clean["Delivery_Year"] > enrolment_clean["Enrol_Start_Date"].dt.year)
    enrolment_clean["Carry_Over_Flag"] = carry_over_mask
    y_carry_over_count = int(((enrolment_clean["Funded_Flag"] == "Y") & carry_over_mask).sum())
    log_rule(
        "B3",
        "Add Carry_Over_Flag where Delivery_Year is later than a valid Enrol_Start_Date's year",
        "Enrolment",
        len(enrolment_clean),
        len(enrolment_clean),
        int(carry_over_mask.sum()),
        "derived",
    )
    note(
        "B3",
        "Funded_Flag and carry-over (data dictionary conflict)",
        "Funded_Flag was left exactly as supplied and was not re-derived. The data dictionary describes "
        "the 85%_only code as 'cancelled/withdrawn', but those 960 rows carry outcome codes 51, 52 and "
        "70 (RPL granted, credit transfer, continuing) - not cancellation outcomes. In practice "
        "Funded_Flag behaves as an 85/15 funding-timing rule, not a cancellation flag. We treat "
        "AHC_Funded as the single source of truth for funded hours, since it is complete and consistent "
        "with the flag at 100%/85%/15%/0%. Delivery_Year is used as the reporting year. "
        f"Carry_Over_Flag = True is added where Delivery_Year is later than the year of a valid "
        f"Enrol_Start_Date ({int(carry_over_mask.sum())} rows). Of those, {y_carry_over_count} rows "
        f"are also Funded_Flag = 'Y' (fully funded) despite being a carry-over enrolment.",
    )

    # ------------------------------------------------------------------
    # Outcome_Group / In_Completion_Rate.
    # ------------------------------------------------------------------
    outcome_group_map = {
        20: ("Achieved", True),
        51: ("Achieved", True),
        52: ("Achieved", True),
        30: ("Not achieved", True),
        40: ("Withdrawn", True),
        70: ("Continuing", False),
        60: ("Not funded / not started", False),
        61: ("Not funded / not started", False),
        85: ("Not funded / not started", False),
        81: ("Learner support", False),
        82: ("Learner support", False),
    }
    enrolment_clean["Outcome_Group"] = enrolment_clean["Outcome"].map(lambda o: outcome_group_map.get(o, (None, None))[0])
    enrolment_clean["In_Completion_Rate"] = enrolment_clean["Outcome"].map(lambda o: outcome_group_map.get(o, (None, None))[1])
    unmapped = int(enrolment_clean["Outcome_Group"].isna().sum())
    if unmapped:
        fail(f"Outcome_Group: {unmapped} rows have an Outcome code not covered by the grouping table")
    log_rule(
        "C1",
        "Add Outcome_Group and In_Completion_Rate from Outcome code",
        "Enrolment",
        len(enrolment_clean),
        len(enrolment_clean),
        len(enrolment_clean),
        "derived",
    )
    note(
        "C1",
        "Outcome grouping",
        "Every Enrolment row is grouped into Outcome_Group (Achieved, Not achieved, Withdrawn, "
        "Continuing, Not funded / not started, or Learner support) and flagged In_Completion_Rate = True "
        "for the three groups (Achieved, Not achieved, Withdrawn) used in the completion-rate "
        "denominator.",
    )

    # ------------------------------------------------------------------
    # B4. At_School_Flag: keep; add Age_at_Enrolment and At_School_Suspect.
    # ------------------------------------------------------------------
    enrolment_with_dob = enrolment_clean.merge(
        student_clean[["Student_ID", "DOB", "At_School_Flag"]], on="Student_ID", how="left"
    )

    reference_date = enrolment_with_dob["Enrol_Start_Date"].copy()
    fallback_date = pd.to_datetime(enrolment_with_dob["Delivery_Year"].astype(str) + "-07-01")
    reference_date = reference_date.where(reference_date.notna(), fallback_date)

    dob = enrolment_with_dob["DOB"]
    age_years = reference_date.dt.year - dob.dt.year
    had_birthday = (reference_date.dt.month > dob.dt.month) | (
        (reference_date.dt.month == dob.dt.month) & (reference_date.dt.day >= dob.dt.day)
    )
    age_at_enrolment = age_years - (~had_birthday).astype(int)

    enrolment_clean["Age_at_Enrolment"] = age_at_enrolment.values
    enrolment_clean["At_School_Suspect"] = (
        (enrolment_with_dob["At_School_Flag"] == "Y") & (enrolment_clean["Age_at_Enrolment"] > 19)
    ).values

    suspect_count = int(enrolment_clean["At_School_Suspect"].sum())
    vet_in_schools_mask = enrolment_clean["Funding_Source"].isin(["11N", "11V"])
    vet_in_schools_total = int(vet_in_schools_mask.sum())
    vet_in_schools_not_at_school = int(
        (vet_in_schools_mask & (enrolment_with_dob["At_School_Flag"] != "Y")).sum()
    )

    log_rule(
        "B4",
        "Add Age_at_Enrolment and At_School_Suspect; keep At_School_Flag unchanged",
        "Enrolment",
        len(enrolment_clean),
        len(enrolment_clean),
        len(enrolment_clean),
        "derived",
    )
    note(
        "B4",
        "At-school flag vs age and funding stream",
        f"At_School_Flag is kept unchanged. We added Age_at_Enrolment (completed years, from DOB and "
        f"Enrol_Start_Date, or 1 July of Delivery_Year where the start date is null/invalid) and "
        f"At_School_Suspect = True where At_School_Flag is Y but the student was over 19 "
        f"({suspect_count} rows). VET in Schools is defined later by funding stream (11N and 11V), not "
        f"by this flag: of {vet_in_schools_total:,} 11N/11V rows, {vet_in_schools_not_at_school} are "
        f"flagged At_School_Flag != Y.",
    )

    # ------------------------------------------------------------------
    # B5. Gender X note (no further change; already standardised in A5).
    # ------------------------------------------------------------------
    note(
        "B5",
        "Gender X is unusually high",
        "657 of 1,974 students (about a third) are coded Gender = X. This is unusually high for a "
        "non-binary code and the data dictionary's code list looks truncated. We cleaned the case "
        "variants (A5) and kept X as supplied, but gender should not be used for headline findings "
        "until this is clarified with the data owner.",
    )
    log_rule(
        "B5",
        "Documentation caveat only: Gender = X prevalence noted, no further change beyond A5",
        "Student",
        len(student_clean),
        len(student_clean),
        0,
        "derived",
    )

    # ------------------------------------------------------------------
    # Validation.
    # ------------------------------------------------------------------
    if len(enrolment_clean) != 5500:
        fail(f"Validation: expected 5,500 Enrolment rows, got {len(enrolment_clean)}")
    if len(organisation_clean) != 8:
        fail(f"Validation: expected 8 Organisation rows, got {len(organisation_clean)}")
    if len(contract_clean) != 23:
        fail(f"Validation: expected 23 Contract rows, got {len(contract_clean)}")
    if len(student_clean) != 1974:
        fail(f"Validation: expected 1,974 Student rows, got {len(student_clean)}")

    remaining_null_names = int(enrolment_clean["Provider_Name"].isna().sum())
    if remaining_null_names:
        fail(f"Validation: {remaining_null_names} Enrolment rows still have a null Provider_Name")

    non_numeric_hours = enrolment_clean.loc[
        ~enrolment_clean["Nominal_Hours"].apply(lambda v: isinstance(v, (int, float)) or pd.isna(v))
    ]
    if len(non_numeric_hours) > 0:
        fail(f"Validation: {len(non_numeric_hours)} Nominal_Hours values are not numeric")

    bad_gender = set(student_clean["Gender"].unique()) - {"M", "F", "X"}
    if bad_gender:
        fail(f"Validation: unexpected Gender codes {bad_gender}")
    bad_atsi = set(student_clean["ATSI"].unique()) - {"Y", "N"}
    if bad_atsi:
        fail(f"Validation: unexpected ATSI codes {bad_atsi}")

    enrolment_student_ids = set(enrolment_clean["Student_ID"])
    student_ids = set(student_clean["Student_ID"])
    missing_students = enrolment_student_ids - student_ids
    if missing_students:
        fail(f"Validation: {len(missing_students)} Enrolment Student_IDs missing from Student")

    usi_check = enrolment_clean[["Student_ID", "USI"]].drop_duplicates().merge(
        student_clean[["Student_ID", "USI"]], on="Student_ID", suffixes=("_enrolment", "_student")
    )
    usi_mismatches = usi_check[usi_check["USI_enrolment"] != usi_check["USI_student"]]
    if len(usi_mismatches) > 0:
        fail(f"Validation: {len(usi_mismatches)} USI mismatches between Enrolment and Student")

    clean_total_ahc_funded = int(enrolment_clean["AHC_Funded"].sum())
    expected_clean_total = raw_total_ahc_funded - dropped_dup_ahc
    if clean_total_ahc_funded != expected_clean_total:
        fail(
            f"Validation: AHC_Funded total mismatch. Raw {raw_total_ahc_funded}, dropped duplicates "
            f"{dropped_dup_ahc}, expected {expected_clean_total}, got {clean_total_ahc_funded}"
        )
    note(
        "Validation",
        "AHC_Funded total reconciliation",
        f"Raw AHC_Funded total across all 5,505 rows: {raw_total_ahc_funded:,}. The 5 dropped duplicate "
        f"rows (A1) account for {dropped_dup_ahc:,} of that. Cleaned total after dedup: "
        f"{clean_total_ahc_funded:,}.",
    )

    if enrolment_clean["Outcome_Group"].isna().any():
        fail("Validation: some Enrolment rows have no Outcome_Group")

    log_rule(
        "Validation",
        "End-to-end checks: row counts, referential integrity, code domains, AHC_Funded reconciliation",
        "All",
        len(enrolment_clean),
        len(enrolment_clean),
        0,
        "derived",
    )

    note(
        "B6",
        "Targets are 3-year totals",
        "All contracts run 1 Jan 2023 to 31 Dec 2025 and are not pro-rated by year. Target_AHC_Total "
        "(and the Urban/Regional/Remote targets, after A8) are 3-year totals for the whole contract "
        "period. Delivered AHC_Funded is therefore compared against each target as a single cumulative "
        "2023-2025 figure, not year by year - this is the basis for the Delivered_AHC_2023_2025 columns "
        "in the B1 reconciliation below.",
    )

    # ------------------------------------------------------------------
    # B1. Contract vs delivery reconciliation.
    # ------------------------------------------------------------------
    recon_rows = []

    enr_combo_totals = (
        enrolment_clean[~enrolment_clean["Funding_Source"].isin(["Unknown"])]
        .groupby(["Provider_ID", "Funding_Source"])["AHC_Funded"]
        .sum()
    )
    enr_remoteness_totals = (
        enrolment_clean[~enrolment_clean["Funding_Source"].isin(["Unknown"])]
        .groupby(["Provider_ID", "Funding_Source", "Remoteness"])["AHC_Funded"]
        .sum()
    )

    contract_combos = set(zip(contract_clean["Provider_ID"], contract_clean["Funding_Source"]))
    enrolment_combos = set(enr_combo_totals.index.tolist())
    all_combos = sorted(contract_combos | enrolment_combos)

    contract_by_combo = contract_clean.set_index(["Provider_ID", "Funding_Source"])

    for provider_id, funding_source in all_combos:
        in_contract = (provider_id, funding_source) in contract_combos
        in_delivery = (provider_id, funding_source) in enrolment_combos

        if in_contract and in_delivery:
            status = "Matched"
        elif in_delivery:
            status = "Delivery without contract"
        else:
            status = "Contract without delivery"

        if in_contract:
            crow = contract_by_combo.loc[(provider_id, funding_source)]
            target_total = crow["Target_AHC_Total"]
            target_urban = crow["Target_AHC_Urban"]
            target_regional = crow["Target_AHC_Regional"]
            target_remote = crow["Target_AHC_Remote"]
            target_status = crow["Target_Status"]
        else:
            target_total = pd.NA
            target_urban = pd.NA
            target_regional = pd.NA
            target_remote = pd.NA
            target_status = "No contract"

        delivered_total = enr_combo_totals.get((provider_id, funding_source), 0)
        delivered_urban = enr_remoteness_totals.get((provider_id, funding_source, "Urban"), 0)
        delivered_regional = enr_remoteness_totals.get((provider_id, funding_source, "Regional"), 0)
        delivered_remote = enr_remoteness_totals.get((provider_id, funding_source, "Remote"), 0)

        recon_rows.append(
            {
                "Provider_ID": provider_id,
                "Funding_Source": funding_source,
                "Status": status,
                "Target_AHC_Total": target_total,
                "Target_Status": target_status,
                "Delivered_AHC_2023_2025": delivered_total,
                "Target_AHC_Urban": target_urban,
                "Delivered_AHC_Urban": delivered_urban,
                "Target_AHC_Regional": target_regional,
                "Delivered_AHC_Regional": delivered_regional,
                "Target_AHC_Remote": target_remote,
                "Delivered_AHC_Remote": delivered_remote,
            }
        )

    recon = pd.DataFrame(recon_rows)
    matched_count = int((recon["Status"] == "Matched").sum())
    delivery_without_contract_count = int((recon["Status"] == "Delivery without contract").sum())
    contract_without_delivery_count = int((recon["Status"] == "Contract without delivery").sum())

    if matched_count != 20:
        fail(f"B1: expected 20 Matched combos, got {matched_count}")
    if delivery_without_contract_count != 16:
        fail(f"B1: expected 16 Delivery without contract combos, got {delivery_without_contract_count}")
    if contract_without_delivery_count != 3:
        fail(f"B1: expected 3 Contract without delivery combos, got {contract_without_delivery_count}")

    p008_no_delivery = recon[(recon["Provider_ID"] == "P008") & (recon["Status"] == "Contract without delivery")][
        "Funding_Source"
    ].tolist()
    if sorted(p008_no_delivery) != ["11J", "11N", "11V"]:
        fail(f"B1: expected P008 11J/11N/11V as Contract without delivery, got {p008_no_delivery}")

    p008_fft_enrolments = int(
        ((enrolment_clean["Provider_ID"] == "P008") & (enrolment_clean["Funding_Source"] == "FFT")).sum()
    )
    note(
        "B1",
        "Contract vs delivery reconciliation",
        f"Matched on Provider_ID + Funding_Source only. Of 39 combinations found in either sheet: "
        f"{matched_count} are Matched, {delivery_without_contract_count} are Delivery without contract, "
        f"and {contract_without_delivery_count} are Contract without delivery - all three are P008's "
        f"11J, 11N and 11V contracts. P008 has {p008_fft_enrolments} FFT enrolments but no FFT contract. "
        f"This is flagged as a reconciliation discrepancy to verify with the data owner, not treated as "
        f"a compliance breach, and nothing is dropped or force-matched. All 30 originally-UNK rows were "
        f"recovered to a real funding source (B2), so no 'UNK' combinations remain in this table.",
    )
    log_rule(
        "B1",
        "Build contract_delivery_recon: one row per Provider_ID+Funding_Source found in either sheet",
        "contract_delivery_recon",
        0,
        len(recon),
        len(recon),
        "derived",
    )

    # ------------------------------------------------------------------
    # Write outputs.
    # ------------------------------------------------------------------
    organisation_clean.to_csv(CLEAN_DIR / "organisation.csv", index=False)
    contract_clean.to_csv(CLEAN_DIR / "contract.csv", index=False)
    student_clean.to_csv(CLEAN_DIR / "student.csv", index=False)
    enrolment_clean.to_csv(CLEAN_DIR / "enrolment.csv", index=False)
    recon.to_csv(CLEAN_DIR / "contract_delivery_recon.csv", index=False)

    pd.DataFrame(LOG_ROWS).to_csv(OUTPUTS_DIR / "cleaning_log.csv", index=False)

    summary_lines = ["# NT VET data cleaning - data quality summary", ""]
    for rule_id, title, text in SUMMARY_NOTES:
        summary_lines.append(f"## {rule_id}: {title}")
        summary_lines.append("")
        summary_lines.append(text)
        summary_lines.append("")
    (OUTPUTS_DIR / "data_quality_summary.md").write_text("\n".join(summary_lines))

    print("Cleaning complete.")
    print(f"  Enrolment: {len(enrolment_clean)} rows")
    print(f"  Organisation: {len(organisation_clean)} rows")
    print(f"  Contract: {len(contract_clean)} rows")
    print(f"  Student: {len(student_clean)} rows")
    print(f"  Recon combinations: {len(recon)} rows "
          f"(Matched {matched_count}, Delivery without contract {delivery_without_contract_count}, "
          f"Contract without delivery {contract_without_delivery_count})")
    print(f"  AHC_Funded total: raw {raw_total_ahc_funded:,} -> clean {clean_total_ahc_funded:,}")
    print(f"  UNK funding source recovered: {recovered_count} of {unk_count}")
    print("Wrote cleaning_log.csv and data_quality_summary.md to outputs/")


if __name__ == "__main__":
    main()
