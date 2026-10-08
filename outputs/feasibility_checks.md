# Feasibility checks

Read-only checks against `data/clean/`. No cleaned file is modified. No USI, DOB, or other student-level rows are shown below - every number is an aggregate count or statistic. "Student-program" means a distinct Student_ID + Provider_ID + Program_ID combination, as defined in the brief.

## 1. Unit of analysis and cluster size

| Metric | Count |
|---|---|
| Enrolment rows | 5,500 |
| Distinct students (with >=1 enrolment) | 1,203 |
| Distinct student-programs | 1,895 |

| Distribution | Mean | Median | Max |
|---|---|---|---|
| Rows per student | 4.6 | 3 | 22 |
| Rows per student-program | 2.9 | 3 | 6 |

| Metric | Count |
|---|---|
| Student-programs with >=1 completion-eligible unit | 1,886 |
| ...of which every completion-eligible unit shares the same Outcome_Group | 721 (38.2%) |

*Assumption: the share is computed over student-programs that have at least one completion-eligible unit (In_Completion_Rate = True); student-programs with zero completion-eligible units are excluded from this share rather than counted as vacuously consistent.*

**What this means for the analysis:** Most student-programs have very few rows (see median above), so later checks that treat a student-program as one unit are not dominated by a handful of large clusters; where the same-Outcome_Group share is well below 100%, student-program-level completion needs the explicit "all completion-eligible units Achieved" rule used in sections 6 and 8, not a single row's Outcome_Group.

## 2. Is 2025 a complete year?

| Delivery_Year | Rows | AHC_Funded |
|---|---|---|
| 2023 | 1,110 | 36,839 |
| 2024 | 2,438 | 82,309 |
| 2025 | 1,952 | 53,646 |

| Start month | 2023 | 2024 | 2025 |
|---|---|---|---|
| Jan | 79 | 210 | 153 |
| Feb | 122 | 259 | 99 |
| Mar | 102 | 243 | 121 |
| Apr | 107 | 270 | 145 |
| May | 88 | 236 | 136 |
| Jun | 114 | 276 | 122 |
| Jul | 92 | 258 | 92 |
| Aug | 68 | 216 | 128 |
| Sep | 92 | 255 | 97 |
| Oct | 64 | 230 | 137 |
| Nov | 97 | 263 | 111 |
| Dec | 84 | 193 | 133 |

Max valid Enrol_Start_Date overall: **2025-12-28**

**What this means for the analysis:** If 2025's monthly start counts drop to (near) zero before December, or AHC_Funded for 2025 is noticeably lower than 2023/2024, any 2025 figure is an in-progress partial year and should be labelled as such rather than compared directly to the two completed years.

## 3. Cell sizes for comparisons

All counts below are distinct student-programs among completion-eligible rows (In_Completion_Rate = True) only.

*Assumption: Provider_ID is part of the student-program key, so its counts cannot double-count. Funding_Source, Remoteness, Industry and Delivery_Year are row-level attributes: if a single student-program has rows with more than one value of a given attribute, it is counted once in each value's cell for that attribute, so a column's cell counts can sum to more than the total number of distinct student-programs. ATSI is a student-level attribute (one value per student) so it does not have this issue.*

| Provider_ID | Student-programs |
|---|---|
| P001 | 240 |
| P002 | 228 |
| P003 | 226 |
| P004 | 242 |
| P005 | 237 |
| P006 | 227 |
| P007 | 243 |
| P008 | 243 |

Cells with fewer than 30 student-programs: **0** of 8.

| Funding_Source | Student-programs |
|---|---|
| 11J | 435 |
| 11K | 511 |
| 11N | 234 |
| 11V | 165 |
| FFT | 546 |

Cells with fewer than 30 student-programs: **0** of 5.

| Remoteness | Student-programs |
|---|---|
| Regional | 503 |
| Remote | 893 |
| Urban | 496 |

Cells with fewer than 30 student-programs: **0** of 3.

