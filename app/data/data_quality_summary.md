# NT VET data cleaning - data quality summary

## A3: Organisation duplicates

The Organisation table had 10 rows for 8 providers. P001 and P003 each appeared twice with slightly different names. We kept the first-listed name for each: 'Charles Darwin University' for P001 and 'NT Skills & Training Pty Ltd' for P003.

## A1: Enrolment duplicates

5 rows in Enrolment were exact duplicates of other rows. We kept the first occurrence of each and dropped the other 5, reducing 5,505 rows to 5,500.

## A2: Missing provider names

328 Enrolment rows had a blank Provider_Name. Each Provider_ID has exactly one organisation name, so we filled the blanks from the Organisation table. 0 rows remain blank after this fix.

## A4: Nominal_Hours text values

Nominal_Hours was stored as text. 269 rows were blank or unparseable (for example 'thirty', '-', 'TBD', 'unknown'). Each Unit_ID has exactly one valid hours value elsewhere in the data, so we converted the column to numeric and rebuilt the 269 bad values from that lookup. The original text is kept in Nominal_Hours_Raw for traceability.

## A5: Gender standardisation

Gender had case-variant spellings ('Male', 'male', 'FEMALE', 'female'). We standardised these to M/F. Final counts: F 670, M 647, X 657.

## A6: ATSI standardisation

ATSI had several variants of 'yes' ('y', 'yes', 'Yes', 'YES'). We standardised these to Y. Final counts: Y 702, N 1,272.

## A7: Invalid start dates

8 rows had an Enrol_Start_Date in 2030, which is not a valid training date in this dataset. We set the date to null and added Start_Date_Invalid = True for these rows. Delivery_Year is unaffected and remains the reporting year.

## A8: Contract totals

Target_AHC_Total was 0 for three contracts. DCVT-2008 and DCVT-2021 had real regional targets (Urban + Regional + Remote), so we rebuilt their totals from those parts (24,870 and 43,440). DCVT-2020 had all-zero values everywhere, so we set its target to null and Target_Status = 'No target set' rather than treating it as a target of zero. Target_Total_Source records whether each total is 'as given' or 'rebuilt from parts'. Separately, five contracts have a +/-1 difference between Target_AHC_Total and the sum of its three parts - DCVT-2005 (+1), DCVT-2006 (+1), DCVT-2011 (-1), DCVT-2018 (-1), DCVT-2019 (-1). These are treated as rounding differences, not data errors, and are left as given (Target_Total_Source = 'as given').

## B2: Unknown funding source

30 rows had Funding_Source = 'UNK'. 30 of these were recovered because the same student, provider and program had exactly one other, known funding source elsewhere in the data (Funding_Source_Recovered = True). The remaining 0 were set to 'Unknown'. These rows stay in overall totals but are excluded from stream-level and contract comparisons.

Recovered rows by Funding_Source:

| Funding_Source | Recovered rows |
|---|---|
| 11J | 2 |
| 11K | 8 |
| 11N | 7 |
| 11V | 3 |
| FFT | 10 |

Recovered rows by Provider_ID:

| Provider_ID | Recovered rows |
|---|---|
| P001 | 2 |
| P002 | 2 |
| P003 | 4 |
| P004 | 3 |
| P005 | 9 |
| P006 | 1 |
| P007 | 7 |
| P008 | 2 |

## A9: Students with no enrolments

771 of 1,974 students have no enrolment record. These are kept in the Student table with Has_Enrolment = False. Participation analysis later should use only the 1,203 students with Has_Enrolment = True.

## B3: Funded_Flag and carry-over (data dictionary conflict)

Funded_Flag was left exactly as supplied and was not re-derived. The data dictionary describes the 85%_only code as 'cancelled/withdrawn', but those 960 rows carry outcome codes 51, 52 and 70 (RPL granted, credit transfer, continuing) - not cancellation outcomes. In practice Funded_Flag behaves as an 85/15 funding-timing rule, not a cancellation flag. We treat AHC_Funded as the single source of truth for funded hours, since it is complete and consistent with the flag at 100%/85%/15%/0%. Delivery_Year is used as the reporting year. Carry_Over_Flag = True is added where Delivery_Year is later than the year of a valid Enrol_Start_Date (477 rows). Of those, 78 rows are also Funded_Flag = 'Y' (fully funded) despite being a carry-over enrolment.

## C1: Outcome grouping

Every Enrolment row is grouped into Outcome_Group (Achieved, Not achieved, Withdrawn, Continuing, Not funded / not started, or Learner support) and flagged In_Completion_Rate = True for the three groups (Achieved, Not achieved, Withdrawn) used in the completion-rate denominator.

## B4: At-school flag vs age and funding stream

At_School_Flag is kept unchanged. We added Age_at_Enrolment (completed years, from DOB and Enrol_Start_Date, or 1 July of Delivery_Year where the start date is null/invalid) and At_School_Suspect = True where At_School_Flag is Y but the student was over 19 (233 rows). VET in Schools is defined later by funding stream (11N and 11V), not by this flag: of 1,161 11N/11V rows, 1070 are flagged At_School_Flag != Y.

## B5: Gender X is unusually high

657 of 1,974 students (about a third) are coded Gender = X. This is unusually high for a non-binary code and the data dictionary's code list looks truncated. We cleaned the case variants (A5) and kept X as supplied, but gender should not be used for headline findings until this is clarified with the data owner.

## Validation: AHC_Funded total reconciliation

Raw AHC_Funded total across all 5,505 rows: 172,964. The 5 dropped duplicate rows (A1) account for 170 of that. Cleaned total after dedup: 172,794.

## B6: Targets are 3-year totals

All contracts run 1 Jan 2023 to 31 Dec 2025 and are not pro-rated by year. Target_AHC_Total (and the Urban/Regional/Remote targets, after A8) are 3-year totals for the whole contract period. Delivered AHC_Funded is therefore compared against each target as a single cumulative 2023-2025 figure, not year by year - this is the basis for the Delivered_AHC_2023_2025 columns in the B1 reconciliation below.

## B1: Contract vs delivery reconciliation

Matched on Provider_ID + Funding_Source only. Of 39 combinations found in either sheet: 20 are Matched, 16 are Delivery without contract, and 3 are Contract without delivery - all three are P008's 11J, 11N and 11V contracts. P008 has 712 FFT enrolments but no FFT contract. This is flagged as a reconciliation discrepancy to verify with the data owner, not treated as a compliance breach, and nothing is dropped or force-matched. All 30 originally-UNK rows were recovered to a real funding source (B2), so no 'UNK' combinations remain in this table.
