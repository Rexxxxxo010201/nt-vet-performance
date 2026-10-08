# Analysis tables - summary

Every table below is read from `data/clean/` only; no cleaned file was modified. Every table is an aggregate - no USI, DOB, or other student-level row appears anywhere in this document.

## t01_kpis

Headline KPIs: scale, completion rate, ATSI reach, and remoteness mix of funded AHC. Value_exact is a full-precision companion of Value (4 decimals where Value is itself rounded; the same number where Value is already an exact count), for whole-number rounding that must not double-round the one-decimal display column.

| Metric                                        |    Value |   CI_Lower |   CI_Upper |   Value_exact |
|:----------------------------------------------|---------:|-----------:|-----------:|--------------:|
| Total funded AHC                              | 172794   |        nan |      nan   |   172794      |
| Enrolment rows                                |   5500   |        nan |      nan   |     5500      |
| Distinct students                             |   1203   |        nan |      nan   |     1203      |
| Distinct providers                            |      8   |        nan |      nan   |        8      |
| Headline completion rate (%)                  |     60.4 |         59 |       61.8 |       60.3718 |
| Share of enrolled students with ATSI = Y (%)  |     36.3 |        nan |      nan   |       36.3259 |
| Share of funded AHC delivered in Urban (%)    |     25.9 |        nan |      nan   |       25.9245 |
| Share of funded AHC delivered in Regional (%) |     26.7 |        nan |      nan   |       26.6919 |
| Share of funded AHC delivered in Remote (%)   |     47.4 |        nan |      nan   |       47.3836 |

## t02a_coverage_summary

Funded AHC split by whether it sits in a matched, targetless, or contract-less pair.

| Coverage_Bucket                   |   AHC |   Share_of_Total_% |
|:----------------------------------|------:|-------------------:|
| Matched comparable pair           | 72169 |               41.8 |
| Matched pair, no target set       |  3075 |                1.8 |
| Delivery without a contract       | 97550 |               56.5 |
| Contract without delivery (0 AHC) |     0 |                0   |

## t02b_coverage_by_provider

Same coverage split as T02a, broken out by Provider_ID.

| Provider_ID   |   Matched comparable pair |   Matched pair, no target set |   Delivery without a contract |   Contract without delivery (0 AHC) |   Total_AHC |
|:--------------|--------------------------:|------------------------------:|------------------------------:|------------------------------------:|------------:|
| P001          |                     10460 |                             0 |                         12597 |                                   0 |       23057 |
| P002          |                     17132 |                             0 |                          3075 |                                   0 |       20207 |
| P003          |                      7292 |                             0 |                         13333 |                                   0 |       20625 |
| P004          |                      8060 |                             0 |                         14189 |                                   0 |       22249 |
| P005          |                      6529 |                             0 |                         15654 |                                   0 |       22183 |
| P006          |                     16968 |                             0 |                          3300 |                                   0 |       20268 |
| P007          |                      5728 |                          3075 |                         13724 |                                   0 |       22527 |
| P008          |                         0 |                             0 |                         21678 |                                   0 |       21678 |

## t02c_delivery_without_contract

The 16 Provider_ID + Funding_Source pairs with delivery but no matching contract, sorted by AHC.

| Provider_ID   | Funding_Source   |   AHC |   Share_of_Total_% | Flag_P008_FFT   |
|:--------------|:-----------------|------:|-------------------:|:----------------|
| P008          | FFT              | 21678 |               12.5 | True            |
| P005          | 11K              |  7973 |                4.6 | False           |
| P004          | 11K              |  7971 |                4.6 | False           |
| P007          | 11K              |  7266 |                4.2 | False           |
| P003          | 11K              |  6773 |                3.9 | False           |
| P001          | 11K              |  6742 |                3.9 | False           |
| P007          | 11J              |  6458 |                3.7 | False           |
| P004          | 11J              |  6218 |                3.6 | False           |
| P003          | 11J              |  5020 |                2.9 | False           |
| P005          | 11J              |  4016 |                2.3 | False           |
| P005          | 11N              |  3665 |                2.1 | False           |
| P001          | 11N              |  3530 |                2   | False           |
| P006          | 11N              |  3300 |                1.9 | False           |
| P002          | 11N              |  3075 |                1.8 | False           |
| P001          | 11V              |  2325 |                1.3 | False           |
| P003          | 11V              |  1540 |                0.9 | False           |

## t02d_uncontracted_excluding_11k

How much delivery-without-a-contract AHC remains once 11K's uncontracted delivery is set aside, as a share of total AHC and of non-11K AHC.

| Metric                                                                      |   Value |
|:----------------------------------------------------------------------------|--------:|
| Uncontracted (delivery without a contract) AHC for 11K only                 | 36725   |
| Uncontracted AHC, excluding 11K from the numerator                          | 60825   |
| (a) Share of total AHC (11K excluded from numerator only)                   |    35.2 |
| (b) Share of non-11K AHC only (11K excluded from numerator and denominator) |    48.5 |

## t03a_matched_pairs

Delivered AHC against the 3-year target for each of the 19 matched comparable pairs.

| Provider_ID   | Funding_Source   |   Delivered_AHC |   Target_AHC_Total |   Delivered_pct_of_Target |
|:--------------|:-----------------|----------------:|-------------------:|--------------------------:|
| P002          | 11J              |            5283 |              10400 |                      50.8 |
| P002          | 11K              |            5661 |              26130 |                      21.7 |
| P006          | 11J              |            6057 |              28610 |                      21.2 |
| P005          | 11V              |            2620 |              13710 |                      19.1 |
| P006          | 11K              |            4933 |              27330 |                      18   |
| P004          | FFT              |            3010 |              19180 |                      15.7 |
| P001          | 11J              |            6214 |              41000 |                      15.2 |
| P001          | FFT              |            4246 |              28280 |                      15   |
| P003          | FFT              |            3517 |              24870 |                      14.1 |
| P003          | 11N              |            3775 |              26870 |                      14   |
| P007          | FFT              |            3208 |              25230 |                      12.7 |
| P002          | 11V              |            2915 |              25890 |                      11.3 |
| P002          | FFT              |            3273 |              30510 |                      10.7 |
| P006          | FFT              |            4268 |              46970 |                       9.1 |
| P005          | FFT              |            3909 |              48070 |                       8.1 |
| P007          | 11N              |            2520 |              36170 |                       7   |
| P004          | 11N              |            2690 |              40280 |                       6.7 |
| P006          | 11V              |            1710 |              32490 |                       5.3 |
| P004          | 11V              |            2360 |              46870 |                       5   |

## t03b_rollups

Delivered-over-target roll-ups by Provider_ID and Funding_Source, plus the overall matched-pair total.

| Level          | Key               |   Delivered_AHC |   Target_AHC_Total |   Delivered_pct_of_Target |
|:---------------|:------------------|----------------:|-------------------:|--------------------------:|
| Funding_Source | 11J               |           17554 |              80010 |                      21.9 |
| Funding_Source | 11K               |           10594 |              53460 |                      19.8 |
| Funding_Source | FFT               |           25431 |             223110 |                      11.4 |
| Funding_Source | 11N               |            8985 |             103320 |                       8.7 |
| Funding_Source | 11V               |            9605 |             118960 |                       8.1 |
| Overall        | All matched pairs |           72169 |             578860 |                      12.5 |
| Provider_ID    | P002              |           17132 |              92930 |                      18.4 |
| Provider_ID    | P001              |           10460 |              69280 |                      15.1 |
| Provider_ID    | P003              |            7292 |              51740 |                      14.1 |
| Provider_ID    | P006              |           16968 |             135400 |                      12.5 |
| Provider_ID    | P005              |            6529 |              61780 |                      10.6 |
| Provider_ID    | P007              |            5728 |              61400 |                       9.3 |
| Provider_ID    | P004              |            8060 |             106330 |                       7.6 |

## t04_coverage_grid

Every Provider_ID x Funding_Source combination found in either sheet, with its status, delivered AHC, and target AHC.