| Industry | Student-programs |
|---|---|
| Business | 353 |
| Community Services | 578 |
| Foundation Skills | 181 |
| Health | 190 |
| Primary Industry | 178 |
| Resources | 190 |
| Sport & Recreation | 216 |

Cells with fewer than 30 student-programs: **0** of 7.

| ATSI | Student-programs |
|---|---|
| N | 1,195 |
| Y | 691 |

Cells with fewer than 30 student-programs: **0** of 2.

| Delivery_Year | Student-programs |
|---|---|
| 2023 | 385 |
| 2024 | 835 |
| 2025 | 671 |

Cells with fewer than 30 student-programs: **0** of 3.

| Provider_ID \ Funding_Source | 11J | 11K | 11N | 11V | FFT |
|---|---|---|---|---|---|
| P001 | 65 | 73 | 33 | 22 | 48 |
| P002 | 62 | 61 | 34 | 28 | 43 |
| P003 | 55 | 73 | 37 | 16 | 45 |
| P004 | 65 | 90 | 27 | 25 | 36 |
| P005 | 52 | 79 | 41 | 24 | 42 |
| P006 | 67 | 56 | 34 | 18 | 52 |
| P007 | 69 | 79 | 28 | 32 | 37 |
| P008 | 0 | 0 | 0 | 0 | 243 |

Cells with fewer than 30 student-programs: **12** of 40 possible combinations (includes 4 combination(s) with zero student-programs; 36 combinations actually occur in the data).

| Remoteness \ ATSI | N | Y |
|---|---|---|
| Regional | 321 | 182 |
| Remote | 559 | 334 |
| Urban | 318 | 178 |

Cells with fewer than 30 student-programs: **0** of 6 possible combinations (includes 0 combination(s) with zero student-programs; 6 combinations actually occur in the data).

| Industry \ ATSI | N | Y |
|---|---|---|
| Business | 204 | 149 |
| Community Services | 384 | 194 |
| Foundation Skills | 114 | 67 |
| Health | 120 | 70 |
| Primary Industry | 123 | 55 |
| Resources | 120 | 70 |
| Sport & Recreation | 130 | 86 |

Cells with fewer than 30 student-programs: **0** of 14 possible combinations (includes 0 combination(s) with zero student-programs; 14 combinations actually occur in the data).

**What this means for the analysis:** Any comparison that conditions on a cell flagged below 30 student-programs is working with a small-sample cell; stream-level and intersectional (pairwise) breakdowns have far more such cells than single-dimension breakdowns, which limits how finely results can be sliced.

## 4. Funded hours by outcome

| Outcome_Group | AHC_Funded | Share of total |
|---|---|---|
| Achieved | 90,449 | 52.3% |
| Not achieved | 36,763 | 21.3% |
| Withdrawn | 25,318 | 14.7% |
| Continuing | 18,604 | 10.8% |
| Learner support | 1,660 | 1.0% |
| Not funded / not started | 0 | 0.0% |

