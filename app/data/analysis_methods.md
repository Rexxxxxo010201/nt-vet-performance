# Analysis methods and definitions

## Core definitions (apply to every table)

- Funded hours means AHC_Funded. Total after cleaning: 172,794.
- Targets are 3-year totals covering 1 Jan 2023 to 31 Dec 2025. Delivered AHC is compared to targets as a cumulative 2023-2025 figure, never pro-rated by year.
- Contracts with matching delivery (19) are those matched on provider and funding stream, excluding the one pair with no target set (DCVT-2020 / P007-11V).
- Headline completion rate (unit level) = Achieved divided by Achieved plus Not achieved plus Withdrawn, counting only units in the completion-rate population. Achieved covers outcome codes 20, 51 and 52.
- Gender is excluded from every table (see the cleaning steps below: not reliable for headline findings).

## Statistical methods in plain words

A range (confidence interval) is the set of values the true figure could plausibly take. If a gap's range includes zero, the data cannot rule out no gap at all; if it excludes zero, the gap is unlikely to be chance.

Results are reproducible: every random step uses a fixed seed.

**Cluster bootstrap.** We re-ran each calculation 2,000 times, resampling students, to see how much a rate would move by chance; the range is the interval shown in the charts.

<span style='color:#6B7280;font-size:13px;'>Every confidence interval resamples students, not rows: for a given slice, distinct students are drawn with replacement (same count as the slice has), each draw carrying all of that student's eligible rows within the slice, and the rate is recomputed from the resampled total. This is done 2,000 times per interval and the reported interval is the 2.5th to 97.5th percentile of the resulting distribution, consumed in table order (T01, then T07, then T09), so rerunning the script reproduces every number exactly.</span>

**Subgroup bootstrap scope.** For a subgroup table (e.g. completion by Provider_ID), the bootstrap resamples only the students who have eligible rows in that subgroup, and only recomputes the rate from their rows within that subgroup - not their rows elsewhere in the data.

**ATSI gap interval.** The uncertainty range for the gap comes from resampling each group separately and looking at how much the difference between them moves.

<span style='color:#6B7280;font-size:13px;'>Because ATSI = Y and ATSI = N are disjoint student populations, the gap's confidence interval is built by independently bootstrapping each group's rate 2,000 times and taking the percentile interval of the elementwise difference - this is equivalent to the sampling distribution of two independent group means.</span>

**Group difference test.** Asks whether any group differs from the others by more than chance would produce; the p-value is the chance of seeing a spread this large if none did.

<span style='color:#6B7280;font-size:13px;'>For each of Funding_Source, Provider_ID, Remoteness and Industry, a separate univariate binomial GEE (completed ~ group, exchangeable correlation, clustered on student) is fit and a Wald test for the joint significance of that dimension's group indicators is reported. This tests whether this one dimension shows any group difference, unadjusted for the other dimensions - it is not a single model holding the other three constant.</span>

**Adjusted ATSI model.** Compares Aboriginal and Torres Strait Islander and other learners while holding provider, stream, region, industry and year the same.

<span style='color:#6B7280;font-size:13px;'>One binomial GEE regresses completion on ATSI, provider, funding stream, region, industry and year together, clustered on student with an exchangeable correlation structure. The ATSI odds ratio comes directly from its coefficient. The predicted completion rates for ATSI = Y and ATSI = N are standardised (g-computation): every eligible row's other covariates are kept as observed, ATSI is forced to each level in turn, the model predicts a probability for every row under that forced value, and the rates reported are the average predicted probability across all eligible rows.</span>

**One estimate per population, reused everywhere.** Every cluster-bootstrap rate (point estimate, CI, units, students, and the underlying 2,000 resample draws) is computed exactly once per distinct (population, definition) pair and cached by that key. T01's headline rate, T07's "Overall" and per-Funding_Source rows, and T10's standard-definition (a) rows all draw on the same cached estimate for a given slice, so the same slice never shows two different CIs across tables. T09's ATSI gap CIs are built from the same cached draws used for that slice's individual Y and N rate CIs in T09a, rather than a fresh, independent resample.

**Permutation chance check.** Reshuffles which programs each student took, 10,000 times, to see how uneven program sizes get by chance.

<span style='color:#6B7280;font-size:13px;'>This is a permutation test, not a bootstrap: each student keeps their observed number of distinct programs, but which programs are reassigned at random, without replacement, uniformly from all 10 programs, independently per student per permutation (10,000 permutations). The null statistic is the spread (max minus min) of the resulting students-per-program counts; the reported range is its 2.5th to 97.5th percentile, and the p-value is two-sided: 2 times the smaller of P(null at or above observed) and P(null at or below observed), capped at 1.</span>

**Reach share interval.** This gives a likely range for each group's Aboriginal and Torres Strait Islander share, based on how many students are in that group.

<span style='color:#6B7280;font-size:13px;'>An enrolled student is a distinct Student_ID with at least one row in the cleaned Enrolment table (any outcome); 1,203 students. ATSI status comes from the cleaned Student table (Y or N). A student counts in a group (Funding_Source after cleaning, Provider_ID, or Remoteness) if they have at least one enrolment row in that group, so a student can appear in several groups within a dimension. Each share is the number of ATSI = Y students over the number of students in the group, with a 95% Wilson score interval.</span>

**Reach group difference test.** Asks whether any group's Aboriginal and Torres Strait Islander share differs from the others by more than chance would produce.

<span style='color:#6B7280;font-size:13px;'>For each of Funding_Source, Provider_ID and Remoteness, a binomial GEE is fit on one row per student-group membership, with outcome ATSI (1 for Y, 0 for N), the group as the only predictor, an exchangeable correlation structure, and clustering on student. The reported p-value is the Wald test for any group difference. Because a student can appear in several groups, the rows are not independent; clustering on student is what accounts for that.</span>

## Judgement calls (stated, not silently assumed)

- T08b reports the At_School_Flag = N share and the At_School_Suspect = True share as two separate columns (not a combined OR share), each out of all 11N/11V rows for that Remoteness.
- T02/T04's "blank where none" is implemented as: Target_AHC is blank only where no contract exists for that pair (a true missing value); Delivered_AHC is 0 where a contract exists but no delivery occurred (a real zero, not missing).
- T02d's two uncontracted-excluding-11K shares share the same numerator (delivery-without-a-contract AHC minus 11K's uncontracted AHC): (a) divides by total AHC (so 11K is removed from the numerator only, and still counted in the denominator); (b) divides by total AHC minus all 11K AHC (contracted and uncontracted), so 11K is removed from both numerator and denominator.
- T09b's multiple-comparisons note counts the 8 regional and funding-stream gaps (3 Remoteness, 5 Funding_Source) as the relevant comparison set; the Overall row is the headline comparison, not one of the 8, since it is not a subgroup.
- T01's enrolled-student ATSI share uses the students with at least one enrolment row (1,203 students), since that is what "share of enrolled students" means here: 36.3%.
- T10(d) excludes rows recovered from an unknown funding source in cleaning (the 30 rows recovered from UNK); there are 0 rows still coded 'Unknown' to exclude, confirming recovery was complete.
- T12b's and T15's Short_Label is a hand-written lookup, not an algorithm - each of the 10 programs was given a short label by eye. T12b's Full_Label column carries the full Program_Name alongside it, for use anywhere that can show the full name on hover or on request.
- Claims 12 and 13 call an industry-mix gap 'material' above 10 percentage points; between 5 and 10 points it is reported as a modest (PARTLY) difference, and below 5 points as not material. This threshold is a judgement call, not a statistical test.