| Provider_ID   | Funding_Source   | Status                    |   Delivered_AHC |   Target_AHC |
|:--------------|:-----------------|:--------------------------|----------------:|-------------:|
| P001          | 11J              | Matched                   |            6214 |        41000 |
| P001          | 11K              | Delivery without contract |            6742 |          nan |
| P001          | 11N              | Delivery without contract |            3530 |          nan |
| P001          | 11V              | Delivery without contract |            2325 |          nan |
| P001          | FFT              | Matched                   |            4246 |        28280 |
| P002          | 11J              | Matched                   |            5283 |        10400 |
| P002          | 11K              | Matched                   |            5661 |        26130 |
| P002          | 11N              | Delivery without contract |            3075 |          nan |
| P002          | 11V              | Matched                   |            2915 |        25890 |
| P002          | FFT              | Matched                   |            3273 |        30510 |
| P003          | 11J              | Delivery without contract |            5020 |          nan |
| P003          | 11K              | Delivery without contract |            6773 |          nan |
| P003          | 11N              | Matched                   |            3775 |        26870 |
| P003          | 11V              | Delivery without contract |            1540 |          nan |
| P003          | FFT              | Matched                   |            3517 |        24870 |
| P004          | 11J              | Delivery without contract |            6218 |          nan |
| P004          | 11K              | Delivery without contract |            7971 |          nan |
| P004          | 11N              | Matched                   |            2690 |        40280 |
| P004          | 11V              | Matched                   |            2360 |        46870 |
| P004          | FFT              | Matched                   |            3010 |        19180 |
| P005          | 11J              | Delivery without contract |            4016 |          nan |
| P005          | 11K              | Delivery without contract |            7973 |          nan |
| P005          | 11N              | Delivery without contract |            3665 |          nan |
| P005          | 11V              | Matched                   |            2620 |        13710 |
| P005          | FFT              | Matched                   |            3909 |        48070 |
| P006          | 11J              | Matched                   |            6057 |        28610 |
| P006          | 11K              | Matched                   |            4933 |        27330 |
| P006          | 11N              | Delivery without contract |            3300 |          nan |
| P006          | 11V              | Matched                   |            1710 |        32490 |
| P006          | FFT              | Matched                   |            4268 |        46970 |
| P007          | 11J              | Delivery without contract |            6458 |          nan |
| P007          | 11K              | Delivery without contract |            7266 |          nan |
| P007          | 11N              | Matched                   |            2520 |        36170 |
| P007          | 11V              | Matched                   |            3075 |          nan |
| P007          | FFT              | Matched                   |            3208 |        25230 |
| P008          | 11J              | Contract without delivery |               0 |        40690 |
| P008          | 11N              | Contract without delivery |               0 |        17800 |
| P008          | 11V              | Contract without delivery |               0 |        43440 |
| P008          | FFT              | Delivery without contract |           21678 |          nan |

## t05a_pairs_geography

Target vs delivered remoteness mix for each matched pair, and the gap in percentage points.

| Provider_ID   | Funding_Source   | Remoteness   |   Target_Share_% |   Delivered_Share_% |   Diff_pp |
|:--------------|:-----------------|:-------------|-----------------:|--------------------:|----------:|
| P001          | 11J              | Urban        |             47.4 |                21.4 |     -26.1 |
| P001          | 11J              | Regional     |             23.7 |                28.9 |       5.2 |
| P001          | 11J              | Remote       |             28.9 |                49.7 |      20.9 |
| P001          | FFT              | Urban        |             42.2 |                27.8 |     -14.4 |
| P001          | FFT              | Regional     |             27.6 |                17.4 |     -10.2 |
| P001          | FFT              | Remote       |             30.2 |                54.8 |      24.6 |
| P002          | 11J              | Urban        |             39.4 |                26.9 |     -12.5 |
| P002          | 11J              | Regional     |             20.9 |                34   |      13.1 |
| P002          | 11J              | Remote       |             39.7 |                39.1 |      -0.6 |
| P002          | 11K              | Urban        |             43.8 |                20.4 |     -23.3 |
| P002          | 11K              | Regional     |             21.1 |                34.7 |      13.6 |
| P002          | 11K              | Remote       |             35.1 |                44.8 |       9.7 |
| P002          | 11V              | Urban        |             35.3 |                31.2 |      -4.1 |
| P002          | 11V              | Regional     |             39.8 |                28.3 |     -11.5 |
| P002          | 11V              | Remote       |             24.9 |                40.5 |      15.6 |
| P002          | FFT              | Urban        |             32.6 |                27.5 |      -5.1 |
| P002          | FFT              | Regional     |             20   |                25.4 |       5.4 |
| P002          | FFT              | Remote       |             47.4 |                47.1 |      -0.3 |
| P003          | 11N              | Urban        |             56.1 |                23.4 |     -32.6 |
| P003          | 11N              | Regional     |             29   |                27.3 |      -1.8 |
| P003          | 11N              | Remote       |             14.9 |                49.3 |      34.4 |
| P003          | FFT              | Urban        |             36.1 |                19.7 |     -16.3 |
| P003          | FFT              | Regional     |             25.8 |                24.9 |      -0.9 |
| P003          | FFT              | Remote       |             38.1 |                55.4 |      17.3 |
| P004          | 11N              | Urban        |             55.9 |                30.5 |     -25.4 |
| P004          | 11N              | Regional     |             34.9 |                18.6 |     -16.3 |
| P004          | 11N              | Remote       |              9.2 |                50.9 |      41.8 |
| P004          | 11V              | Urban        |             37.9 |                27.8 |     -10.2 |
| P004          | 11V              | Regional     |             26.7 |                16.3 |     -10.4 |
| P004          | 11V              | Remote       |             35.4 |                55.9 |      20.6 |
| P004          | FFT              | Urban        |             57.1 |                35.1 |     -22   |
| P004          | FFT              | Regional     |             23.9 |                26   |       2.1 |
| P004          | FFT              | Remote       |             19   |                38.9 |      19.9 |
| P005          | 11V              | Urban        |             31.6 |                19.5 |     -12.1 |
| P005          | 11V              | Regional     |             21.8 |                24.2 |       2.5 |
| P005          | 11V              | Remote       |             46.6 |                56.3 |       9.7 |
| P005          | FFT              | Urban        |             43.1 |                37.2 |      -5.9 |
| P005          | FFT              | Regional     |             29.7 |                26.7 |      -3   |
| P005          | FFT              | Remote       |             27.3 |                36.2 |       8.9 |
| P006          | 11J              | Urban        |             36.4 |                25.4 |     -11.1 |
| P006          | 11J              | Regional     |             26.4 |                25.8 |      -0.6 |
| P006          | 11J              | Remote       |             37.1 |                48.8 |      11.7 |
| P006          | 11K              | Urban        |             55.9 |                21.6 |     -34.3 |
| P006          | 11K              | Regional     |             20.4 |                32.4 |      12   |
| P006          | 11K              | Remote       |             23.7 |                46   |      22.3 |
| P006          | 11V              | Urban        |             59.3 |                19.3 |     -40   |
| P006          | 11V              | Regional     |             25.2 |                21.1 |      -4.2 |
| P006          | 11V              | Remote       |             15.5 |                59.6 |      44.2 |
| P006          | FFT              | Urban        |             47   |                13.2 |     -33.8 |
| P006          | FFT              | Regional     |             29.4 |                25.4 |      -4   |
| P006          | FFT              | Remote       |             23.6 |                61.4 |      37.8 |
| P007          | 11N              | Urban        |             50.1 |                35.5 |     -14.5 |
| P007          | 11N              | Regional     |             35.4 |                29   |      -6.4 |
| P007          | 11N              | Remote       |             14.6 |                35.5 |      20.9 |
| P007          | FFT              | Urban        |             55.6 |                34.8 |     -20.9 |
| P007          | FFT              | Regional     |             20.5 |                16   |      -4.4 |
| P007          | FFT              | Remote       |             23.9 |                49.2 |      25.3 |

## t05b_aggregate_geography

Aggregate target vs delivered remoteness mix, summed across all 19 matched pairs.

| Remoteness   |   Target_AHC_Sum |   Delivered_AHC_Sum |   Target_Share_% |   Delivered_Share_% |   Diff_pp |   Delivered_pct_of_Target_% |
|:-------------|-----------------:|--------------------:|-----------------:|--------------------:|----------:|----------------------------:|
| Urban        |           265517 |               18475 |             45.9 |                25.6 |     -20.3 |                         7   |
| Regional     |           157385 |               19054 |             27.2 |                26.4 |      -0.8 |                        12.1 |
| Remote       |           155958 |               34640 |             26.9 |                48   |      21.1 |                        22.2 |

## t05c_geography_flags

How many of the 19 matched pairs under-deliver Urban or over-deliver Remote relative to target.

| Metric                                                   |   Count |   Of_pairs |
|:---------------------------------------------------------|--------:|-----------:|
| Pairs where Urban delivered share is below target share  |      19 |         19 |
| Pairs where Remote delivered share is above target share |      17 |         19 |

## t06a_ahc_by_funding_outcome

Funded AHC by Funding_Source and Outcome_Group, with share within stream and share of the grand total. Share_within_Stream_exact is a 4-decimal companion of Share_within_Stream_%, for whole-number rounding.