| Funding_Source | Outcome_Group | AHC_Funded | Share within Funding_Source |
|---|---|---|---|
| 11J | Achieved | 21,124 | 53.8% |
| 11J | Not achieved | 8,211 | 20.9% |
| 11J | Withdrawn | 5,608 | 14.3% |
| 11J | Continuing | 3,984 | 10.1% |
| 11J | Learner support | 339 | 0.9% |
| 11J | Not funded / not started | 0 | 0.0% |
| 11K | Achieved | 23,821 | 50.3% |
| 11K | Not achieved | 10,732 | 22.7% |
| 11K | Withdrawn | 7,145 | 15.1% |
| 11K | Continuing | 5,183 | 11.0% |
| 11K | Learner support | 438 | 0.9% |
| 11K | Not funded / not started | 0 | 0.0% |
| 11N | Achieved | 11,085 | 49.1% |
| 11N | Not achieved | 5,095 | 22.6% |
| 11N | Withdrawn | 3,585 | 15.9% |
| 11N | Continuing | 2,485 | 11.0% |
| 11N | Learner support | 305 | 1.4% |
| 11N | Not funded / not started | 0 | 0.0% |
| 11V | Achieved | 9,000 | 54.4% |
| 11V | Not achieved | 3,200 | 19.3% |
| 11V | Withdrawn | 2,230 | 13.5% |
| 11V | Continuing | 1,960 | 11.8% |
| 11V | Learner support | 155 | 0.9% |
| 11V | Not funded / not started | 0 | 0.0% |
| FFT | Achieved | 25,419 | 54.0% |
| FFT | Not achieved | 9,525 | 20.2% |
| FFT | Withdrawn | 6,750 | 14.3% |
| FFT | Continuing | 4,992 | 10.6% |
| FFT | Learner support | 423 | 0.9% |
| FFT | Not funded / not started | 0 | 0.0% |

| Metric | Value |
|---|---|
| Rows: Outcome_Group in (Withdrawn, Not achieved) AND Funded_Flag = Y | 1,750 |
| AHC_Funded for those rows | 61,465 |

**What this means for the analysis:** AHC_Funded is concentrated in Achieved rows as expected; the rows flagged in the last table are where the funding-timing flag (Funded_Flag = Y, fully funded) and the training outcome (Withdrawn/Not achieved) point in different directions, so any funding-vs-outcome narrative should check this group rather than assume Funded_Flag tracks success.

## 5. Delivery mix vs contract mix

*Assumption: "matched Provider_ID + Funding_Source pairs" means Status = 'Matched' in contract_delivery_recon.csv, excluding the one pair with Target_Status = 'No target set' (DCVT-2020 / P007-11V), which has no usable target.*

| Provider_ID | Funding_Source | Target Urban% | Delivered Urban% | Target Regional% | Delivered Regional% | Target Remote% | Delivered Remote% |
|---|---|---|---|---|---|---|---|
| P001 | 11J | 47.4% | 21.4% | 23.7% | 28.9% | 28.9% | 49.7% |
| P001 | FFT | 42.2% | 27.8% | 27.6% | 17.4% | 30.2% | 54.8% |
| P002 | 11J | 39.4% | 26.9% | 20.9% | 34.0% | 39.7% | 39.1% |
| P002 | 11K | 43.8% | 20.4% | 21.1% | 34.7% | 35.1% | 44.8% |
| P002 | 11V | 35.3% | 31.2% | 39.8% | 28.3% | 24.9% | 40.5% |
| P002 | FFT | 32.6% | 27.5% | 20.0% | 25.4% | 47.4% | 47.1% |
| P003 | 11N | 56.1% | 23.4% | 29.0% | 27.3% | 14.9% | 49.3% |
| P003 | FFT | 36.1% | 19.7% | 25.8% | 24.9% | 38.1% | 55.4% |
| P004 | 11N | 55.9% | 30.5% | 34.9% | 18.6% | 9.2% | 50.9% |
| P004 | 11V | 37.9% | 27.8% | 26.7% | 16.3% | 35.4% | 55.9% |
| P004 | FFT | 57.1% | 35.1% | 23.9% | 26.0% | 19.0% | 38.9% |
| P005 | 11V | 31.6% | 19.5% | 21.8% | 24.2% | 46.6% | 56.3% |
| P005 | FFT | 43.1% | 37.2% | 29.7% | 26.7% | 27.3% | 36.2% |
| P006 | 11J | 36.4% | 25.4% | 26.4% | 25.8% | 37.1% | 48.8% |
| P006 | 11K | 55.9% | 21.6% | 20.4% | 32.4% | 23.7% | 46.0% |
| P006 | 11V | 59.3% | 19.3% | 25.2% | 21.1% | 15.5% | 59.6% |
| P006 | FFT | 47.0% | 13.2% | 29.4% | 25.4% | 23.6% | 61.4% |
| P007 | 11N | 50.1% | 35.5% | 35.4% | 29.0% | 14.6% | 35.5% |
| P007 | FFT | 55.7% | 34.8% | 20.5% | 16.0% | 23.9% | 49.2% |

