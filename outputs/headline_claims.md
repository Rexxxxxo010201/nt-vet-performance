# Headline claim checks

## 1. "Most delivered hours sit outside any contract."

Matched comparable pairs: 72,169 AHC (41.8%). Delivery without a contract: 97,550 AHC (56.5%). Matched but no target set: 3,075 AHC (1.8%). "Outside any contract" (delivery without a contract only, the literal reading of the claim) is 56.5% of total AHC, a majority.

**Verdict: SUPPORTED**

## 2. "Urban delivery falls below its contracted share in every comparable pair."

19 of 19 matched pairs have delivered Urban share below target Urban share (see t05a_pairs_geography.csv, Diff_pp < 0 for Urban). Delivered Urban share across the 19 pairs ranges 13.2% to 37.2% (mean 26.2%, SD 6.7pp); delivered Remote share ranges 35.5% to 61.4% (mean 48.4%, SD 7.8pp). This is a far narrower spread than the target shares (see t05a/t05b), so individual pairs deliver a broadly similar remoteness mix to each other, and the aggregate row in t05b_aggregate_geography.csv (Urban 25.6%, Remote 48.0%) is the primary evidence for claims 2 and 3, not pair-by-pair variation.

**Verdict: SUPPORTED**

## 3. "Remote delivery exceeds its contracted share in most comparable pairs."

17 of 19 matched pairs have delivered Remote share above target Remote share. See claim 2 above for the delivered-share dispersion figures across pairs; the same aggregate row in t05b_aggregate_geography.csv (Remote 48.0%) is the primary evidence here too.

**Verdict: SUPPORTED**

## 4. "More than a third of funded hours went to units that were not achieved or were withdrawn."

Withdrawn + Not achieved AHC: 62,081 of 172,794 total (35.9%).

**Verdict: SUPPORTED**

## 5. "Nearly all hours on withdrawn or not-achieved units are fully funded (Funded_Flag = Y)."

Of AHC on Withdrawn/Not-achieved units, 99.0% carries Funded_Flag = Y (see t06c).

**Verdict: SUPPORTED**

## 6. "Completion is about 60% in every stream and provider (use the CIs and omnibus p-values)."

Overall rate 60.4% (CI 59.0 to 61.8). Funding_Source rates range 57.2% to 62.3% (omnibus GEE p = 0.229, spread 5.1 pp). Provider_ID rates range 57.6% to 64.1% (omnibus GEE p = 0.272, spread 6.5 pp).

**Verdict: SUPPORTED**

## 7. "ATSI learners complete at a lower rate than non-ATSI learners (unadjusted and adjusted)."

Unadjusted gap (Y minus N): -2.8 pp (95% CI -5.6 to 0.1). Adjusted GEE odds ratio for ATSI = Y vs N: 0.88 (p = 0.0388); model-predicted gap -3.1 pp.

**Verdict: PARTLY**

## 11. "Funded hours are concentrated in a small number of industries."

Top 3 industries hold 70.9% of funded AHC; an even spread across all industries would give the top 3 42.9%.

**Verdict: SUPPORTED**

## 12. "Industry mix differs by remoteness."

The largest gap in any industry's share between two regions is 4.1 percentage points (Community Services, see t12c_industry_by_remoteness). This is small enough that it does not look material - the industry mix is close to uniform across Urban, Regional and Remote.

**Verdict: NOT SUPPORTED**

## 13. "Industry mix differs by funding stream."

The largest gap in any industry's share between two streams is 7.9 percentage points (Community Services, see t12c_industry_by_funding_source). This is a modest difference, not a dramatic one - no industry changes its overall ranking across streams.

**Verdict: PARTLY**

## 14. "Funded hours are concentrated at entry level (Certificate I to II)."

Certificate I + II hold 27.8% of funded AHC; Certificate III + IV hold 72.2% - the opposite pattern to the claim, with most funded hours at the higher levels (see t13_by_qualification_level for the per-level breakdown).

**Verdict: NOT SUPPORTED**

## 15. "Funded hours are concentrated in a few towns."

Top 1 town holds 13.7% of funded AHC; top 3 towns hold 40.3% (see t14_by_town). Across all towns the share ranges by only 2.6 percentage points - every one of the 8 towns holds a broadly similar share, the opposite of concentration.

**Verdict: NOT SUPPORTED**

## 16. "Student numbers are similar across the ten programs."

Distinct students per program range from 169 to 204 (ratio 1.21). The permutation chance check (t16_student_count_chance_check) gives a two-sided p-value of 0.7314 for this spread, meaning the observed variation is well within what random chance alone would produce once each student's number of programs is held fixed.

**Verdict: SUPPORTED**

## 17. "The three Community Services programs carry roughly twice the funded hours per unit of the other programs."

AHC_per_Unit: Community Services 46.1, other seven 24.5 (ratio 1.88). Mean_Nominal_Hours_per_Unit: 50.5 vs 27.5 (ratio 1.84). Mean_Funded_Fraction: 0.913 vs 0.892 (ratio 1.02). The AHC-per-unit ratio tracks the unit-length ratio almost exactly while the funded-fraction ratio sits close to 1, so the difference is accounted for arithmetically by longer units (Mean_Nominal_Hours_per_Unit), not a different funded fraction, which does not show why.

**Verdict: SUPPORTED**

## 18. "Certificate IV in Early Childhood Education and Care (CER40115) ranks second of ten programs by distinct students and by funded hours."

By distinct students: rank 2 of 10 with 191 students (neighbour above: 204; neighbour below: 187). By funded hours: rank 2 of 10 with 25,793 AHC (neighbour above: 31,357; neighbour below: 24,347). The student-count gap down to rank 3 is only 4 students.

**Verdict: SUPPORTED**

## 19. "Funded hours per student are about twice as high in the Community Services programs."

AHC_per_Student: Community Services 164.3, other seven 96.5 (ratio 1.70).

**Verdict: PARTLY**

## Additional claims the data supports

8. "P008 accounts for 21,678 AHC (712 enrolment rows) of FFT delivery without a matching FFT contract, while its 11J/11N/11V contracts have zero delivery." P008 is 22.2% of all delivery-without-a-contract AHC, so the remaining 15 pairs account for 75,872 AHC between them. Why it matters: this single provider drives both the biggest delivery-without-contract line and all three contract-without-delivery lines, so it is the first place a data owner should look, not a general funding-stream pattern - but most of the delivery-without-contract total (the other 77.8%) is spread across the other 15 pairs, not concentrated in P008 alone.
9. "Delivered AHC across matched pairs is nowhere near 100% of target" (min/median/max from t03a: see the table; every matched pair is under its 3-year target). Why it matters: before reading any provider as under-performing, the Executive Director needs to know this gap is universal, not provider-specific.
10. "2023 has no carry-in from 2022, and annual delivered AHC differs materially year to year" (see t11_context: 2023 = 36,839 AHC, 2024 = 82,309 AHC, 2025 = 53,646 AHC; the feasibility check shows valid Enrol_Start_Date values run through 28 Dec 2025, so 2025 is not an obviously incomplete year on that evidence alone). Why it matters: 2023 being a first-year-of-contract figure with no prior carry-over, combined with the year-to-year swings already in the data, means a year-over-year trend claim needs to account for this structural difference rather than treating all three years as comparable baselines.