| Funding_Source   | Outcome_Group            |   AHC_Funded |   Share_within_Stream_% |   Share_Overall_% |   Share_within_Stream_exact |
|:-----------------|:-------------------------|-------------:|------------------------:|------------------:|----------------------------:|
| 11J              | Achieved                 |        21124 |                    53.8 |              12.2 |                     53.7972 |
| 11J              | Not achieved             |         8211 |                    20.9 |               4.8 |                     20.9112 |
| 11J              | Withdrawn                |         5608 |                    14.3 |               3.2 |                     14.2821 |
| 11J              | Continuing               |         3984 |                    10.1 |               2.3 |                     10.1462 |
| 11J              | Learner support          |          339 |                     0.9 |               0.2 |                      0.8633 |
| 11J              | Not funded / not started |            0 |                     0   |               0   |                      0      |
| 11K              | Achieved                 |        23821 |                    50.3 |              13.8 |                     50.3413 |
| 11K              | Not achieved             |        10732 |                    22.7 |               6.2 |                     22.6801 |
| 11K              | Withdrawn                |         7145 |                    15.1 |               4.1 |                     15.0996 |
| 11K              | Continuing               |         5183 |                    11   |               3   |                     10.9533 |
| 11K              | Learner support          |          438 |                     0.9 |               0.3 |                      0.9256 |
| 11K              | Not funded / not started |            0 |                     0   |               0   |                      0      |
| 11N              | Achieved                 |        11085 |                    49.1 |               6.4 |                     49.1465 |
| 11N              | Not achieved             |         5095 |                    22.6 |               2.9 |                     22.5892 |
| 11N              | Withdrawn                |         3585 |                    15.9 |               2.1 |                     15.8945 |
| 11N              | Continuing               |         2485 |                    11   |               1.4 |                     11.0175 |
| 11N              | Learner support          |          305 |                     1.4 |               0.2 |                      1.3523 |
| 11N              | Not funded / not started |            0 |                     0   |               0   |                      0      |
| 11V              | Achieved                 |         9000 |                    54.4 |               5.2 |                     54.3971 |
| 11V              | Not achieved             |         3200 |                    19.3 |               1.9 |                     19.3412 |
| 11V              | Withdrawn                |         2230 |                    13.5 |               1.3 |                     13.4784 |
| 11V              | Continuing               |         1960 |                    11.8 |               1.1 |                     11.8465 |
| 11V              | Learner support          |          155 |                     0.9 |               0.1 |                      0.9368 |
| 11V              | Not funded / not started |            0 |                     0   |               0   |                      0      |
| FFT              | Achieved                 |        25419 |                    54   |              14.7 |                     53.9578 |
| FFT              | Not achieved             |         9525 |                    20.2 |               5.5 |                     20.2191 |
| FFT              | Withdrawn                |         6750 |                    14.3 |               3.9 |                     14.3285 |
| FFT              | Continuing               |         4992 |                    10.6 |               2.9 |                     10.5967 |
| FFT              | Learner support          |          423 |                     0.9 |               0.2 |                      0.8979 |
| FFT              | Not funded / not started |            0 |                     0   |               0   |                      0      |

## t06b_sankey_links

Sankey-ready link table: Funding_Source to Outcome_Group, valued by AHC.

| source   | target                   |   value |
|:---------|:-------------------------|--------:|
| 11J      | Achieved                 |   21124 |
| 11J      | Not achieved             |    8211 |
| 11J      | Withdrawn                |    5608 |
| 11J      | Continuing               |    3984 |
| 11J      | Learner support          |     339 |
| 11J      | Not funded / not started |       0 |
| 11K      | Achieved                 |   23821 |
| 11K      | Not achieved             |   10732 |
| 11K      | Withdrawn                |    7145 |
| 11K      | Continuing               |    5183 |
| 11K      | Learner support          |     438 |
| 11K      | Not funded / not started |       0 |
| 11N      | Achieved                 |   11085 |
| 11N      | Not achieved             |    5095 |
| 11N      | Withdrawn                |    3585 |
| 11N      | Continuing               |    2485 |
| 11N      | Learner support          |     305 |
| 11N      | Not funded / not started |       0 |
| 11V      | Achieved                 |    9000 |
| 11V      | Not achieved             |    3200 |
| 11V      | Withdrawn                |    2230 |
| 11V      | Continuing               |    1960 |
| 11V      | Learner support          |     155 |
| 11V      | Not funded / not started |       0 |
| FFT      | Achieved                 |   25419 |
| FFT      | Not achieved             |    9525 |
| FFT      | Withdrawn                |    6750 |
| FFT      | Continuing               |    4992 |
| FFT      | Learner support          |     423 |
| FFT      | Not funded / not started |       0 |

## t06c_withdrawn_notachieved_by_funded_flag

AHC on withdrawn/not-achieved units, split by Funded_Flag, with the share flagged Y.

| Funded_Flag   |   AHC_Funded |   Share_% |
|:--------------|-------------:|----------:|
| Y             |        61465 |        99 |
| 15%_only      |          616 |         1 |

## t07_completion_by_group

Unit-level completion rate with 95% cluster-bootstrap CI, overall and by Funding_Source, Provider_ID, Remoteness, Industry, and Delivery_Year. Achieved_units/Rate_exact/Lower_exact/Upper_exact are full-precision companions of Units*Rate_%/Rate_%/CI_Lower/CI_Upper, for whole-number rounding that must not double-round the one-decimal display columns.

| Dimension      | Group              |   Rate_% |   CI_Lower |   CI_Upper |   Units |   Students |   Achieved_units |   Rate_exact |   Lower_exact |   Upper_exact |
|:---------------|:-------------------|---------:|-----------:|-----------:|--------:|-----------:|-----------------:|-------------:|--------------:|--------------:|
| Overall        | Overall            |     60.4 |       59   |       61.8 |    4734 |       1198 |             2858 |      60.3718 |       58.9869 |       61.7556 |
| Funding_Source | 11J                |     60.9 |       57.8 |       63.7 |    1099 |        389 |              669 |      60.8735 |       57.802  |       63.7019 |
| Funding_Source | 11K                |     59   |       56.3 |       61.7 |    1289 |        460 |              761 |      59.038  |       56.3203 |       61.7355 |
| Funding_Source | 11N                |     57.2 |       53.3 |       61.2 |     573 |        212 |              328 |      57.2426 |       53.2974 |       61.2178 |
| Funding_Source | 11V                |     62.3 |       58   |       67.1 |     424 |        162 |              264 |      62.2642 |       57.9671 |       67.0562 |
| Funding_Source | FFT                |     62   |       59.4 |       64.5 |    1349 |        468 |              836 |      61.9718 |       59.3682 |       64.485  |
| Provider_ID    | P001               |     60.4 |       56.7 |       64.1 |     624 |        227 |              377 |      60.4167 |       56.7038 |       64.0703 |
| Provider_ID    | P002               |     64.1 |       60   |       68.2 |     574 |        220 |              368 |      64.1115 |       60      |       68.1744 |
| Provider_ID    | P003               |     57.6 |       54   |       61.3 |     571 |        211 |              329 |      57.6182 |       53.9652 |       61.3129 |
| Provider_ID    | P004               |     58.5 |       54.6 |       62.3 |     602 |        229 |              352 |      58.4718 |       54.6409 |       62.3165 |
| Provider_ID    | P005               |     59   |       54.9 |       63.3 |     598 |        222 |              353 |      59.0301 |       54.9412 |       63.3333 |
| Provider_ID    | P006               |     58.8 |       54.5 |       63.4 |     549 |        212 |              323 |      58.8342 |       54.4658 |       63.3531 |
| Provider_ID    | P007               |     62   |       57.9 |       66   |     613 |        227 |              380 |      61.9902 |       57.8857 |       65.9811 |
| Provider_ID    | P008               |     62.4 |       58.1 |       66.2 |     603 |        229 |              376 |      62.3549 |       58.0529 |       66.2445 |
| Remoteness     | Regional           |     58.5 |       55.6 |       61.4 |    1247 |        447 |              729 |      58.4603 |       55.5916 |       61.3692 |
| Remoteness     | Remote             |     61.9 |       60   |       63.8 |    2250 |        707 |             1393 |      61.9111 |       59.9735 |       63.7705 |
| Remoteness     | Urban              |     59.5 |       56.7 |       62.2 |    1237 |        433 |              736 |      59.4988 |       56.6588 |       62.2099 |
| Industry       | Business           |     61.4 |       58.2 |       64.6 |     903 |        323 |              554 |      61.3511 |       58.2113 |       64.604  |
| Industry       | Community Services |     60.6 |       58.1 |       63   |    1532 |        496 |              928 |      60.5744 |       58.1145 |       63.0309 |
| Industry       | Foundation Skills  |     61.7 |       57.3 |       65.9 |     433 |        169 |              267 |      61.6628 |       57.3057 |       65.9211 |
| Industry       | Health             |     61.9 |       57.4 |       66.4 |     452 |        180 |              280 |      61.9469 |       57.3908 |       66.3809 |
| Industry       | Primary Industry   |     56.3 |       51.4 |       61   |     423 |        176 |              238 |      56.2648 |       51.3569 |       61.0183 |
| Industry       | Resources          |     60   |       55.3 |       64.6 |     467 |        185 |              280 |      59.9572 |       55.2909 |       64.5572 |
| Industry       | Sport & Recreation |     59.4 |       54.8 |       63.8 |     524 |        204 |              311 |      59.3511 |       54.8203 |       63.8072 |
| Delivery_Year  | 2023               |     60.2 |       57.1 |       63.3 |     954 |        354 |              574 |      60.1677 |       57.1132 |       63.3476 |
| Delivery_Year  | 2024               |     59.1 |       57   |       61.1 |    2104 |        673 |             1243 |      59.0779 |       57.0412 |       61.1389 |
| Delivery_Year  | 2025               |     62.1 |       59.7 |       64.7 |    1676 |        578 |             1041 |      62.1122 |       59.6783 |       64.6529 |