| Provider_ID | Funding_Source | Delivered AHC as % of Target_AHC_Total |
|---|---|---|
| P001 | 11J | 15.2% |
| P001 | FFT | 15.0% |
| P002 | 11J | 50.8% |
| P002 | 11K | 21.7% |
| P002 | 11V | 11.3% |
| P002 | FFT | 10.7% |
| P003 | 11N | 14.0% |
| P003 | FFT | 14.1% |
| P004 | 11N | 6.7% |
| P004 | 11V | 5.0% |
| P004 | FFT | 15.7% |
| P005 | 11V | 19.1% |
| P005 | FFT | 8.1% |
| P006 | 11J | 21.2% |
| P006 | 11K | 18.0% |
| P006 | 11V | 5.3% |
| P006 | FFT | 9.1% |
| P007 | 11N | 7.0% |
| P007 | FFT | 12.7% |

| Statistic | Delivered AHC as % of Target_AHC_Total |
|---|---|
| Min across matched pairs | 5.0% |
| Median across matched pairs | 14.0% |
| Max across matched pairs | 50.8% |

| Scope | Total delivered AHC | Total target AHC | Delivered as % of target |
|---|---|---|---|
| Matched pairs only | 72,169 | 578,860 | 12.5% |
| All delivery vs all targets (every pair in the recon table) | 172,794 | 680,790 | 25.4% |

*Assumption: "all delivery vs all targets" sums Delivered_AHC_2023_2025 and Target_AHC_Total across every row of contract_delivery_recon.csv, including 'Delivery without contract' and 'Contract without delivery' rows (nulls contribute 0 to the respective sum), not only matched pairs.*

Matched pairs where at least one remoteness cell has Delivered AHC below 100 hours: **0** of 19.

**What this means for the analysis:** Where the delivered-as-%-of-target figure is far from 100% or a remoteness cell has very few delivered hours, a provider/stream-level comparison of delivery against target is being driven by a thin slice of hours rather than a full year's activity.

## 6. Adjusted equity gap feasibility

| ATSI | Completed student-programs | Non-completed student-programs |
|---|---|---|
| N | 398 | 797 |
| Y | 195 | 496 |

Total non-completions (student-programs with >=1 completion-eligible unit, not all Achieved): **1,293**.

*Assumption: rule-of-thumb guidance of ~10 non-completion events per predictor is applied to the rarer outcome class (non-completion) since it is smaller than the completion class here.*

| Grouping | Qualifying groups (ATSI=Y and ATSI=N both >=30 student-programs) |
|---|---|
| Program_ID | 10 |
| Provider_ID | 8 |

**What this means for the analysis:** An ATSI-adjusted completion comparison is only statistically meaningful where both the event count (non-completions) and the group cell sizes above clear usual minimums; the qualifying-group counts above show how many programs/providers that applies to, not whether a gap exists.

## 7. Pathways

| Pathway | Students in both programs | Lower started before higher | ...with >=1 Achieved unit in lower |
|---|---|---|---|
| BSB20120 -> BSB30120 | 16 | 10 (of 16 with valid dates) | 15 |
| CER30115 -> CER40115 | 19 | 10 (of 19 with valid dates) | 18 |
| FSK10213 -> any Certificate II or III | 102 | 39 (of 102 with valid dates) | 89 |

*Assumption: "started before" compares each student's earliest valid Enrol_Start_Date in the lower program against their earliest valid Enrol_Start_Date in the higher program; students missing a valid start date in either program are excluded from that count (denominator shown in parentheses). For the FSK10213 pathway, 'any Certificate II or III' is identified from Program_Name containing 'Certificate II' or 'Certificate III' and excludes FSK10213 itself (a Certificate I).*

