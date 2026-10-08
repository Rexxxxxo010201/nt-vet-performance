# NT VET Performance project: cleaning phase

## Context
Graduate program assessment for the NT Department of Education and Training. The workbook `data/raw/VET_Data_Task1.xlsx` holds VET delivery data for 2023 to 2025 (sheets: Tasks, Data Dictionary, Organisation, Contract, Student, Enrolment). The final audience is an Executive Director, so every rule here must be explainable in plain English in a methodology appendix.

This phase is cleaning only. Do not do analysis, charts, modelling or dashboards yet.

## Ground rules
1. Never modify anything in `data/raw/`.
2. One script, `scripts/clean_data.py`, runs end to end from raw to clean and can be rerun at any time with the same result.
3. Every rule gets an ID (A1, B2, etc., as below) and a row in `outputs/cleaning_log.csv` with: rule_id, description, table, rows_before, rows_after, rows_changed.
4. Do not make silent assumptions. If something is not covered by this brief, stop and ask.
5. The data contains student-level USIs, dates of birth and ATSI status. Never print USIs or DOBs to the terminal or logs, never commit `data/` to git, and never send data to any external service.
6. Keep original columns where practical and add new columns for derived values, so every change is traceable.

## Output files (all in `data/clean/` unless noted)
- `organisation.csv`, `contract.csv`, `student.csv`, `enrolment.csv`
- `contract_delivery_recon.csv` (see B1)
- `outputs/cleaning_log.csv`
- `outputs/data_quality_summary.md`: plain-English summary of every rule, what it changed and why

## Mechanical rules (apply as written)

**A1. Enrolment duplicates.** Drop the 5 exact duplicate rows, keep the first. Raw 5,505 rows, expect 5,500.

**A2. Missing Provider_Name.** 328 blanks. Fill from Provider_ID using the Organisation table (the 8 names are consistent per Provider_ID).

**A3. Organisation duplicates.** Raw 10 rows, expect 8 (one per Provider_ID). Keep the first listed name per Provider_ID: "Charles Darwin University" for P001 and "NT Skills & Training Pty Ltd" for P003.

**A4. Nominal_Hours.** The column is stored as text. 163 blanks plus 107 unparseable values (for example "thirty" = 30, "-", and a few other text forms). Convert to numeric, then rebuild blanks and unparseable values from a Unit_ID lookup (each Unit_ID has exactly one valid value in the data). Report any Unit_ID that cannot be recovered; do not guess.

**A5. Gender.** Standardise "Male", "male" to M and "FEMALE", "female" to F. Expected counts after: F 670, M 647, X 657.

**A6. ATSI.** Standardise "y", "yes", "Yes", "YES" to Y. Expected counts after: Y 702, N 1,272.

**A7. Invalid start dates.** 8 rows have Enrol_Start_Date in 2030. Set Enrol_Start_Date to null for these and add `Start_Date_Invalid = True`. Delivery_Year is always valid and remains the reporting year.

**A8. Contract totals.**
- Keep Target_AHC_Total as given where it is non-zero (ignore the +/-1 rounding differences against the three parts).
- DCVT-2008 and DCVT-2021 have a Total of 0 but real regional targets: set Total to the sum of Urban, Regional and Remote (24,870 and 43,440).
- DCVT-2020 has all zeros: set the target to null and `Target_Status = "No target set"`. Do not treat it as a target of zero.
- Add `Target_Total_Source` ("as given" or "rebuilt from parts") and `Target_Status`.

**A9. Students with no enrolments.** 771 of 1,974 students have no enrolment. Keep them, and add `Has_Enrolment` (True/False). Participation analysis later uses the 1,203 students with enrolments.

## Judgement calls (decisions already made)

**B1. Contracts vs delivery.** Match on Provider_ID + Funding_Source only.
- Build `contract_delivery_recon.csv` with one row per Provider_ID + Funding_Source combination found in either sheet, with: status (Matched, Delivery without contract, Contract without delivery), target total, cumulative 2023 to 2025 AHC_Funded, and the three remoteness targets with matching delivered AHC.
- Expected before UNK recovery: 20 Matched (including DCVT-2020 as "No target set"), 16 Delivery without contract (excluding UNK), 3 Contract without delivery (all P008: 11J, 11N, 11V), and 8 UNK combinations listed separately.
- Do not drop or force-match anything. P008's 710 enrolments are all FFT and P008 has no FFT contract: flag this as a reconciliation discrepancy to verify with the data owner, not as a breach.

**B2. Unknown funding source.** 30 rows coded UNK.
- Try recovery: for a UNK row, if the same Student_ID + Provider_ID + Program_ID has exactly one distinct non-UNK Funding_Source on other rows, use it and set `Funding_Source_Recovered = True`.
- Otherwise set Funding_Source to "Unknown". These rows stay in overall totals and are excluded from stream-level and contract comparisons.
- Report how many were recovered.