## t07_omnibus_tests

Omnibus GEE Wald test (any difference between groups) and max-minus-min spread, per dimension.

| Dimension      |   Omnibus_GEE_p_value |   Spread_pp |
|:---------------|----------------------:|------------:|
| Funding_Source |                0.229  |         5.1 |
| Provider_ID    |                0.2721 |         6.5 |
| Remoteness     |                0.1159 |         3.4 |
| Industry       |                0.6641 |         5.6 |

## t08a_atsi_reach

Share of units and share of funded AHC going to ATSI = Y, by Remoteness, Funding_Source, and Provider_ID.

| Dimension      | Group    |   Share_Units_ATSI_Y_% |   Share_AHC_ATSI_Y_% |   Units |
|:---------------|:---------|-----------------------:|---------------------:|--------:|
| Remoteness     | Regional |                   35.9 |                 35.4 |    1457 |
| Remoteness     | Remote   |                   37.8 |                 37.4 |    2603 |
| Remoteness     | Urban    |                   35.7 |                 35.4 |    1440 |
| Funding_Source | 11J      |                   34.4 |                 34   |    1266 |
| Funding_Source | 11K      |                   39.5 |                 39.6 |    1501 |
| Funding_Source | 11N      |                   40   |                 39.4 |     667 |
| Funding_Source | 11V      |                   37.4 |                 36.1 |     494 |
| Funding_Source | FFT      |                   34.5 |                 33.6 |    1572 |
| Provider_ID    | P001     |                   36.6 |                 36.2 |     708 |
| Provider_ID    | P002     |                   40.5 |                 39.7 |     665 |
| Provider_ID    | P003     |                   36.4 |                 35.7 |     656 |
| Provider_ID    | P004     |                   31.1 |                 30.8 |     711 |
| Provider_ID    | P005     |                   36.4 |                 35.4 |     681 |
| Provider_ID    | P006     |                   39.6 |                 41.8 |     657 |
| Provider_ID    | P007     |                   41.1 |                 41.3 |     710 |
| Provider_ID    | P008     |                   32.9 |                 30.3 |     712 |

## t08b_vet_in_schools

VET in Schools (11N/11V) AHC and units by Remoteness, with the At_School_Flag = N share and the At_School_Suspect = True share reported as separate columns.

| Remoteness   |   AHC |   Units |   Share_AtSchoolFlag_N_% |   Share_AtSchoolSuspect_True_% |
|:-------------|------:|--------:|-------------------------:|-------------------------------:|
| Regional     |  9820 |     284 |                     93.3 |                            4.2 |
| Remote       | 18895 |     566 |                     92   |                            4.2 |
| Urban        | 10385 |     311 |                     91.3 |                            4.8 |

## t08c_at_school_suspect_totals

Total rows and distinct students flagged At_School_Suspect across all of Enrolment.

| Metric                     |   Count |
|:---------------------------|--------:|
| At_School_Suspect rows     |     233 |
| At_School_Suspect students |      48 |

## t09a_unadjusted_completion_by_atsi

Unadjusted unit-level completion rate for ATSI Y and N, overall and by Remoteness and Funding_Source. Achieved_units/Rate_exact/Lower_exact/Upper_exact are full-precision companions, for whole-number rounding that must not double-round the one-decimal display columns.

| Dimension      | Group    | ATSI   |   Rate_% |   CI_Lower |   CI_Upper |   Units |   Achieved_units |   Rate_exact |   Lower_exact |   Upper_exact |
|:---------------|:---------|:-------|---------:|-----------:|-----------:|--------:|-----------------:|-------------:|--------------:|--------------:|
| Overall        | Overall  | Y      |     58.6 |       56.3 |       60.9 |    1729 |             1013 |      58.5888 |       56.3306 |       60.8841 |
| Overall        | Overall  | N      |     61.4 |       59.7 |       63.1 |    3005 |             1845 |      61.3977 |       59.6828 |       63.0765 |
| Remoteness     | Regional | Y      |     58.3 |       53.5 |       63.1 |     448 |              261 |      58.2589 |       53.5139 |       63.0672 |
| Remoteness     | Regional | N      |     58.6 |       55.1 |       62   |     799 |              468 |      58.5732 |       55.1423 |       62.0244 |
| Remoteness     | Remote   | Y      |     59.1 |       56.1 |       62.1 |     847 |              501 |      59.1499 |       56.0802 |       62.1283 |
| Remoteness     | Remote   | N      |     63.6 |       60.9 |       66.1 |    1403 |              892 |      63.578  |       60.8789 |       66.1213 |
| Remoteness     | Urban    | Y      |     57.8 |       53.4 |       62.3 |     434 |              251 |      57.8341 |       53.4403 |       62.2739 |
| Remoteness     | Urban    | N      |     60.4 |       56.8 |       63.8 |     803 |              485 |      60.3985 |       56.8264 |       63.8022 |
| Funding_Source | 11J      | Y      |     63.2 |       58.3 |       68   |     372 |              235 |      63.172  |       58.3103 |       67.9621 |
| Funding_Source | 11J      | N      |     59.7 |       56.1 |       63.2 |     727 |              434 |      59.6974 |       56.101  |       63.1945 |
| Funding_Source | 11K      | Y      |     57   |       52.7 |       61.3 |     514 |              293 |      57.0039 |       52.6908 |       61.2655 |
| Funding_Source | 11K      | N      |     60.4 |       56.5 |       63.9 |     775 |              468 |      60.3871 |       56.4557 |       63.8604 |
| Funding_Source | 11N      | Y      |     53.7 |       47.8 |       59.7 |     229 |              123 |      53.7118 |       47.7674 |       59.664  |
| Funding_Source | 11N      | N      |     59.6 |       54.1 |       64.7 |     344 |              205 |      59.593  |       54.0536 |       64.6579 |
| Funding_Source | 11V      | Y      |     61.1 |       52.1 |       69.5 |     149 |               91 |      61.0738 |       52.1112 |       69.5364 |
| Funding_Source | 11V      | N      |     62.9 |       57.3 |       68.6 |     275 |              173 |      62.9091 |       57.298  |       68.5612 |
| Funding_Source | FFT      | Y      |     58.3 |       54.1 |       62.6 |     465 |              271 |      58.2796 |       54.0536 |       62.5561 |
| Funding_Source | FFT      | N      |     63.9 |       60.6 |       67.2 |     884 |              565 |      63.914  |       60.6299 |       67.1546 |

## t09b_atsi_gap