Certificate II/III programs identified for the FSK10213 pathway: AHC20116, BSB20120, BSB30120, CER30115, CHC33015, HLT33015, RII20715, SIS30321.

| Metric | Count |
|---|---|
| Students with more than one distinct Program_ID | 481 |
| ...of which span more than one Provider_ID | 432 |

**What this means for the analysis:** Low counts of students in both programs of a pair mean a pathway progression analysis for that pair would rest on a small sample; the multi-program/multi-provider counts show how often enrolment history is genuinely cross-program or cross-provider at all.

## 8. Sensitivity of the completion rate

Student-program level completion, for every definition below, uses the rule in the brief: a student-program counts as completed if ALL of its eligible units (as defined for that variant) are Achieved, and it must have at least one eligible unit to be in the population.

## 8 (a) Standard: Achieved / (Achieved + Not achieved + Withdrawn)

| Scope | Unit-level completion rate | Eligible units | Student-program-level completion rate | Eligible student-programs |
|---|---|---|---|---|
| Overall | 60.4% | 4,734 | 31.4% | 1,886 |
| 11J | 60.9% | 1,099 | 31.5% | 435 |
| 11K | 59.0% | 1,289 | 29.5% | 511 |
| 11N | 57.2% | 573 | 28.6% | 234 |
| 11V | 62.3% | 424 | 33.3% | 165 |
| FFT | 62.0% | 1,349 | 34.1% | 546 |

*Assumption: "Achieved" uses Outcome_Group = 'Achieved', which already covers outcome codes 20, 51 and 52.*

## 8 (b) Outcome 20 only (RPL/credit transfer excluded from both numerator and denominator)

| Scope | Unit-level completion rate | Eligible units | Student-program-level completion rate | Eligible student-programs |
|---|---|---|---|---|
| Overall | 53.3% | 4,016 | 29.6% | 1,837 |
| 11J | 54.6% | 948 | 29.6% | 423 |
| 11K | 51.7% | 1,093 | 27.6% | 497 |
| 11N | 49.7% | 487 | 27.1% | 229 |
| 11V | 54.9% | 355 | 31.7% | 161 |
| FFT | 54.7% | 1,133 | 32.3% | 532 |

## 8 (c) Continuing included in the denominator as non-completion

| Scope | Unit-level completion rate | Eligible units | Student-program-level completion rate | Eligible student-programs |
|---|---|---|---|---|
| Overall | 53.2% | 5,369 | 19.2% | 1,895 |
| 11J | 54.0% | 1,239 | 20.8% | 437 |
| 11K | 51.8% | 1,470 | 17.3% | 514 |
| 11N | 50.8% | 646 | 17.8% | 236 |
| 11V | 54.5% | 484 | 18.7% | 166 |
| FFT | 54.6% | 1,530 | 20.7% | 547 |

## 8 (d) Excluding Funding_Source = Unknown (0 rows) and Funding_Source_Recovered rows (30 rows)

| Scope | Unit-level completion rate | Eligible units | Student-program-level completion rate | Eligible student-programs |
|---|---|---|---|---|
| Overall | 60.4% | 4,712 | 31.7% | 1,885 |
| 11J | 60.9% | 1,097 | 31.6% | 434 |
| 11K | 59.0% | 1,283 | 29.7% | 511 |
| 11N | 57.5% | 569 | 29.1% | 234 |
| 11V | 62.1% | 422 | 33.3% | 165 |
| FFT | 62.0% | 1,341 | 34.4% | 546 |

**What this means for the analysis:** Comparing (a) to (b)-(d) shows how much the headline completion rate moves under alternative, equally defensible definitions; if a Funding_Source's rate shifts by more than a point or two between variants, that stream's headline number is sensitive to the definition choice and should be reported with the definition stated explicitly.

## Checks that could not be run

None. Every check specified in the brief was run against `data/clean/` as described above.
