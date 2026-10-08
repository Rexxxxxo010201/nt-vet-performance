# Pathway check: FSK10213 to higher qualifications

Read-only verification against `data/clean/enrolment.csv` only, recomputed from scratch - no number here is taken from any earlier report. Every number below is an aggregate count; no Student_ID, USI, or other per-student row appears anywhere in this document.

## Definitions

Work is at student level. Lower program = FSK10213. Higher programs = every Program_ID whose Program_Name contains 'Certificate II' or 'Certificate III' (matched with a word-boundary regex, so 'Certificate III' is never counted as also matching 'Certificate II'). Only rows with a valid Enrol_Start_Date are used for any timing comparison; the 8 rows with an invalid (2030) start date are excluded from timing, same as in the cleaning step (A7), where they already carry a null Enrol_Start_Date. A student's start in a program is their earliest valid start date in that program.

Rows excluded from all timing comparisons for an invalid or missing Enrol_Start_Date: **8**.

## Higher programs identified (Certificate II or III)

| Program_ID | Program_Name |
|---|---|
| AHC20116 | Certificate II in Agriculture |
| BSB20120 | Certificate II in Business |
| BSB30120 | Certificate III in Business |
| CER30115 | Certificate III in Early Childhood Education and Care |
| CHC33015 | Certificate III in Individual Support |
| HLT33015 | Certificate III in Allied Health Assistance |
| RII20715 | Certificate II in Resources and Infrastructure |
| SIS30321 | Certificate III in Fitness |

## 1. FSK10213 learners

| Metric | Count |
|---|---|
| Distinct students with any FSK10213 enrolment | 170 |

## 2-3. FSK10213 to any Certificate II or III

### FSK10213 -> any Certificate II or III

| Metric | Count |
|---|---|
| Distinct students with any FSK10213 enrolment | 170 |
| ...of whom also have any enrolment in a higher program | 102 (60.0% of lower-program learners) |

| Metric | Count |
|---|---|
| Students in both, excluded from order comparison (missing valid date, either side) | 0 |
|   - missing valid lower-program date | 0 |
|   - missing valid higher-program date | 0 |
| Students in both with valid dates on both sides (order comparison population) | 102 |
| Started lower program strictly first | 39 |
| Started both on the same date | 0 |
| Started a higher program strictly first | 63 |

| Alternative definition | Count |
|---|---|
| Students in both, excluded (missing valid lower-program date) | 0 |
| Eligible for alternative check | 102 |
| ...with any higher-program enrolment starting after their lower-program start | 53 |

Students in both as a share of all FSK10213 learners: **102 / 170 = 60.0%**.

## 4. Achievement among students who started FSK10213 first

| Metric | Count | Of |
|---|---|---|
| Started FSK10213 strictly first | 39 | 39 |
| ...with >=1 Achieved unit in FSK10213 | 35 | 39 |
| ...with >=1 Achieved unit in a higher program | 34 | 39 |
| ...with >=1 Achieved unit in both | 33 | 39 |

## 5. Achievement among all students in both programs (regardless of order)

| Metric | Count | Of |
|---|---|---|
| Students in both programs | 102 | 102 |
| ...with >=1 Achieved unit in FSK10213 | 89 | 102 |
| ...with >=1 Achieved unit in a higher program | 90 | 102 |

## 6. Chance benchmark: random order of FSK10213 vs higher-program start

Among the 102 students in both programs with a valid start date on each side, each student's two actual start dates are kept, but which one is labelled 'FSK10213' and which is labelled 'higher program' is randomised with a fair coin, independently per student per permutation (10,000 permutations, seed 42). Same-date students never count as 'FSK first' under any labelling, since swapping identical dates changes nothing.

| Metric | Value |
|---|---|
| Observed: started FSK10213 strictly first | 39 |
| Observed: started both on the same date | 0 |
| Observed: started a higher program strictly first | 63 |
| Expected FSK-first under random order (mean) | 50.9 |
| Expected FSK-first under random order (95% range) | 41 to 61 |

The observed count (39) sits **below** the 95% range expected under random ordering (41 to 61).

## 7. BSB20120 to BSB30120, and CER30115 to CER40115

### BSB20120 -> BSB30120

| Metric | Count |
|---|---|
| Distinct students with any BSB20120 enrolment | 169 |
| ...of whom also have any enrolment in a higher program | 16 (9.5% of lower-program learners) |