ATSI completion gap (Y minus N) in percentage points, with cluster-bootstrap CI. The Overall row is the headline comparison; the other 8 rows (3 Remoteness, 5 Funding_Source) are the subgroup comparisons. At a 95% CI with no true effect in any subgroup, about 0.40 of 8 (5%) would be expected to exclude zero by chance alone. Gap_exact/Lower_exact/Upper_exact are full-precision companions of Gap_pp_Y_minus_N/CI_Lower/CI_Upper (Gap_exact from the two groups' unrounded rates, not their rounded display values), for whole-number or one-decimal rounding that must not double-round the display columns.

| Dimension      | Group    |   Gap_pp_Y_minus_N |   CI_Lower |   CI_Upper |   N_Comparisons_in_Table |   Gap_exact |   Lower_exact |   Upper_exact |
|:---------------|:---------|-------------------:|-----------:|-----------:|-------------------------:|------------:|--------------:|--------------:|
| Overall        | Overall  |               -2.8 |       -5.6 |        0.1 |                        9 |     -2.8089 |       -5.6094 |        0.0744 |
| Remoteness     | Regional |               -0.3 |       -6.2 |        5.8 |                        9 |     -0.3143 |       -6.2157 |        5.822  |
| Remoteness     | Remote   |               -4.4 |       -8.5 |       -0.4 |                        9 |     -4.4281 |       -8.5224 |       -0.4112 |
| Remoteness     | Urban    |               -2.6 |       -8.2 |        3.2 |                        9 |     -2.5644 |       -8.2105 |        3.2185 |
| Funding_Source | 11J      |                3.5 |       -2.4 |        9.5 |                        9 |      3.4746 |       -2.4498 |        9.4548 |
| Funding_Source | 11K      |               -3.4 |       -8.9 |        2.5 |                        9 |     -3.3832 |       -8.9342 |        2.5375 |
| Funding_Source | 11N      |               -5.9 |      -13.9 |        2.6 |                        9 |     -5.8812 |      -13.9154 |        2.5651 |
| Funding_Source | 11V      |               -1.8 |      -12.4 |        8   |                        9 |     -1.8353 |      -12.3589 |        8.0185 |
| Funding_Source | FFT      |               -5.6 |      -10.7 |       -0.2 |                        9 |     -5.6344 |      -10.681  |       -0.1888 |

## t09c_adjusted_gee

Adjusted binomial GEE (ATSI + Provider_ID + Funding_Source + Remoteness + Industry + Delivery_Year, clustered on student): ATSI odds ratio and standardised predicted completion rates. Value_exact is a full-precision (4 decimal) companion of Value, for rounding that must not double-round the display column.

| Metric                                        |   Value |   Value_exact |
|:----------------------------------------------|--------:|--------------:|
| ATSI odds ratio (Y vs N)                      |  0.88   |        0.8795 |
| OR 95% CI lower                               |  0.779  |        0.7787 |
| OR 95% CI upper                               |  0.993  |        0.9934 |
| OR p-value                                    |  0.0388 |        0.0388 |
| Model-predicted completion rate, ATSI = Y (%) | 58.4    |       58.4189 |
| Model-predicted completion rate, ATSI = N (%) | 61.5    |       61.4841 |
| Model-predicted gap, Y minus N (pp)           | -3.1    |       -3.0652 |

## t10_sensitivity

Completion rate under four alternative definitions, plus a labelled reference row for strict student-program completion. Rate_exact is a 4-decimal companion of Rate_%, for whole-number rounding.

| Definition                                                                                                                      | Scope   |   Rate_% |   CI_Lower |   CI_Upper |   Rate_exact |
|:--------------------------------------------------------------------------------------------------------------------------------|:--------|---------:|-----------:|-----------:|-------------:|
| (a) Standard unit-level                                                                                                         | Overall |     60.4 |       59   |       61.8 |      60.3718 |
| (a) Standard unit-level                                                                                                         | 11J     |     60.9 |       57.8 |       63.7 |      60.8735 |
| (a) Standard unit-level                                                                                                         | 11K     |     59   |       56.3 |       61.7 |      59.038  |
| (a) Standard unit-level                                                                                                         | 11N     |     57.2 |       53.3 |       61.2 |      57.2426 |
| (a) Standard unit-level                                                                                                         | 11V     |     62.3 |       58   |       67.1 |      62.2642 |
| (a) Standard unit-level                                                                                                         | FFT     |     62   |       59.4 |       64.5 |      61.9718 |
| (b) Outcome 20 only                                                                                                             | Overall |     53.3 |      nan   |      nan   |      53.2869 |
| (b) Outcome 20 only                                                                                                             | 11J     |     54.6 |      nan   |      nan   |      54.6414 |
| (b) Outcome 20 only                                                                                                             | 11K     |     51.7 |      nan   |      nan   |      51.6926 |
| (b) Outcome 20 only                                                                                                             | 11N     |     49.7 |      nan   |      nan   |      49.692  |
| (b) Outcome 20 only                                                                                                             | 11V     |     54.9 |      nan   |      nan   |      54.9296 |
| (b) Outcome 20 only                                                                                                             | FFT     |     54.7 |      nan   |      nan   |      54.722  |
| (c) Continuing counted as non-completion                                                                                        | Overall |     53.2 |      nan   |      nan   |      53.2315 |
| (c) Continuing counted as non-completion                                                                                        | 11J     |     54   |      nan   |      nan   |      53.9952 |
| (c) Continuing counted as non-completion                                                                                        | 11K     |     51.8 |      nan   |      nan   |      51.7687 |
| (c) Continuing counted as non-completion                                                                                        | 11N     |     50.8 |      nan   |      nan   |      50.774  |
| (c) Continuing counted as non-completion                                                                                        | 11V     |     54.5 |      nan   |      nan   |      54.5455 |
| (c) Continuing counted as non-completion                                                                                        | FFT     |     54.6 |      nan   |      nan   |      54.6405 |
| (d) Excluding Funding_Source_Recovered rows                                                                                     | Overall |     60.4 |      nan   |      nan   |      60.3778 |
| (d) Excluding Funding_Source_Recovered rows                                                                                     | 11J     |     60.9 |      nan   |      nan   |      60.8933 |
| (d) Excluding Funding_Source_Recovered rows                                                                                     | 11K     |     59   |      nan   |      nan   |      59.0023 |
| (d) Excluding Funding_Source_Recovered rows                                                                                     | 11N     |     57.5 |      nan   |      nan   |      57.4692 |
| (d) Excluding Funding_Source_Recovered rows                                                                                     | 11V     |     62.1 |      nan   |      nan   |      62.0853 |
| (d) Excluding Funding_Source_Recovered rows                                                                                     | FFT     |     62   |      nan   |      nan   |      61.9687 |
| REFERENCE: strict student-program (all eligible units Achieved) - NOT qualification completion, only units present in this data | Overall |     31.4 |      nan   |      nan   |      31.4422 |

## t11_context

Units, funded AHC, and valid-start-date counts by Delivery_Year and Funding_Source, with carry-over notes.

|   Delivery_Year | Funding_Source   |   Units |   AHC |   Valid_Start_Count | Note                                     |
|----------------:|:-----------------|--------:|------:|--------------------:|:-----------------------------------------|
|            2023 | 11J              |     261 |  8710 |                 260 | 2023 has no carry-in from 2022           |
|            2023 | 11K              |     272 |  8920 |                 272 | 2023 has no carry-in from 2022           |
|            2023 | 11N              |     129 |  4505 |                 129 | 2023 has no carry-in from 2022           |
|            2023 | 11V              |     108 |  3365 |                 108 | 2023 has no carry-in from 2022           |
|            2023 | FFT              |     340 | 11339 |                 340 | 2023 has no carry-in from 2022           |
|            2024 | 11J              |     580 | 19218 |                 578 |                                          |
|            2024 | 11K              |     658 | 22892 |                 657 |                                          |
|            2024 | 11N              |     300 | 10200 |                 300 |                                          |
|            2024 | 11V              |     221 |  7445 |                 219 |                                          |
|            2024 | FFT              |     679 | 22554 |                 678 |                                          |
|            2025 | 11J              |     425 | 11338 |                 425 | Carry_Over_Flag rows only appear in 2025 |
|            2025 | 11K              |     571 | 15507 |                 570 | Carry_Over_Flag rows only appear in 2025 |
|            2025 | 11N              |     238 |  7850 |                 238 | Carry_Over_Flag rows only appear in 2025 |
|            2025 | 11V              |     165 |  5735 |                 165 | Carry_Over_Flag rows only appear in 2025 |
|            2025 | FFT              |     553 | 13216 |                 553 | Carry_Over_Flag rows only appear in 2025 |

## t12a_by_industry

Funded AHC, units, students, completion rate (the cached T07 estimate for this Industry) and ATSI reach, by Industry, sorted by AHC descending. Contracts carry no industry, program or town targets, so no target comparison is possible for T12 to T14.

| Industry           |   AHC_Funded |   Share_of_Total_% |   Units |   Distinct_Students |   Completion_Rate_% |   CI_Lower |   CI_Upper |   Eligible_Units |   ATSI_Share_of_Units_% |
|:-------------------|-------------:|-------------------:|--------:|--------------------:|--------------------:|-----------:|-----------:|-----------------:|------------------------:|
| Community Services |        81497 |               47.2 |    1767 |                 496 |                60.6 |       58.1 |       63   |             1532 |                    33.7 |
| Business           |        25339 |               14.7 |    1064 |                 325 |                61.4 |       58.2 |       64.6 |              903 |                    42.3 |
| Sport & Recreation |        15690 |                9.1 |     599 |                 204 |                59.4 |       54.8 |       63.8 |              524 |                    40.4 |
| Health             |        14141 |                8.2 |     535 |                 182 |                61.9 |       57.4 |       66.4 |              452 |                    37.2 |
| Resources          |        14104 |                8.2 |     545 |                 187 |                60   |       55.3 |       64.6 |              467 |                    37.2 |
| Primary Industry   |        11197 |                6.5 |     492 |                 178 |                56.3 |       51.4 |       61   |              423 |                    29.9 |
| Foundation Skills  |        10826 |                6.3 |     498 |                 170 |                61.7 |       57.3 |       65.9 |              433 |                    37.3 |

## t12b_by_program

Funded AHC, units and students by Program, with a hand-written, glance-readable Short_Label and the Full_Label (the full Program_Name) for display alongside it.

| Program_ID   | Program_Name                                          | Industry           |   AHC_Funded |   Share_of_Total_% |   Units |   Distinct_Students | Short_Label                  | Full_Label                                            |
|:-------------|:------------------------------------------------------|:-------------------|-------------:|-------------------:|--------:|--------------------:|:-----------------------------|:------------------------------------------------------|
| CER30115     | Certificate III in Early Childhood Education and Care | Community Services |        31357 |               18.1 |     691 |                 177 | Cert III Early Childhood     | Certificate III in Early Childhood Education and Care |
| CER40115     | Certificate IV in Early Childhood Education and Care  | Community Services |        25793 |               14.9 |     548 |                 191 | Cert IV Early Childhood      | Certificate IV in Early Childhood Education and Care  |
| CHC33015     | Certificate III in Individual Support                 | Community Services |        24347 |               14.1 |     528 |                 185 | Cert III Individual Support  | Certificate III in Individual Support                 |
| SIS30321     | Certificate III in Fitness                            | Sport & Recreation |        15690 |                9.1 |     599 |                 204 | Cert III Fitness             | Certificate III in Fitness                            |
| HLT33015     | Certificate III in Allied Health Assistance           | Health             |        14141 |                8.2 |     535 |                 182 | Cert III Allied Health Asst. | Certificate III in Allied Health Assistance           |
| RII20715     | Certificate II in Resources and Infrastructure        | Resources          |        14104 |                8.2 |     545 |                 187 | Cert II Resources            | Certificate II in Resources and Infrastructure        |
| BSB30120     | Certificate III in Business                           | Business           |        13557 |                7.8 |     501 |                 172 | Cert III Business            | Certificate III in Business                           |
| BSB20120     | Certificate II in Business                            | Business           |        11782 |                6.8 |     563 |                 169 | Cert II Business             | Certificate II in Business                            |
| AHC20116     | Certificate II in Agriculture                         | Primary Industry   |        11197 |                6.5 |     492 |                 178 | Cert II Agriculture          | Certificate II in Agriculture                         |
| FSK10213     | Certificate I in Skills for Vocational Pathways       | Foundation Skills  |        10826 |                6.3 |     498 |                 170 | Cert I Vocational Pathways   | Certificate I in Skills for Vocational Pathways       |

## t12c_industry_by_remoteness

Funded AHC by Industry within each Remoteness class; the share column sums to 100% within each region.

| Industry           | Remoteness   |   AHC_Funded |   Share_within_Remoteness_% |
|:-------------------|:-------------|-------------:|----------------------------:|
| Community Services | Regional     |        22820 |                        49.5 |
| Business           | Regional     |         6543 |                        14.2 |
| Sport & Recreation | Regional     |         4076 |                         8.8 |
| Health             | Regional     |         3842 |                         8.3 |
| Foundation Skills  | Regional     |         3204 |                         6.9 |
| Resources          | Regional     |         3097 |                         6.7 |
| Primary Industry   | Regional     |         2540 |                         5.5 |
| Community Services | Remote       |        38350 |                        46.8 |
| Business           | Remote       |        12324 |                        15.1 |
| Sport & Recreation | Remote       |         7326 |                         8.9 |
| Resources          | Remote       |         7182 |                         8.8 |
| Health             | Remote       |         6768 |                         8.3 |
| Primary Industry   | Remote       |         5326 |                         6.5 |
| Foundation Skills  | Remote       |         4600 |                         5.6 |
| Community Services | Urban        |        20327 |                        45.4 |
| Business           | Urban        |         6472 |                        14.4 |
| Sport & Recreation | Urban        |         4288 |                         9.6 |
| Resources          | Urban        |         3825 |                         8.5 |
| Health             | Urban        |         3531 |                         7.9 |
| Primary Industry   | Urban        |         3331 |                         7.4 |
| Foundation Skills  | Urban        |         3022 |                         6.7 |

## t12c_industry_by_funding_source

Funded AHC by Industry within each Funding_Source; the share column sums to 100% within each stream.

| Industry           | Funding_Source   |   AHC_Funded |   Share_within_FundingSource_% |
|:-------------------|:-----------------|-------------:|-------------------------------:|
| Community Services | 11J              |        18628 |                           47.4 |
| Business           | 11J              |         5867 |                           14.9 |
| Health             | 11J              |         3509 |                            8.9 |
| Sport & Recreation | 11J              |         3189 |                            8.1 |
| Resources          | 11J              |         2827 |                            7.2 |
| Primary Industry   | 11J              |         2648 |                            6.7 |
| Foundation Skills  | 11J              |         2598 |                            6.6 |
| Community Services | 11K              |        24132 |                           51   |
| Business           | 11K              |         5836 |                           12.3 |
| Sport & Recreation | 11K              |         4318 |                            9.1 |
| Resources          | 11K              |         4244 |                            9   |
| Health             | 11K              |         3556 |                            7.5 |
| Primary Industry   | 11K              |         2861 |                            6   |
| Foundation Skills  | 11K              |         2372 |                            5   |
| Community Services | 11N              |         9730 |                           43.1 |
| Business           | 11N              |         4400 |                           19.5 |
| Sport & Recreation | 11N              |         2240 |                            9.9 |
| Resources          | 11N              |         1940 |                            8.6 |
| Health             | 11N              |         1610 |                            7.1 |
| Foundation Skills  | 11N              |         1480 |                            6.6 |
| Primary Industry   | 11N              |         1155 |                            5.1 |
| Community Services | 11V              |         7215 |                           43.6 |
| Business           | 11V              |         2215 |                           13.4 |
| Sport & Recreation | 11V              |         2060 |                           12.5 |
| Resources          | 11V              |         1520 |                            9.2 |
| Foundation Skills  | 11V              |         1400 |                            8.5 |
| Primary Industry   | 11V              |         1155 |                            7   |
| Health             | 11V              |          980 |                            5.9 |
| Community Services | FFT              |        21792 |                           46.3 |
| Business           | FFT              |         7021 |                           14.9 |
| Health             | FFT              |         4486 |                            9.5 |
| Sport & Recreation | FFT              |         3883 |                            8.2 |
| Resources          | FFT              |         3573 |                            7.6 |
| Primary Industry   | FFT              |         3378 |                            7.2 |
| Foundation Skills  | FFT              |         2976 |                            6.3 |

## t12d_concentration

Share of funded AHC held by the top industries and programs, against the share expected if hours were spread evenly across all industries or programs.

| Metric                                                 |   Value |
|:-------------------------------------------------------|--------:|
| Top 1 industry share of total AHC                      |    47.2 |
| Top 2 industries share of total AHC                    |    61.8 |
| Top 3 industries share of total AHC                    |    70.9 |
| Top 3 programs share of total AHC                      |    47.2 |
| Reference: even-spread share for top 3 of 7 industries |    42.9 |
| Reference: even-spread share for top 3 of 10 programs  |    30   |

## t13_by_qualification_level

Funded AHC, units, students and completion rate (cached, new to this dimension) by qualification level parsed from Program_Name, listing the Program_IDs at each level.

| Qualification_Level   |   AHC_Funded |   Share_of_Total_% |   Units |   Distinct_Students |   Completion_Rate_% |   CI_Lower |   CI_Upper |   Eligible_Units | Program_IDs                                      |
|:----------------------|-------------:|-------------------:|--------:|--------------------:|--------------------:|-----------:|-----------:|-----------------:|:-------------------------------------------------|
| Certificate I         |        10826 |                6.3 |     498 |                 170 |                61.7 |       57.2 |       65.9 |              433 | FSK10213                                         |
| Certificate II        |        37083 |               21.5 |    1600 |                 483 |                59.4 |       56.8 |       62.1 |             1368 | AHC20116, BSB20120, RII20715                     |
| Certificate III       |        99092 |               57.3 |    2854 |                 766 |                60.9 |       59   |       62.7 |             2450 | BSB30120, CER30115, CHC33015, HLT33015, SIS30321 |
| Certificate IV        |        25793 |               14.9 |     548 |                 191 |                59.2 |       55   |       63.3 |              483 | CER40115                                         |

## t14_by_town

Funded AHC, units, students, providers and completion rate by town (Location), sorted by AHC descending. No coordinates are included; do not add any.

| Location      | Remoteness   |   AHC_Funded |   Share_of_Total_% |   Units |   Distinct_Students |   Distinct_Providers |   Completion_Rate_% |
|:--------------|:-------------|-------------:|-------------------:|--------:|--------------------:|---------------------:|--------------------:|
| Darwin        | Urban        |        23721 |               13.7 |     754 |                 241 |                    8 |                60.1 |
| Alice Springs | Regional     |        23583 |               13.6 |     732 |                 237 |                    8 |                57.1 |
| Katherine     | Regional     |        22539 |               13   |     725 |                 238 |                    8 |                59.8 |
| Wadeye        | Remote       |        21747 |               12.6 |     679 |                 227 |                    8 |                63   |
| Jabiru        | Remote       |        21608 |               12.5 |     693 |                 226 |                    8 |                59.7 |
| Palmerston    | Urban        |        21075 |               12.2 |     686 |                 229 |                    8 |                58.9 |
| Nhulunbuy     | Remote       |        19272 |               11.2 |     612 |                 196 |                    8 |                59.9 |
| Tennant Creek | Remote       |        19249 |               11.1 |     619 |                 203 |                    8 |                65   |

## t14b_town_summary

How many towns there are in total, and how many individually hold at least 5% of total funded AHC.

| Metric                                       |   Value |
|:---------------------------------------------|--------:|
| Number of towns (distinct Location values)   |       8 |
| Towns holding at least 5% of funded AHC each |       8 |

## t15_program_intensity

Program-level intensity: units, students, units/AHC per student and per unit, mean unit length and mean funded fraction per program, plus two summary rows for the three Community Services programs combined and the other seven combined.

| Program_ID                      | Short_Label                  | Industry           |   Distinct_Students |   Units |   Units_per_Student |   Distinct_Unit_IDs |   AHC_Funded |   Share_of_Total_% |   AHC_per_Unit |   AHC_per_Student |   Mean_Nominal_Hours_per_Unit |   Mean_Funded_Fraction |   Mean_Nominal_Hours_per_Unit_exact |   Mean_Funded_Fraction_exact |
|:--------------------------------|:-----------------------------|:-------------------|--------------------:|--------:|--------------------:|--------------------:|-------------:|-------------------:|---------------:|------------------:|------------------------------:|-----------------------:|------------------------------------:|-----------------------------:|
| CER30115                        | Cert III Early Childhood     | Community Services |                 177 |     691 |                 3.9 |                   5 |        31357 |               18.1 |           45.4 |             177.2 |                          49.9 |                  0.91  |                             49.8698 |                       0.9098 |
| CER40115                        | Cert IV Early Childhood      | Community Services |                 191 |     548 |                 2.9 |                   3 |        25793 |               14.9 |           47.1 |             135   |                          51.7 |                  0.91  |                             51.6971 |                       0.9102 |
| CHC33015                        | Cert III Individual Support  | Community Services |                 185 |     528 |                 2.9 |                   3 |        24347 |               14.1 |           46.1 |             131.6 |                          50   |                  0.921 |                             50.0379 |                       0.9207 |
| SIS30321                        | Cert III Fitness             | Sport & Recreation |                 204 |     599 |                 2.9 |                   3 |        15690 |                9.1 |           26.2 |              76.9 |                          30   |                  0.874 |                             30.0083 |                       0.8737 |
| HLT33015                        | Cert III Allied Health Asst. | Health             |                 182 |     535 |                 2.9 |                   3 |        14141 |                8.2 |           26.4 |              77.7 |                          29.8 |                  0.884 |                             29.8318 |                       0.8844 |
| RII20715                        | Cert II Resources            | Resources          |                 187 |     545 |                 2.9 |                   3 |        14104 |                8.2 |           25.9 |              75.4 |                          30   |                  0.862 |                             30.0367 |                       0.8624 |
| BSB30120                        | Cert III Business            | Business           |                 172 |     501 |                 2.9 |                   3 |        13557 |                7.8 |           27.1 |              78.8 |                          30   |                  0.903 |                             30.0299 |                       0.9028 |
| BSB20120                        | Cert II Business             | Business           |                 169 |     563 |                 3.3 |                   4 |        11782 |                6.8 |           20.9 |              69.7 |                          22.4 |                  0.936 |                             22.4334 |                       0.9364 |
| AHC20116                        | Cert II Agriculture          | Primary Industry   |                 178 |     492 |                 2.8 |                   3 |        11197 |                6.5 |           22.8 |              62.9 |                          24.9 |                  0.913 |                             24.8984 |                       0.9126 |
| FSK10213                        | Cert I Vocational Pathways   | Foundation Skills  |                 170 |     498 |                 2.9 |                   3 |        10826 |                6.3 |           21.7 |              63.7 |                          25   |                  0.87  |                             25.0201 |                       0.87   |
| Community Services (3 programs) | Community Services combined  | Community Services |                 496 |    1767 |                 3.6 |                  11 |        81497 |               47.2 |           46.1 |             164.3 |                          50.5 |                  0.913 |                             50.4867 |                       0.9132 |
| Other 7 programs combined       | Other 7 programs combined    | Multiple           |                 946 |    3733 |                 3.9 |                  22 |        91297 |               52.8 |           24.5 |              96.5 |                          27.5 |                  0.892 |                             27.5087 |                       0.8916 |

## t16_student_count_chance_check

Whether the observed spread in distinct students per program (35, from 169 to 204 across 10 programs) is more or less than a chance benchmark: each of the 1203 students keeps their observed number of distinct programs, but which programs are reassigned at random without replacement from all 10 (10,000 permutations, seed 42). Assumes every program is equally available to every student and that students can appear in more than one program, both already true of the observed data.

| Metric                                     | Value    |
|:-------------------------------------------|:---------|
| Observed minimum students (any program)    | 169      |
| Observed maximum students (any program)    | 204      |
| Observed max-to-min ratio                  | 1.21     |
| Observed spread (max minus min)            | 35       |
| Null mean spread under random reassignment | 39.5     |
| Null 95% range of spread                   | 22 to 61 |
| Two-sided p-value for observed spread      | 0.7314   |

## t17a_ahc_by_industry_outcome

Funded AHC by Industry and Outcome_Group (all six groups), with the share within each industry and that industry's share of hours in units not achieved or withdrawn ('not completed'), repeated on every row for the industry. Share_within_Industry_exact and Not_Completed_Share_exact are 4-decimal companions, for whole-number rounding. Feeds the industry-range sentence in the 'Funding vs outcome' Sankey caption.

| Industry           | Outcome_Group            |   AHC_Funded |   Share_within_Industry_% |   Not_Completed_Share_% |   Share_within_Industry_exact |   Not_Completed_Share_exact |
|:-------------------|:-------------------------|-------------:|--------------------------:|------------------------:|------------------------------:|----------------------------:|
| Community Services | Achieved                 |        42971 |                      52.7 |                    35.9 |                       52.7271 |                     35.8933 |
| Community Services | Not achieved             |        17545 |                      21.5 |                    35.9 |                       21.5284 |                     35.8933 |
| Community Services | Withdrawn                |        11707 |                      14.4 |                    35.9 |                       14.3649 |                     35.8933 |
| Community Services | Continuing               |         8516 |                      10.4 |                    35.9 |                       10.4495 |                     35.8933 |
| Community Services | Learner support          |          758 |                       0.9 |                    35.9 |                        0.9301 |                     35.8933 |
| Community Services | Not funded / not started |            0 |                       0   |                    35.9 |                        0      |                     35.8933 |
| Business           | Achieved                 |        13369 |                      52.8 |                    34.1 |                       52.7606 |                     34.0976 |
| Business           | Not achieved             |         5218 |                      20.6 |                    34.1 |                       20.5928 |                     34.0976 |
| Business           | Withdrawn                |         3422 |                      13.5 |                    34.1 |                       13.5049 |                     34.0976 |
| Business           | Continuing               |         3046 |                      12   |                    34.1 |                       12.021  |                     34.0976 |
| Business           | Learner support          |          284 |                       1.1 |                    34.1 |                        1.1208 |                     34.0976 |
| Business           | Not funded / not started |            0 |                       0   |                    34.1 |                        0      |                     34.0976 |
| Sport & Recreation | Achieved                 |         8231 |                      52.5 |                    36.8 |                       52.4602 |                     36.8451 |
| Sport & Recreation | Not achieved             |         3344 |                      21.3 |                    36.8 |                       21.3129 |                     36.8451 |
| Sport & Recreation | Withdrawn                |         2437 |                      15.5 |                    36.8 |                       15.5322 |                     36.8451 |
| Sport & Recreation | Continuing               |         1639 |                      10.4 |                    36.8 |                       10.4461 |                     36.8451 |
| Sport & Recreation | Learner support          |           39 |                       0.2 |                    36.8 |                        0.2486 |                     36.8451 |
| Sport & Recreation | Not funded / not started |            0 |                       0   |                    36.8 |                        0      |                     36.8451 |
| Health             | Achieved                 |         7291 |                      51.6 |                    35.2 |                       51.5593 |                     35.1531 |
| Health             | Not achieved             |         2790 |                      19.7 |                    35.2 |                       19.7299 |                     35.1531 |
| Health             | Withdrawn                |         2181 |                      15.4 |                    35.2 |                       15.4232 |                     35.1531 |
| Health             | Continuing               |         1759 |                      12.4 |                    35.2 |                       12.439  |                     35.1531 |
| Health             | Learner support          |          120 |                       0.8 |                    35.2 |                        0.8486 |                     35.1531 |
| Health             | Not funded / not started |            0 |                       0   |                    35.2 |                        0      |                     35.1531 |
| Resources          | Achieved                 |         7260 |                      51.5 |                    36.7 |                       51.4748 |                     36.6846 |
| Resources          | Not achieved             |         3192 |                      22.6 |                    36.7 |                       22.6319 |                     36.6846 |
| Resources          | Withdrawn                |         1982 |                      14.1 |                    36.7 |                       14.0528 |                     36.6846 |
| Resources          | Continuing               |         1456 |                      10.3 |                    36.7 |                       10.3233 |                     36.6846 |
| Resources          | Learner support          |          214 |                       1.5 |                    36.7 |                        1.5173 |                     36.6846 |
| Resources          | Not funded / not started |            0 |                       0   |                    36.7 |                        0      |                     36.6846 |
| Primary Industry   | Achieved                 |         5456 |                      48.7 |                    39.5 |                       48.7273 |                     39.5017 |
| Primary Industry   | Not achieved             |         2376 |                      21.2 |                    39.5 |                       21.22   |                     39.5017 |
| Primary Industry   | Withdrawn                |         2047 |                      18.3 |                    39.5 |                       18.2817 |                     39.5017 |
| Primary Industry   | Continuing               |         1138 |                      10.2 |                    39.5 |                       10.1634 |                     39.5017 |
| Primary Industry   | Learner support          |          180 |                       1.6 |                    39.5 |                        1.6076 |                     39.5017 |
| Primary Industry   | Not funded / not started |            0 |                       0   |                    39.5 |                        0      |                     39.5017 |
| Foundation Skills  | Achieved                 |         5871 |                      54.2 |                    35.5 |                       54.2306 |                     35.4702 |
| Foundation Skills  | Not achieved             |         2298 |                      21.2 |                    35.5 |                       21.2267 |                     35.4702 |
| Foundation Skills  | Withdrawn                |         1542 |                      14.2 |                    35.5 |                       14.2435 |                     35.4702 |
| Foundation Skills  | Continuing               |         1050 |                       9.7 |                    35.5 |                        9.6989 |                     35.4702 |
| Foundation Skills  | Learner support          |           65 |                       0.6 |                    35.5 |                        0.6004 |                     35.4702 |
| Foundation Skills  | Not funded / not started |            0 |                       0   |                    35.5 |                        0      |                     35.4702 |

## t19_provider_names

Provider_ID and its organisation name, for display only - no student-level rows.

| Provider_ID   | Provider_Name                     |
|:--------------|:----------------------------------|
| P001          | Charles Darwin University         |
| P002          | TAFE NT                           |
| P003          | NT Skills & Training Pty Ltd      |
| P004          | Barkly Regional Training Services |
| P005          | Top End Workforce Solutions       |
| P006          | Arafura Learning Institute        |
| P007          | Desert Training Co                |
| P008          | Jabiru Community College          |

## t21_data_quality_figures

Small aggregate counts (no student-level rows) for the Method and data quality page: Gender = X prevalence, the Funded_Flag/outcome-code conflict, P008's Fee-Free TAFE delivery, VET in Schools at-school flag counts, and the 11N/11V share of rows by Remoteness.

| Metric                                                    |     Value |
|:----------------------------------------------------------|----------:|
| Student table rows                                        | 1974      |
| Gender = X students                                       |  657      |
| Rows with Funded_Flag = 85%_only and outcome 51, 52 or 70 |  960      |
| P008 Fee-Free TAFE enrolment rows                         |  712      |
| 11N and 11V rows (VET in Schools streams)                 | 1161      |
| 11N and 11V rows not flagged At_School_Flag = Y           | 1070      |
| 11N share of rows in Urban (%)                            |   29.2354 |
| 11N share of rows in Regional (%)                         |   26.6867 |
| 11N share of rows in Remote (%)                           |   44.078  |
| 11V share of rows in Urban (%)                            |   23.4818 |
| 11V share of rows in Regional (%)                         |   21.4575 |
| 11V share of rows in Remote (%)                           |   55.0607 |

## t18_atsi_enrolled_share

Share of enrolled students recorded as ATSI = Y, overall and by Funding_Source, Provider_ID and Remoteness, with a 95% Wilson interval. An enrolled student is a distinct Student_ID with at least one Enrolment row; a student counts in a group if they have an enrolment row in it, so one student can appear in several groups. Share_exact, Lower_exact and Upper_exact are 4-decimal companions of Share_%, CI_Lower and CI_Upper, for whole-number rounding that must not double-round.

| Dimension      | Group    |   Students |   ATSI_students |   Share_% |   Share_exact |   CI_Lower |   CI_Upper |   Lower_exact |   Upper_exact |
|:---------------|:---------|-----------:|----------------:|----------:|--------------:|-----------:|-----------:|--------------:|--------------:|
| Overall        | Overall  |       1203 |             437 |      36.3 |       36.3259 |       33.7 |       39.1 |       33.6556 |       39.0831 |
| Funding_Source | 11J      |        391 |             135 |      34.5 |       34.5269 |       30   |       39.4 |       29.9853 |       39.3695 |
| Funding_Source | 11K      |        461 |             183 |      39.7 |       39.6963 |       35.3 |       44.2 |       35.3329 |       44.2301 |
| Funding_Source | 11N      |        214 |              80 |      37.4 |       37.3832 |       31.2 |       44   |       31.177  |       44.0343 |
| Funding_Source | 11V      |        163 |              62 |      38   |       38.0368 |       30.9 |       45.7 |       30.9405 |       45.684  |
| Funding_Source | FFT      |        469 |             161 |      34.3 |       34.3284 |       30.2 |       38.7 |       30.1742 |       38.7372 |
| Provider_ID    | P001     |        228 |              80 |      35.1 |       35.0877 |       29.2 |       41.5 |       29.1867 |       41.483  |
| Provider_ID    | P002     |        221 |              88 |      39.8 |       39.819  |       33.6 |       46.4 |       33.592  |       46.3939 |
| Provider_ID    | P003     |        211 |              76 |      36   |       36.019  |       29.8 |       42.7 |       29.8449 |       42.693  |
| Provider_ID    | P004     |        230 |              72 |      31.3 |       31.3043 |       25.7 |       37.6 |       25.6599 |       37.5631 |
| Provider_ID    | P005     |        224 |              79 |      35.3 |       35.2679 |       29.3 |       41.7 |       29.3071 |       41.7253 |
| Provider_ID    | P006     |        215 |              89 |      41.4 |       41.3953 |       35   |       48.1 |       35.019  |       48.0738 |
| Provider_ID    | P007     |        227 |              94 |      41.4 |       41.4097 |       35.2 |       47.9 |       35.1969 |       47.9084 |
| Provider_ID    | P008     |        229 |              81 |      35.4 |       35.3712 |       29.5 |       41.8 |       29.4666 |       41.7585 |
| Remoteness     | Regional |        447 |             166 |      37.1 |       37.1365 |       32.8 |       41.7 |       32.7847 |       41.7074 |
| Remoteness     | Remote   |        712 |             258 |      36.2 |       36.236  |       32.8 |       39.8 |       32.7878 |       39.8318 |
| Remoteness     | Urban    |        436 |             154 |      35.3 |       35.3211 |       31   |       39.9 |       30.9806 |       39.918  |

## t18b_atsi_omnibus_tests

Test for any difference in ATSI share between groups, per dimension: a binomial GEE with one row per student-group membership, outcome ATSI = Y (1 or 0), the group as the only predictor, an exchangeable correlation structure clustered on Student_ID, and a Wald test for any group difference.

| Dimension      |   P_value |
|:---------------|----------:|
| Funding_Source |    0.3279 |
| Provider_ID    |    0.3741 |
| Remoteness     |    0.6423 |