**B3. Funded_Flag.** Do not change it and do not re-derive it. The data dictionary describes 85%_only as "cancelled/withdrawn", but those 960 rows are outcomes 51, 52 and 70, so the flag actually behaves as an 85/15 funding-timing rule. Use `AHC_Funded` (complete, consistent with the flag at 100%/85%/15%/0%) as the single source of truth for funded hours. Use Delivery_Year as the reporting year. Add `Carry_Over_Flag = True` where Delivery_Year is later than the year of a valid Enrol_Start_Date. Record the dictionary conflict in the data quality summary.

**B4. At_School_Flag.** Keep the column. Add:
- `Age_at_Enrolment` (completed years, from DOB and Enrol_Start_Date; where the start date is null use 1 July of Delivery_Year)
- `At_School_Suspect = True` where At_School_Flag is Y and Age_at_Enrolment is over 19
VET in Schools is defined later by funding stream (11N and 11V), not by this flag. Report how many rows are suspect and how many 11N/11V rows are flagged as not at school (expected about 1,061 of 1,152).

**B5. Gender X.** 657 of 1,974 students (about a third) is unusually high and the dictionary code list looks truncated. Clean the codes (A5) and keep X, but note in the summary that gender is not to be used for headline findings.

**B6. Targets are 3-year totals.** All contracts run 1 Jan 2023 to 31 Dec 2025. Do not pro-rate by year. Delivered AHC is compared with targets as a cumulative 2023 to 2025 figure.

## Derived outcome grouping
Add `Outcome_Group` and `In_Completion_Rate` to Enrolment:

| Outcome codes | Outcome_Group | In_Completion_Rate |
|---|---|---|
| 20, 51, 52 | Achieved | True |
| 30 | Not achieved | True |
| 40 | Withdrawn | True |
| 70 | Continuing | False |
| 60, 61, 85 | Not funded / not started | False |
| 81, 82 | Learner support | False |

Completion rate (used later) = Achieved / (Achieved + Not achieved + Withdrawn).

## Validation (assert in the script, stop on failure)
- Enrolment rows after A1 = 5,500; Organisation rows = 8; Contract rows = 23; Student rows = 1,974
- No null Provider_Name; Nominal_Hours numeric (list any exceptions)
- Gender only M/F/X; ATSI only Y/N
- No Student_ID in Enrolment missing from Student; USIs match between the two
- Total AHC_Funded after cleaning equals the raw total (172,964) minus the AHC_Funded of the 5 dropped duplicates; log both numbers
- Every row in Enrolment has an Outcome_Group

## When done
Show me `cleaning_log.csv` and `data_quality_summary.md`, and list anything unexpected or any count that differs from the expectations above.

## Writing standard (app build phase)

Every chart's title, caption and table reaches an Executive Director, not
an analyst. This holds across all charts, not just the one currently
being built:

- Write in plain English. Never use the words "pair", "comparable",
  "aggregate", "omnibus" or "cluster" in anything the reader sees (titles,
  captions, chart labels, table headers, expander labels, notes). Say
  "contract" or "contract with a target" instead. This does not apply to
  internal variable, function or column names - those stay as they are.
- Titles, captions and chart labels use whole numbers. Tables may keep
  one decimal place.
- Exception: where a difference between two figures is the point of the
  chart (for example a gap between two rates), show those figures to
  one decimal place so the displayed numbers add up.
- Where the data allow, a caption follows three beats: what we see, what
  it could mean, how sure we are. Never claim a cause. Never use
  "over-delivery" or "exceeds mandate".
- Every strong word in a caption (for example "pattern", "furthest
  behind") must be backed by a computed condition in the code that
  produces it. If that condition stops holding, the wording must change
  or the function must raise, never print stale or false wording - this
  is the same discipline `TitleAssumptionError` already enforces for
  titles (see lib/titles.py).

## Working agreement: app build phase (Streamlit app in app/)

Visual review of every chart is done manually, by the user, in the
browser. This means:

- No test renders an image, takes a screenshot, or measures pixels.
  `tests/` is data-integrity only: source-table lookups, number
  formatting, totals, row counts, and the assumption checks behind each
  generated title/caption (`TitleAssumptionError`).
- No script or dependency exists solely to produce a static preview of
  a chart (no `kaleido`, no `scripts/render_chart_previews.py`, no
  `outputs/chart_previews/`). These were built once and then removed
  for this reason.
- Never claim a chart "looks correct," "renders cleanly," or similar -
  that judgement is the user's, made in the browser, not something to
  assert from a rendered-and-inspected image.
- When a chart's code changes, say in plain words which function
  changed and which Plotly settings moved (margins, colours, label
  positions, axis/legend visibility, etc.), and what to look for in the
  browser to confirm it. The user checks the result; the response
  describes the change, not the outcome.