| Metric | Count |
|---|---|
| Students in both, excluded from order comparison (missing valid date, either side) | 0 |
|   - missing valid lower-program date | 0 |
|   - missing valid higher-program date | 0 |
| Students in both with valid dates on both sides (order comparison population) | 16 |
| Started lower program strictly first | 10 |
| Started both on the same date | 0 |
| Started a higher program strictly first | 6 |

| Alternative definition | Count |
|---|---|
| Students in both, excluded (missing valid lower-program date) | 0 |
| Eligible for alternative check | 16 |
| ...with any higher-program enrolment starting after their lower-program start | 10 |

### CER30115 -> CER40115

| Metric | Count |
|---|---|
| Distinct students with any CER30115 enrolment | 177 |
| ...of whom also have any enrolment in a higher program | 19 (10.7% of lower-program learners) |

| Metric | Count |
|---|---|
| Students in both, excluded from order comparison (missing valid date, either side) | 0 |
|   - missing valid lower-program date | 0 |
|   - missing valid higher-program date | 0 |
| Students in both with valid dates on both sides (order comparison population) | 19 |
| Started lower program strictly first | 10 |
| Started both on the same date | 0 |
| Started a higher program strictly first | 9 |

| Alternative definition | Count |
|---|---|
| Students in both, excluded (missing valid lower-program date) | 0 |
| Eligible for alternative check | 19 |
| ...with any higher-program enrolment starting after their lower-program start | 10 |

## 8. FSK-first students: same provider or different provider for the higher program

Provider is taken from the specific enrolment row that set each student's earliest valid start date in that program; where more than one row is tied for the earliest date, the smallest Provider_ID is used as a deterministic tie-break (stated as an assumption, not silently applied).

| Metric | Count |
|---|---|
| FSK-first students resolved to a provider on both sides | 39 |
| ...same provider for both FSK10213 and the higher program | 2 |
| ...different provider for the higher program | 37 |

## Claim checks

### A. "102 is the number of students enrolled in FSK10213."

Distinct students with any FSK10213 enrolment (item 1): 170. 102 is the number of students in BOTH FSK10213 and a higher program (item 2), a different and smaller population - it is not the count this statement describes.

**Verdict: FALSE**

### B. "89 is the number of students who achieved units in the higher qualification."

Students in both programs with >=1 Achieved unit in a higher program (item 5): 90. Students in both programs with >=1 Achieved unit in FSK10213 (item 5): 89. 89 does not match the higher-program figure; among students in both programs, 89 is instead very close to (or equal to) the FSK10213 (lower-program) achievement figure, not the higher-qualification one.

**Verdict: FALSE**

### C. "Most students enrolled in both programs started FSK10213 first."

Of the 102 students in both programs with a valid date on each side: 39 started FSK10213 first, 0 started both on the same date, 63 started a higher program first. 39 of 102 is 38.2% (not a majority).

**Verdict: FALSE**

### D. "The data shows more movement from FSK10213 into higher programs than random ordering would produce."

Observed FSK-first count: 39. Expected under random order: mean 50.9, 95% range 41 to 61. The observed count sits below that range.

**Verdict: FALSE**

## Unexpected findings and assumptions

- Unexpected: of the 102 students in both FSK10213 and a higher program, more started a higher program first (63) than started FSK10213 first (39). This is not just a failure to confirm claim D ('more movement than chance') - the observed FSK-first count sits below the 95% chance range, meaning the data shows less FSK-to-higher ordering than random chance would produce, the opposite of what claim D asserts.

- Unexpected: among the 39 FSK-first students, only 2 stayed with the same provider for their higher-program enrolment; 37 moved to a different provider. Provider-switching is close to universal in this (small) group, not an occasional pattern.

- Assumption: for item 3's alternative definition, a student whose higher-program rows all lack a valid start date is scored as 'no' (not excluded), since there is no confirmed later-starting row to point to; only a missing lower-program start date excludes a student from that check.

- Assumption: item 8's provider attribution uses the single row that set a student's earliest valid start date in each program; a tie between providers on the exact same earliest date is broken by the smallest Provider_ID.

- Claims A and B both reuse a number from an earlier report (102 students in both programs, and an achievement count) but misattribute what population or program that number described; recomputing from scratch here is what surfaces the misattribution rather than confirming the claim.
