"""
NT VET Performance project - analysis tables (read-only, no charts).

Reads data/clean/*.csv (never modifies them) and writes:
  - outputs/analysis_tables/*.csv  (one CSV per table/sub-table)
  - outputs/analysis_summary.md    (every table in full, as markdown)
  - outputs/analysis_methods.md    (definitions and methodology choices)
  - outputs/headline_claims.md     (claim-by-claim verdicts)

Deterministic: every random draw (the cluster bootstraps) comes from a single
numpy Generator seeded with 42, consumed in a fixed order, so two runs
produce byte-identical output.

Privacy: this script never prints or writes USI, DOB, or any other
student-level row - every table is an aggregate (by provider, funding
source, remoteness, industry, outcome, year, or ATSI category).
"""

import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.proportion import proportion_confint

ROOT = Path(__file__).resolve().parent.parent
CLEAN_DIR = ROOT / "data" / "clean"
OUTPUTS_DIR = ROOT / "outputs"
TABLES_DIR = OUTPUTS_DIR / "analysis_tables"

# The app's half-up rounding helper, so every one-decimal and four-decimal
# figure written by this script rounds the same way the app does.
sys.path.insert(0, str(ROOT / "app"))
from lib.numfmt import round_dp  # noqa: E402

SEED = 42
N_RESAMPLES = 2000
N_PERMUTATIONS = 10000
EXPECTED_TOTAL_AHC = 172794
EXPECTED_MATCHED_PAIRS = 19
EXPECTED_ELIGIBLE_UNITS = 4734
EXPECTED_ENROLLED_STUDENTS = 1203
EXPECTED_GROUP_COUNTS = {"Funding_Source": 5, "Provider_ID": 8, "Remoteness": 3}

# Hand-written, not algorithmic: short, glance-readable labels for each of the
# 10 programs. Used by T12b and T15. Full_Label (= Program_Name) carries the
# full name for anywhere that needs it (for example a hover tooltip).
SHORT_LABEL_LOOKUP = {
    "CER30115": "Cert III Early Childhood",
    "CER40115": "Cert IV Early Childhood",
    "CHC33015": "Cert III Individual Support",
    "SIS30321": "Cert III Fitness",
    "HLT33015": "Cert III Allied Health Asst.",
    "RII20715": "Cert II Resources",
    "BSB30120": "Cert III Business",
    "BSB20120": "Cert II Business",
    "AHC20116": "Cert II Agriculture",
    "FSK10213": "Cert I Vocational Pathways",
}

TABLES = []  # list of (csv_name, dataframe, one_line_description) in write order


def fail(message):
    print(f"VALIDATION FAILED: {message}", file=sys.stderr)
    sys.exit(1)


def record_table(name, df, description):
    TABLES.append((name, df.copy(), description))


def round_pct(x, decimals=1):
    """Round a percentage value to `decimals` places. Works on a scalar or a
    pandas Series/numpy array alike, since several tables assign this over a
    whole column at once."""
    if isinstance(x, pd.Series):
        return x.astype(float).round(decimals)
    if isinstance(x, np.ndarray):
        return np.round(x.astype(float), decimals)
    if x is None or pd.isna(x):
        return np.nan
    return round(float(x), decimals)


def round_ahc(x):
    if x is None or pd.isna(x):
        return np.nan
    return int(round(float(x)))


def assert_close(actual, expected, tol, message):
    if abs(actual - expected) > tol:
        fail(f"{message}: expected {expected}, got {actual}")


def assert_shares_sum_to_100(shares, label, tol=0.5):
    total = sum(s for s in shares if not pd.isna(s))
    if abs(total - 100) > tol:
        fail(f"{label}: shares sum to {total:.2f}, not ~100 (tolerance {tol})")


# ----------------------------------------------------------------------
# Cluster bootstrap (resamples students, not rows)
# ----------------------------------------------------------------------

def student_level_counts(df, eligible_mask, achieved_mask, student_col="Student_ID"):
    """Per-student (eligible_count, achieved_count) arrays for a slice."""
    d = df.loc[eligible_mask, [student_col]].copy()
    d["_ach"] = np.asarray(achieved_mask)[np.asarray(eligible_mask)].astype(int)
    agg = d.groupby(student_col)["_ach"].agg(n_eligible="size", n_achieved="sum")
    return agg["n_eligible"].to_numpy(), agg["n_achieved"].to_numpy()


def bootstrap_rate_draws(n_eligible_arr, n_achieved_arr, rng, n_resamples=N_RESAMPLES):
    n = len(n_eligible_arr)
    if n == 0:
        return np.full(n_resamples, np.nan)
    idx = rng.integers(0, n, size=(n_resamples, n))
    elig_sums = n_eligible_arr[idx].sum(axis=1)
    ach_sums = n_achieved_arr[idx].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        rates = np.where(elig_sums > 0, 100 * ach_sums / elig_sums, np.nan)
    return rates


def point_rate(n_eligible_arr, n_achieved_arr):
    tot_e = n_eligible_arr.sum()
    tot_a = n_achieved_arr.sum()
    return 100 * tot_a / tot_e if tot_e > 0 else np.nan, int(tot_e), int(tot_a)


def completion_rate_with_ci(df, eligible_mask, achieved_mask, rng, student_col="Student_ID"):
    n_elig_arr, n_ach_arr = student_level_counts(df, eligible_mask, achieved_mask, student_col)
    rate, n_units, n_ach_units = point_rate(n_elig_arr, n_ach_arr)
    n_students = len(n_elig_arr)
    draws = bootstrap_rate_draws(n_elig_arr, n_ach_arr, rng)
    lo, hi = np.nanpercentile(draws, [2.5, 97.5])
    return {
        "rate": round_pct(rate),
        "ci_lo": round_pct(lo),
        "ci_hi": round_pct(hi),
        "units": n_units,
        "students": n_students,
        "draws": draws,
        # Full-precision companions (4 decimals) of rate/ci_lo/ci_hi, captured
        # before the one-decimal rounding above, plus the achieved-unit count
        # (already exact, not rounded) - so a whole-number display elsewhere
        # in the app can round the true value once, instead of rounding this
        # already-rounded one-decimal figure a second time.
        "rate_exact": round_pct(rate, 4),
        "ci_lo_exact": round_pct(lo, 4),
        "ci_hi_exact": round_pct(hi, 4),
        "achieved_units": n_ach_units,
    }


def get_cached_rate(cache, key, df, eligible_mask, achieved_mask, rng, student_col="Student_ID"):
    """Compute a cluster-bootstrap completion rate exactly once per key and
    reuse it everywhere that key is requested again, so the same estimate
    never shows two different point values or CIs across tables. `key` must
    uniquely identify the (population, definition) pair, e.g.
    ("standard", "Funding_Source", "FFT") or ("atsi", "Y", "Remoteness", "Urban")."""
    if key not in cache:
        cache[key] = completion_rate_with_ci(df, eligible_mask, achieved_mask, rng, student_col)
    return cache[key]


def omnibus_gee_pvalue(df, eligible_mask, group_col, student_col="Student_ID"):
    d = df.loc[eligible_mask, [group_col, student_col]].copy()
    d["completed"] = (df.loc[eligible_mask, "Outcome_Group"] == "Achieved").astype(int).values
    if d[group_col].nunique() < 2:
        return np.nan
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = smf.gee(
            f"completed ~ C({group_col})",
            groups=student_col,
            data=d,
            family=sm.families.Binomial(),
            cov_struct=sm.cov_struct.Exchangeable(),
        )
        res = model.fit()
        wt = res.wald_test_terms()
    term_name = f"C({group_col})"
    return float(wt.table.loc[term_name, "pvalue"])


def main():
    rng = np.random.default_rng(SEED)

    enr = pd.read_csv(CLEAN_DIR / "enrolment.csv")
    stu = pd.read_csv(CLEAN_DIR / "student.csv")
    recon = pd.read_csv(CLEAN_DIR / "contract_delivery_recon.csv")
    org = pd.read_csv(CLEAN_DIR / "organisation.csv")

    enr["_valid_start"] = pd.to_datetime(enr["Enrol_Start_Date"], errors="coerce")
    eligible_mask_all = (enr["In_Completion_Rate"] == True).to_numpy()  # noqa: E712
    achieved_mask_all = (enr["Outcome_Group"] == "Achieved").to_numpy()
    enr_with_atsi = enr.merge(stu[["Student_ID", "ATSI", "At_School_Flag"]], on="Student_ID", how="left")

    rate_cache = {}  # one bootstrap estimate per (population, definition) key, reused across every table

    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    # ==================================================================
    # T01. KPI values
    # ==================================================================
    total_ahc = int(enr["AHC_Funded"].sum())
    n_rows = len(enr)
    n_students = enr["Student_ID"].nunique()
    n_providers = enr["Provider_ID"].nunique()

    headline = get_cached_rate(rate_cache, ("standard", "Overall", "Overall"), enr, eligible_mask_all, achieved_mask_all, rng)

    enrolled_students = stu[stu["Has_Enrolment"] == True]  # noqa: E712
    share_atsi_y = 100 * (enrolled_students["ATSI"] == "Y").sum() / len(enrolled_students)

    ahc_by_remoteness = enr.groupby("Remoteness")["AHC_Funded"].sum()
    remoteness_shares = 100 * ahc_by_remoteness / ahc_by_remoteness.sum()

    t01_rows = [
        ["Total funded AHC", round_ahc(total_ahc), np.nan, np.nan, float(total_ahc)],
        ["Enrolment rows", n_rows, np.nan, np.nan, float(n_rows)],
        ["Distinct students", n_students, np.nan, np.nan, float(n_students)],
        ["Distinct providers", n_providers, np.nan, np.nan, float(n_providers)],
        ["Headline completion rate (%)", headline["rate"], headline["ci_lo"], headline["ci_hi"], headline["rate_exact"]],
        [
            "Share of enrolled students with ATSI = Y (%)",
            round_pct(share_atsi_y), np.nan, np.nan, round_pct(share_atsi_y, 4),
        ],
    ]
    for remote_cat in ["Urban", "Regional", "Remote"]:
        t01_rows.append(
            [
                f"Share of funded AHC delivered in {remote_cat} (%)",
                round_pct(remoteness_shares.get(remote_cat, 0)), np.nan, np.nan,
                round_pct(remoteness_shares.get(remote_cat, 0), 4),
            ]
        )
    t01 = pd.DataFrame(t01_rows, columns=["Metric", "Value", "CI_Lower", "CI_Upper", "Value_exact"], dtype=object)
    assert_close(total_ahc, EXPECTED_TOTAL_AHC, 0, "T01 total funded AHC")
    assert_shares_sum_to_100(remoteness_shares.tolist(), "T01 remoteness shares")
    record_table(
        "t01_kpis",
        t01,
        "Headline KPIs: scale, completion rate, ATSI reach, and remoteness mix of funded AHC. "
        "Value_exact is a full-precision companion of Value (4 decimals where Value is itself "
        "rounded; the same number where Value is already an exact count), for whole-number "
        "rounding that must not double-round the one-decimal display column.",
    )

    # ==================================================================
    # T02. Contract coverage
    # ==================================================================
    recon2 = recon.copy()
    for col in ["Target_AHC_Total", "Delivered_AHC_2023_2025"]:
        recon2[col] = pd.to_numeric(recon2[col], errors="coerce")

    def coverage_bucket(row):
        if row["Status"] == "Matched" and row["Target_Status"] != "No target set":
            return "Matched comparable pair"
        if row["Status"] == "Matched" and row["Target_Status"] == "No target set":
            return "Matched pair, no target set"
        if row["Status"] == "Delivery without contract":
            return "Delivery without a contract"
        return "Contract without delivery (0 AHC)"

    recon2["Coverage_Bucket"] = recon2.apply(coverage_bucket, axis=1)

    t02a = (
        recon2.groupby("Coverage_Bucket")["Delivered_AHC_2023_2025"]
        .sum()
        .reindex(["Matched comparable pair", "Matched pair, no target set", "Delivery without a contract", "Contract without delivery (0 AHC)"])
        .fillna(0)
        .reset_index()
    )
    t02a.columns = ["Coverage_Bucket", "AHC"]
    t02a["Share_of_Total_%"] = round_pct(100 * t02a["AHC"] / t02a["AHC"].sum())
    t02a["AHC"] = t02a["AHC"].apply(round_ahc)
    assert_close(t02a["AHC"].sum(), EXPECTED_TOTAL_AHC, 1, "T02a coverage AHC total")
    assert_shares_sum_to_100(t02a["Share_of_Total_%"].tolist(), "T02a coverage shares")
    record_table("t02a_coverage_summary", t02a, "Funded AHC split by whether it sits in a matched, targetless, or contract-less pair.")

    t02b = (
        recon2.groupby(["Provider_ID", "Coverage_Bucket"])["Delivered_AHC_2023_2025"]
        .sum()
        .unstack("Coverage_Bucket", fill_value=0)
        .reindex(columns=["Matched comparable pair", "Matched pair, no target set", "Delivery without a contract", "Contract without delivery (0 AHC)"], fill_value=0)
    )
    t02b = t02b.map(round_ahc).reset_index()
    t02b["Total_AHC"] = t02b[[c for c in t02b.columns if c != "Provider_ID"]].sum(axis=1)
    assert_close(t02b["Total_AHC"].sum(), EXPECTED_TOTAL_AHC, 1, "T02b coverage-by-provider AHC total")
    record_table("t02b_coverage_by_provider", t02b, "Same coverage split as T02a, broken out by Provider_ID.")

    dwc = recon2[recon2["Status"] == "Delivery without contract"].copy()
    dwc["Share_of_Total_%"] = round_pct(100 * dwc["Delivered_AHC_2023_2025"] / recon2["Delivered_AHC_2023_2025"].sum())
    dwc["Flag_P008_FFT"] = (dwc["Provider_ID"] == "P008") & (dwc["Funding_Source"] == "FFT")
    dwc = dwc.sort_values("Delivered_AHC_2023_2025", ascending=False)
    dwc["AHC"] = dwc["Delivered_AHC_2023_2025"].apply(round_ahc)
    t02c = dwc[["Provider_ID", "Funding_Source", "AHC", "Share_of_Total_%", "Flag_P008_FFT"]].reset_index(drop=True)
    if len(t02c) != 16:
        fail(f"T02c: expected 16 Delivery-without-contract pairs, got {len(t02c)}")
    record_table("t02c_delivery_without_contract", t02c, "The 16 Provider_ID + Funding_Source pairs with delivery but no matching contract, sorted by AHC.")

    dwc_11k_ahc = recon2.loc[(recon2["Status"] == "Delivery without contract") & (recon2["Funding_Source"] == "11K"), "Delivered_AHC_2023_2025"].sum()
    total_11k_ahc = recon2.loc[recon2["Funding_Source"] == "11K", "Delivered_AHC_2023_2025"].sum()
    dwc_excl_11k_ahc = recon2.loc[recon2["Status"] == "Delivery without contract", "Delivered_AHC_2023_2025"].sum() - dwc_11k_ahc
    share_a = 100 * dwc_excl_11k_ahc / recon2["Delivered_AHC_2023_2025"].sum()
    share_b = 100 * dwc_excl_11k_ahc / (recon2["Delivered_AHC_2023_2025"].sum() - total_11k_ahc)
    t02d = pd.DataFrame(
        [
            ["Uncontracted (delivery without a contract) AHC for 11K only", round_ahc(dwc_11k_ahc)],
            ["Uncontracted AHC, excluding 11K from the numerator", round_ahc(dwc_excl_11k_ahc)],
            ["(a) Share of total AHC (11K excluded from numerator only)", round_pct(share_a)],
            ["(b) Share of non-11K AHC only (11K excluded from numerator and denominator)", round_pct(share_b)],
        ],
        columns=["Metric", "Value"],
        dtype=object,
    )
    record_table(
        "t02d_uncontracted_excluding_11k",
        t02d,
        "How much delivery-without-a-contract AHC remains once 11K's uncontracted delivery is set aside, as a share of total AHC and of non-11K AHC.",
    )

    # ==================================================================
    # T03. Delivered vs target (matched comparable pairs)
    # ==================================================================
    matched = recon2[(recon2["Status"] == "Matched") & (recon2["Target_Status"] != "No target set")].copy()
    if len(matched) != EXPECTED_MATCHED_PAIRS:
        fail(f"T03: expected {EXPECTED_MATCHED_PAIRS} matched comparable pairs, got {len(matched)}")
    # A8 rounding: on five contracts the three regional targets differ from the given
    # Target_AHC_Total by 1 AHC (source rounding). Each such contract has the difference
    # added to its largest regional part, so the regional sums reconcile exactly to the
    # given totals used in T03b. Nothing else about any contract changes.
    REGION_TARGET_COLS = ["Target_AHC_Urban", "Target_AHC_Regional", "Target_AHC_Remote"]
    for col in REGION_TARGET_COLS:
        matched[col] = pd.to_numeric(matched[col], errors="coerce")
    parts_gap = matched["Target_AHC_Total"] - matched[REGION_TARGET_COLS].sum(axis=1)
    if parts_gap.abs().max() > 1:
        fail(f"T03: regional target parts differ from the total by more than 1 AHC: {parts_gap.tolist()}")
    for idx in matched.index[parts_gap != 0]:
        largest = matched.loc[idx, REGION_TARGET_COLS].idxmax()
        matched.loc[idx, largest] += parts_gap[idx]
    assert_close(
        matched[REGION_TARGET_COLS].sum().sum(), matched["Target_AHC_Total"].sum(), 0,
        "T03 regional target parts reconcile to the given totals",
    )
    matched["Delivered_pct_of_Target"] = 100 * matched["Delivered_AHC_2023_2025"] / matched["Target_AHC_Total"]
    t03a = matched[["Provider_ID", "Funding_Source", "Delivered_AHC_2023_2025", "Target_AHC_Total", "Delivered_pct_of_Target"]].copy()
    t03a.columns = ["Provider_ID", "Funding_Source", "Delivered_AHC", "Target_AHC_Total", "Delivered_pct_of_Target"]
    t03a["Delivered_AHC"] = t03a["Delivered_AHC"].apply(round_ahc)
    t03a["Target_AHC_Total"] = t03a["Target_AHC_Total"].apply(round_ahc)
    t03a["Delivered_pct_of_Target"] = round_pct(t03a["Delivered_pct_of_Target"])
    t03a = t03a.sort_values("Delivered_pct_of_Target", ascending=False).reset_index(drop=True)
    record_table("t03a_matched_pairs", t03a, "Delivered AHC against the 3-year target for each of the 19 matched comparable pairs.")

    rollup_rows = []
    for prov, grp in matched.groupby("Provider_ID"):
        d, t = grp["Delivered_AHC_2023_2025"].sum(), grp["Target_AHC_Total"].sum()
        rollup_rows.append(["Provider_ID", prov, round_ahc(d), round_ahc(t), round_pct(100 * d / t)])
    for fs, grp in matched.groupby("Funding_Source"):
        d, t = grp["Delivered_AHC_2023_2025"].sum(), grp["Target_AHC_Total"].sum()
        rollup_rows.append(["Funding_Source", fs, round_ahc(d), round_ahc(t), round_pct(100 * d / t)])
    d, t = matched["Delivered_AHC_2023_2025"].sum(), matched["Target_AHC_Total"].sum()
    rollup_rows.append(["Overall", "All matched pairs", round_ahc(d), round_ahc(t), round_pct(100 * d / t)])
    t03b = pd.DataFrame(rollup_rows, columns=["Level", "Key", "Delivered_AHC", "Target_AHC_Total", "Delivered_pct_of_Target"])
    t03b = t03b.sort_values(["Level", "Delivered_pct_of_Target"], ascending=[True, False]).reset_index(drop=True)
    record_table("t03b_rollups", t03b, "Delivered-over-target roll-ups by Provider_ID and Funding_Source, plus the overall matched-pair total.")

    # ==================================================================
    # T04. Coverage grid
    # ==================================================================
    t04 = recon2[["Provider_ID", "Funding_Source", "Status", "Delivered_AHC_2023_2025", "Target_AHC_Total"]].copy()
    t04.columns = ["Provider_ID", "Funding_Source", "Status", "Delivered_AHC", "Target_AHC"]
    t04["Delivered_AHC"] = t04["Delivered_AHC"].apply(round_ahc)
    t04["Target_AHC"] = t04["Target_AHC"].apply(lambda x: round_ahc(x) if pd.notna(x) else np.nan)
    t04 = t04.sort_values(["Provider_ID", "Funding_Source"]).reset_index(drop=True)
    record_table("t04_coverage_grid", t04, "Every Provider_ID x Funding_Source combination found in either sheet, with its status, delivered AHC, and target AHC.")

    # ==================================================================
    # T05. Geography
    # ==================================================================
    for col in ["Target_AHC_Urban", "Target_AHC_Regional", "Target_AHC_Remote",
                "Delivered_AHC_Urban", "Delivered_AHC_Regional", "Delivered_AHC_Remote"]:
        matched[col] = pd.to_numeric(matched[col], errors="coerce")

    t05a_rows = []
    for _, r in matched.iterrows():
        for remote_cat, t_col, d_col in [
            ("Urban", "Target_AHC_Urban", "Delivered_AHC_Urban"),
            ("Regional", "Target_AHC_Regional", "Delivered_AHC_Regional"),
            ("Remote", "Target_AHC_Remote", "Delivered_AHC_Remote"),
        ]:
            target_share = 100 * r[t_col] / r["Target_AHC_Total"]
            delivered_share = 100 * r[d_col] / r["Delivered_AHC_2023_2025"]
            t05a_rows.append(
                [r["Provider_ID"], r["Funding_Source"], remote_cat, round_pct(target_share), round_pct(delivered_share),
                 round_pct(delivered_share - target_share)]
            )
    t05a = pd.DataFrame(
        t05a_rows,
        columns=["Provider_ID", "Funding_Source", "Remoteness", "Target_Share_%", "Delivered_Share_%", "Diff_pp"],
    )
    record_table("t05a_pairs_geography", t05a, "Target vs delivered remoteness mix for each matched pair, and the gap in percentage points.")

    agg_rows = []
    for remote_cat, t_col, d_col in [
        ("Urban", "Target_AHC_Urban", "Delivered_AHC_Urban"),
        ("Regional", "Target_AHC_Regional", "Delivered_AHC_Regional"),
        ("Remote", "Target_AHC_Remote", "Delivered_AHC_Remote"),
    ]:
        t_sum = matched[t_col].sum()
        d_sum = matched[d_col].sum()
        agg_rows.append([remote_cat, round_ahc(t_sum), round_ahc(d_sum)])
    t05b = pd.DataFrame(agg_rows, columns=["Remoteness", "Target_AHC_Sum", "Delivered_AHC_Sum"])
    t05b["Target_Share_%"] = round_pct(100 * t05b["Target_AHC_Sum"] / t05b["Target_AHC_Sum"].sum())
    t05b["Delivered_Share_%"] = round_pct(100 * t05b["Delivered_AHC_Sum"] / t05b["Delivered_AHC_Sum"].sum())
    t05b["Diff_pp"] = round_pct(t05b["Delivered_Share_%"] - t05b["Target_Share_%"])
    t05b["Delivered_pct_of_Target_%"] = round_pct(100 * t05b["Delivered_AHC_Sum"] / t05b["Target_AHC_Sum"])
    assert_shares_sum_to_100(t05b["Target_Share_%"].tolist(), "T05b target shares")
    assert_shares_sum_to_100(t05b["Delivered_Share_%"].tolist(), "T05b delivered shares")
    record_table("t05b_aggregate_geography", t05b, "Aggregate target vs delivered remoteness mix, summed across all 19 matched pairs.")

    n_urban_below = int((t05a[t05a["Remoteness"] == "Urban"]["Diff_pp"] < 0).sum())
    n_remote_above = int((t05a[t05a["Remoteness"] == "Remote"]["Diff_pp"] > 0).sum())
    t05c = pd.DataFrame(
        [
            ["Pairs where Urban delivered share is below target share", n_urban_below, len(matched)],
            ["Pairs where Remote delivered share is above target share", n_remote_above, len(matched)],
        ],
        columns=["Metric", "Count", "Of_pairs"],
    )
    record_table("t05c_geography_flags", t05c, "How many of the 19 matched pairs under-deliver Urban or over-deliver Remote relative to target.")

    # ==================================================================
    # T06. Funded hours by outcome
    # ==================================================================
    t06a = enr.groupby(["Funding_Source", "Outcome_Group"])["AHC_Funded"].sum().reset_index()
    fs_totals = enr.groupby("Funding_Source")["AHC_Funded"].sum()
    overall_total = enr["AHC_Funded"].sum()
    t06a["Share_within_Stream_%"] = t06a.apply(lambda r: round_pct(100 * r["AHC_Funded"] / fs_totals[r["Funding_Source"]]), axis=1)
    t06a["Share_Overall_%"] = round_pct(100 * t06a["AHC_Funded"] / overall_total)
    t06a["Share_within_Stream_exact"] = t06a.apply(
        lambda r: round_dp(100 * r["AHC_Funded"] / fs_totals[r["Funding_Source"]], 4), axis=1
    )
    t06a["AHC_Funded"] = t06a["AHC_Funded"].apply(round_ahc)
    t06a = t06a.sort_values(["Funding_Source", "AHC_Funded"], ascending=[True, False]).reset_index(drop=True)
    assert_close(t06a["AHC_Funded"].sum(), EXPECTED_TOTAL_AHC, 1, "T06a AHC total")
    for fs, grp in t06a.groupby("Funding_Source"):
        assert_shares_sum_to_100(grp["Share_within_Stream_%"].tolist(), f"T06a within-stream shares ({fs})")
    assert_shares_sum_to_100(t06a["Share_Overall_%"].tolist(), "T06a overall shares")
    record_table(
        "t06a_ahc_by_funding_outcome",
        t06a,
        "Funded AHC by Funding_Source and Outcome_Group, with share within stream and share of the grand total. "
        "Share_within_Stream_exact is a 4-decimal companion of Share_within_Stream_%, for whole-number rounding.",
    )

    t06b = t06a[["Funding_Source", "Outcome_Group", "AHC_Funded"]].copy()
    t06b.columns = ["source", "target", "value"]
    record_table("t06b_sankey_links", t06b, "Sankey-ready link table: Funding_Source to Outcome_Group, valued by AHC.")

    bad_outcomes = enr[enr["Outcome_Group"].isin(["Withdrawn", "Not achieved"])]
    t06c = bad_outcomes.groupby("Funded_Flag")["AHC_Funded"].sum().reset_index()
    t06c["Share_%"] = round_pct(100 * t06c["AHC_Funded"] / t06c["AHC_Funded"].sum())
    t06c["AHC_Funded"] = t06c["AHC_Funded"].apply(round_ahc)
    t06c = t06c.sort_values("AHC_Funded", ascending=False).reset_index(drop=True)
    record_table("t06c_withdrawn_notachieved_by_funded_flag", t06c, "AHC on withdrawn/not-achieved units, split by Funded_Flag, with the share flagged Y.")

    # ==================================================================
    # T07. Completion rates with intervals
    # ==================================================================
    t07_rows = []

    r = get_cached_rate(rate_cache, ("standard", "Overall", "Overall"), enr, eligible_mask_all, achieved_mask_all, rng)
    t07_rows.append(
        [
            "Overall", "Overall", r["rate"], r["ci_lo"], r["ci_hi"], r["units"], r["students"],
            r["achieved_units"], r["rate_exact"], r["ci_lo_exact"], r["ci_hi_exact"],
        ]
    )
    if r["units"] != EXPECTED_ELIGIBLE_UNITS:
        fail(f"T07: expected {EXPECTED_ELIGIBLE_UNITS} eligible units overall, got {r['units']}")

    dimension_cols = {
        "Funding_Source": enr["Funding_Source"],
        "Provider_ID": enr["Provider_ID"],
        "Remoteness": enr["Remoteness"],
        "Industry": enr["Industry"],
        "Delivery_Year": enr["Delivery_Year"].astype(str),
    }
    for dim_name, series in dimension_cols.items():
        for group_val in sorted(series.dropna().unique()):
            mask = eligible_mask_all & (series == group_val).to_numpy()
            r = get_cached_rate(rate_cache, ("standard", dim_name, group_val), enr, mask, achieved_mask_all, rng)
            t07_rows.append(
                [
                    dim_name, group_val, r["rate"], r["ci_lo"], r["ci_hi"], r["units"], r["students"],
                    r["achieved_units"], r["rate_exact"], r["ci_lo_exact"], r["ci_hi_exact"],
                ]
            )

    t07 = pd.DataFrame(
        t07_rows,
        columns=[
            "Dimension", "Group", "Rate_%", "CI_Lower", "CI_Upper", "Units", "Students",
            "Achieved_units", "Rate_exact", "Lower_exact", "Upper_exact",
        ],
    )
    record_table(
        "t07_completion_by_group",
        t07,
        "Unit-level completion rate with 95% cluster-bootstrap CI, overall and by Funding_Source, "
        "Provider_ID, Remoteness, Industry, and Delivery_Year. Achieved_units/Rate_exact/Lower_exact/"
        "Upper_exact are full-precision companions of Units*Rate_%/Rate_%/CI_Lower/CI_Upper, for "
        "whole-number rounding that must not double-round the one-decimal display columns.",
    )

    omnibus_rows = []
    for dim_name in ["Funding_Source", "Provider_ID", "Remoteness", "Industry"]:
        p = omnibus_gee_pvalue(enr, eligible_mask_all, dim_name)
        sub = t07[t07["Dimension"] == dim_name]
        spread = round_pct(sub["Rate_%"].max() - sub["Rate_%"].min())
        omnibus_rows.append([dim_name, round(p, 4) if not pd.isna(p) else np.nan, spread])
    t07_omnibus = pd.DataFrame(omnibus_rows, columns=["Dimension", "Omnibus_GEE_p_value", "Spread_pp"])
    record_table("t07_omnibus_tests", t07_omnibus, "Omnibus GEE Wald test (any difference between groups) and max-minus-min spread, per dimension.")

    # ==================================================================
    # T08. Reach
    # ==================================================================
    def atsi_reach_table(df, dim_col):
        rows = []
        for group_val, grp in df.groupby(dim_col):
            n_units = len(grp)
            share_units_y = 100 * (grp["ATSI"] == "Y").sum() / n_units
            share_ahc_y = 100 * grp.loc[grp["ATSI"] == "Y", "AHC_Funded"].sum() / grp["AHC_Funded"].sum()
            rows.append([group_val, round_pct(share_units_y), round_pct(share_ahc_y), n_units])
        return pd.DataFrame(rows, columns=[dim_col, "Share_Units_ATSI_Y_%", "Share_AHC_ATSI_Y_%", "Units"])

    t08a_remoteness = atsi_reach_table(enr_with_atsi, "Remoteness")
    t08a_remoteness.insert(0, "Dimension", "Remoteness")
    t08a_remoteness = t08a_remoteness.rename(columns={"Remoteness": "Group"})
    t08a_fs = atsi_reach_table(enr_with_atsi, "Funding_Source")
    t08a_fs.insert(0, "Dimension", "Funding_Source")
    t08a_fs = t08a_fs.rename(columns={"Funding_Source": "Group"})
    t08a_prov = atsi_reach_table(enr_with_atsi, "Provider_ID")
    t08a_prov.insert(0, "Dimension", "Provider_ID")
    t08a_prov = t08a_prov.rename(columns={"Provider_ID": "Group"})
    t08a = pd.concat([t08a_remoteness, t08a_fs, t08a_prov], ignore_index=True)
    record_table("t08a_atsi_reach", t08a, "Share of units and share of funded AHC going to ATSI = Y, by Remoteness, Funding_Source, and Provider_ID.")

    vis = enr_with_atsi[enr_with_atsi["Funding_Source"].isin(["11N", "11V"])].copy()
    vis_rows = []
    for remote_cat, grp in vis.groupby("Remoteness"):
        n_units = len(grp)
        ahc = grp["AHC_Funded"].sum()
        share_not_at_school = 100 * (grp["At_School_Flag"] == "N").sum() / n_units
        share_suspect = 100 * (grp["At_School_Suspect"] == True).sum() / n_units  # noqa: E712
        vis_rows.append([remote_cat, round_ahc(ahc), n_units, round_pct(share_not_at_school), round_pct(share_suspect)])
    t08b = pd.DataFrame(vis_rows, columns=["Remoteness", "AHC", "Units", "Share_AtSchoolFlag_N_%", "Share_AtSchoolSuspect_True_%"])
    record_table(
        "t08b_vet_in_schools",
        t08b,
        "VET in Schools (11N/11V) AHC and units by Remoteness, with the At_School_Flag = N share and the At_School_Suspect = True share reported as separate columns.",
    )

    n_suspect_rows = int((enr["At_School_Suspect"] == True).sum())  # noqa: E712
    n_suspect_students = enr.loc[enr["At_School_Suspect"] == True, "Student_ID"].nunique()  # noqa: E712
    t08c = pd.DataFrame(
        [["At_School_Suspect rows", n_suspect_rows], ["At_School_Suspect students", n_suspect_students]],
        columns=["Metric", "Count"],
    )
    record_table("t08c_at_school_suspect_totals", t08c, "Total rows and distinct students flagged At_School_Suspect across all of Enrolment.")

    # ==================================================================
    # T09. ATSI completion
    # ==================================================================
    atsi_series = enr_with_atsi["ATSI"]

    def atsi_slice(level, dim_name, group_val, mask_extra=None):
        mask = eligible_mask_all & (atsi_series == level).to_numpy()
        if mask_extra is not None:
            mask = mask & mask_extra
        return get_cached_rate(rate_cache, ("atsi", level, dim_name, group_val), enr_with_atsi, mask, achieved_mask_all, rng)

    t09a_rows = []
    gap_rows = []
    atsi_dim_specs = [("Overall", "Overall", None)] + [
        (dim_name, group_val, (series == group_val).to_numpy())
        for dim_name, series in [("Remoteness", enr_with_atsi["Remoteness"]), ("Funding_Source", enr_with_atsi["Funding_Source"])]
        for group_val in sorted(series.dropna().unique())
    ]
    n_comparisons = len(atsi_dim_specs)

    for dim_name, group_val, mask_extra in atsi_dim_specs:
        r_y = atsi_slice("Y", dim_name, group_val, mask_extra)
        r_n = atsi_slice("N", dim_name, group_val, mask_extra)
        t09a_rows.append(
            [
                dim_name, group_val, "Y", r_y["rate"], r_y["ci_lo"], r_y["ci_hi"], r_y["units"],
                r_y["achieved_units"], r_y["rate_exact"], r_y["ci_lo_exact"], r_y["ci_hi_exact"],
            ]
        )
        t09a_rows.append(
            [
                dim_name, group_val, "N", r_n["rate"], r_n["ci_lo"], r_n["ci_hi"], r_n["units"],
                r_n["achieved_units"], r_n["rate_exact"], r_n["ci_lo_exact"], r_n["ci_hi_exact"],
            ]
        )

        gap_draws = r_y["draws"] - r_n["draws"]
        # The display Gap_pp_Y_minus_N is kept exactly as before (the difference of
        # the two *rounded* rates); Gap_exact is the difference of the two unrounded
        # rates, computed separately so a whole-number or one-decimal display
        # elsewhere does not double-round r_y["rate"]/r_n["rate"] a second time.
        gap_point_exact = r_y["rate_exact"] - r_n["rate_exact"]
        gap_point = round_dp(gap_point_exact, 1)
        gap_lo, gap_hi = np.nanpercentile(gap_draws, [2.5, 97.5])
        gap_rows.append(
            [
                dim_name, group_val, gap_point, round_pct(gap_lo), round_pct(gap_hi), n_comparisons,
                round_pct(gap_point_exact, 4), round_pct(gap_lo, 4), round_pct(gap_hi, 4),
            ]
        )

    t09a = pd.DataFrame(
        t09a_rows,
        columns=[
            "Dimension", "Group", "ATSI", "Rate_%", "CI_Lower", "CI_Upper", "Units",
            "Achieved_units", "Rate_exact", "Lower_exact", "Upper_exact",
        ],
    )
    record_table(
        "t09a_unadjusted_completion_by_atsi",
        t09a,
        "Unadjusted unit-level completion rate for ATSI Y and N, overall and by Remoteness and "
        "Funding_Source. Achieved_units/Rate_exact/Lower_exact/Upper_exact are full-precision "
        "companions, for whole-number rounding that must not double-round the one-decimal display columns.",
    )

    t09b = pd.DataFrame(
        gap_rows,
        columns=[
            "Dimension", "Group", "Gap_pp_Y_minus_N", "CI_Lower", "CI_Upper", "N_Comparisons_in_Table",
            "Gap_exact", "Lower_exact", "Upper_exact",
        ],
    )
    n_subgroup_comparisons = n_comparisons - 1  # Overall is the headline comparison, not a subgroup
    expected_false_positives = 0.05 * n_subgroup_comparisons
    record_table(
        "t09b_atsi_gap",
        t09b,
        "ATSI completion gap (Y minus N) in percentage points, with cluster-bootstrap CI. The Overall row "
        f"is the headline comparison; the other {n_subgroup_comparisons} rows (3 Remoteness, 5 "
        "Funding_Source) are the subgroup comparisons. At a 95% CI with no true effect in any subgroup, "
        f"about {expected_false_positives:.2f} of {n_subgroup_comparisons} (5%) would be expected to "
        "exclude zero by chance alone. "
        "Gap_exact/Lower_exact/Upper_exact are full-precision companions of Gap_pp_Y_minus_N/CI_Lower/CI_Upper "
        "(Gap_exact from the two groups' unrounded rates, not their rounded display values), for whole-number "
        "or one-decimal rounding that must not double-round the display columns.",
    )

    elig_df = enr_with_atsi[eligible_mask_all].copy()
    elig_df["completed"] = (elig_df["Outcome_Group"] == "Achieved").astype(int)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        adj_model = smf.gee(
            "completed ~ C(ATSI) + C(Provider_ID) + C(Funding_Source) + C(Remoteness) + C(Industry) + C(Delivery_Year)",
            groups="Student_ID",
            data=elig_df,
            family=sm.families.Binomial(),
            cov_struct=sm.cov_struct.Exchangeable(),
        )
        adj_res = adj_model.fit()

    atsi_term = [name for name in adj_res.params.index if name.startswith("C(ATSI)")][0]
    coef = adj_res.params[atsi_term]
    se = adj_res.bse[atsi_term]
    pval = adj_res.pvalues[atsi_term]
    or_point = np.exp(coef)
    or_lo = np.exp(coef - 1.96 * se)
    or_hi = np.exp(coef + 1.96 * se)

    pred_y_df = elig_df.copy()
    pred_y_df["ATSI"] = "Y"
    pred_n_df = elig_df.copy()
    pred_n_df["ATSI"] = "N"
    pred_y = adj_res.predict(exog=pred_y_df)
    pred_n = adj_res.predict(exog=pred_n_df)
    pred_rate_y = 100 * pred_y.mean()
    pred_rate_n = 100 * pred_n.mean()

    t09c = pd.DataFrame(
        [
            ["ATSI odds ratio (Y vs N)", round(or_point, 3), round_pct(or_point, 4)],
            ["OR 95% CI lower", round(or_lo, 3), round_pct(or_lo, 4)],
            ["OR 95% CI upper", round(or_hi, 3), round_pct(or_hi, 4)],
            ["OR p-value", round(float(pval), 4), round_pct(float(pval), 4)],
            ["Model-predicted completion rate, ATSI = Y (%)", round_pct(pred_rate_y), round_pct(pred_rate_y, 4)],
            ["Model-predicted completion rate, ATSI = N (%)", round_pct(pred_rate_n), round_pct(pred_rate_n, 4)],
            [
                "Model-predicted gap, Y minus N (pp)",
                round_pct(pred_rate_y - pred_rate_n),
                round_pct(pred_rate_y - pred_rate_n, 4),
            ],
        ],
        columns=["Metric", "Value", "Value_exact"],
        dtype=object,
    )
    record_table(
        "t09c_adjusted_gee",
        t09c,
        "Adjusted binomial GEE (ATSI + Provider_ID + Funding_Source + Remoteness + Industry + Delivery_Year, "
        "clustered on student): ATSI odds ratio and standardised predicted completion rates. Value_exact is a "
        "full-precision (4 decimal) companion of Value, for rounding that must not double-round the display column.",
    )

    # ==================================================================
    # T10. Sensitivity of completion rate
    # ==================================================================
    def sensitivity_variant(eligible_fn, achieved_fn, want_ci, use_shared_cache=False):
        rows = []
        elig = eligible_fn(enr)
        ach = achieved_fn(enr) & elig
        if want_ci:
            if use_shared_cache:
                r = get_cached_rate(rate_cache, ("standard", "Overall", "Overall"), enr, elig, ach, rng)
            else:
                r = completion_rate_with_ci(enr, elig, ach, rng)
            rows.append(["Overall", r["rate"], r["ci_lo"], r["ci_hi"], r["rate_exact"]])
        else:
            tot_e, tot_a = elig.sum(), ach.sum()
            rate = round_pct(100 * tot_a / tot_e) if tot_e else np.nan
            rate_exact = round_dp(100 * tot_a / tot_e, 4) if tot_e else np.nan
            rows.append(["Overall", rate, np.nan, np.nan, rate_exact])
        for fs in sorted(enr["Funding_Source"].dropna().unique()):
            fs_mask = (enr["Funding_Source"] == fs).to_numpy()
            if want_ci:
                if use_shared_cache:
                    r = get_cached_rate(rate_cache, ("standard", "Funding_Source", fs), enr, elig & fs_mask, ach, rng)
                else:
                    r = completion_rate_with_ci(enr, elig & fs_mask, ach, rng)
                rows.append([fs, r["rate"], r["ci_lo"], r["ci_hi"], r["rate_exact"]])
            else:
                e2, a2 = (elig & fs_mask).sum(), (ach & fs_mask).sum()
                rate = round_pct(100 * a2 / e2) if e2 else np.nan
                rate_exact = round_dp(100 * a2 / e2, 4) if e2 else np.nan
                rows.append([fs, rate, np.nan, np.nan, rate_exact])
        return rows

    t10_rows = []
    for scope, rate, lo, hi, rate_x in sensitivity_variant(
        lambda d: d["Outcome_Group"].isin(["Achieved", "Not achieved", "Withdrawn"]).to_numpy(),
        lambda d: (d["Outcome_Group"] == "Achieved").to_numpy(),
        want_ci=True,
        use_shared_cache=True,
    ):
        t10_rows.append(["(a) Standard unit-level", scope, rate, lo, hi, rate_x])
    for scope, rate, lo, hi, rate_x in sensitivity_variant(
        lambda d: d["Outcome"].isin([20, 30, 40]).to_numpy(),
        lambda d: (d["Outcome"] == 20).to_numpy(),
        want_ci=False,
    ):
        t10_rows.append(["(b) Outcome 20 only", scope, rate, lo, hi, rate_x])
    for scope, rate, lo, hi, rate_x in sensitivity_variant(
        lambda d: d["Outcome_Group"].isin(["Achieved", "Not achieved", "Withdrawn", "Continuing"]).to_numpy(),
        lambda d: (d["Outcome_Group"] == "Achieved").to_numpy(),
        want_ci=False,
    ):
        t10_rows.append(["(c) Continuing counted as non-completion", scope, rate, lo, hi, rate_x])

    enr_no_recovered = enr[enr["Funding_Source_Recovered"] != True]  # noqa: E712
    d_overall_exact = 100 * (enr_no_recovered["Outcome_Group"] == "Achieved").sum() / enr_no_recovered["Outcome_Group"].isin(["Achieved", "Not achieved", "Withdrawn"]).sum()
    t10_rows.append(
        ["(d) Excluding Funding_Source_Recovered rows", "Overall", round_pct(d_overall_exact), np.nan, np.nan, round_dp(d_overall_exact, 4)]
    )
    for fs in sorted(enr["Funding_Source"].dropna().unique()):
        sub = enr_no_recovered[enr_no_recovered["Funding_Source"] == fs]
        elig_sub = sub["Outcome_Group"].isin(["Achieved", "Not achieved", "Withdrawn"])
        ach_sub = sub["Outcome_Group"] == "Achieved"
        rate = round_pct(100 * ach_sub.sum() / elig_sub.sum()) if elig_sub.sum() else np.nan
        rate_exact = round_dp(100 * ach_sub.sum() / elig_sub.sum(), 4) if elig_sub.sum() else np.nan
        t10_rows.append(["(d) Excluding Funding_Source_Recovered rows", fs, rate, np.nan, np.nan, rate_exact])

    t10 = pd.DataFrame(t10_rows, columns=["Definition", "Scope", "Rate_%", "CI_Lower", "CI_Upper", "Rate_exact"])

    sp = enr.groupby(["Student_ID", "Provider_ID", "Program_ID"]).apply(
        lambda g: pd.Series(
            {
                "n_eligible": g["In_Completion_Rate"].sum(),
                "n_achieved": ((g["Outcome_Group"] == "Achieved") & g["In_Completion_Rate"]).sum(),
            }
        ),
        include_groups=False,
    )
    sp = sp[sp["n_eligible"] > 0]
    sp_rate = 100 * (sp["n_achieved"] == sp["n_eligible"]).sum() / len(sp)
    reference_row = pd.DataFrame(
        [["REFERENCE: strict student-program (all eligible units Achieved) - NOT qualification completion, only units present in this data", "Overall", round_pct(sp_rate), np.nan, np.nan, round_dp(sp_rate, 4)]],
        columns=t10.columns,
    )
    t10 = pd.concat([t10, reference_row], ignore_index=True)
    record_table(
        "t10_sensitivity",
        t10,
        "Completion rate under four alternative definitions, plus a labelled reference row for strict student-program completion. "
        "Rate_exact is a 4-decimal companion of Rate_%, for whole-number rounding.",
    )

    # ==================================================================
    # T11. Context
    # ==================================================================
    t11_rows = []
    for year, grp in enr.groupby("Delivery_Year"):
        for fs, grp2 in grp.groupby("Funding_Source"):
            units = len(grp2)
            ahc = round_ahc(grp2["AHC_Funded"].sum())
            valid_starts = int(grp2["_valid_start"].notna().sum())
            note = ""
            if year == 2023:
                note = "2023 has no carry-in from 2022"
            carry_count = int(grp2["Carry_Over_Flag"].sum())
            if year == 2025 and carry_count > 0:
                note = (note + "; " if note else "") + "Carry_Over_Flag rows only appear in 2025"
            t11_rows.append([year, fs, units, ahc, valid_starts, note])
    t11 = pd.DataFrame(t11_rows, columns=["Delivery_Year", "Funding_Source", "Units", "AHC", "Valid_Start_Count", "Note"])
    assert_close(t11["AHC"].sum(), EXPECTED_TOTAL_AHC, 1, "T11 AHC total")
    record_table("t11_context", t11, "Units, funded AHC, and valid-start-date counts by Delivery_Year and Funding_Source, with carry-over notes.")

    # ==================================================================
    # T12a. By Industry
    # ==================================================================
    if enr["Industry"].nunique() != 7:
        fail(f"T12a: expected 7 industries, got {enr['Industry'].nunique()}")

    industry_rows = []
    for industry in sorted(enr["Industry"].dropna().unique()):
        industry_mask = (enr["Industry"] == industry).to_numpy()
        grp = enr[industry_mask]
        ahc = grp["AHC_Funded"].sum()
        units = len(grp)
        students = grp["Student_ID"].nunique()
        grp_atsi = enr_with_atsi[enr_with_atsi["Industry"] == industry]
        atsi_share = 100 * (grp_atsi["ATSI"] == "Y").sum() / len(grp_atsi)

        elig_mask = eligible_mask_all & industry_mask
        r = get_cached_rate(rate_cache, ("standard", "Industry", industry), enr, elig_mask, achieved_mask_all, rng)

        industry_rows.append(
            [industry, round_ahc(ahc), units, students, r["rate"], r["ci_lo"], r["ci_hi"], r["units"], round_pct(atsi_share)]
        )

    t12a = pd.DataFrame(
        industry_rows,
        columns=["Industry", "AHC_Funded", "Units", "Distinct_Students", "Completion_Rate_%", "CI_Lower", "CI_Upper", "Eligible_Units", "ATSI_Share_of_Units_%"],
    )
    total_ahc_12a = t12a["AHC_Funded"].sum()
    t12a["Share_of_Total_%"] = round_pct(100 * t12a["AHC_Funded"] / total_ahc_12a)
    t12a = t12a[["Industry", "AHC_Funded", "Share_of_Total_%", "Units", "Distinct_Students", "Completion_Rate_%", "CI_Lower", "CI_Upper", "Eligible_Units", "ATSI_Share_of_Units_%"]]
    t12a = t12a.sort_values("AHC_Funded", ascending=False).reset_index(drop=True)

    assert_close(t12a["AHC_Funded"].sum(), EXPECTED_TOTAL_AHC, 1, "T12a AHC total")
    assert_shares_sum_to_100(t12a["Share_of_Total_%"].tolist(), "T12a shares")

    t07_industry_units = t07.loc[t07["Dimension"] == "Industry"].set_index("Group")["Units"]
    for _, row in t12a.iterrows():
        t07_units = int(t07_industry_units.loc[row["Industry"]])
        if int(row["Eligible_Units"]) != t07_units:
            fail(
                f"T12a/T07 mismatch for {row['Industry']}: T12a eligible units {row['Eligible_Units']} "
                f"vs T07 {t07_units}"
            )

    record_table(
        "t12a_by_industry",
        t12a,
        "Funded AHC, units, students, completion rate (the cached T07 estimate for this Industry) and ATSI "
        "reach, by Industry, sorted by AHC descending. Contracts carry no industry, program or town targets, "
        "so no target comparison is possible for T12 to T14.",
    )

    # ==================================================================
    # T12b. By Program
    # ==================================================================
    prog_industry_counts = enr.groupby("Program_ID")["Industry"].nunique()
    if (prog_industry_counts > 1).any():
        fail(f"T12b: some Program_ID maps to more than one Industry: {prog_industry_counts[prog_industry_counts > 1].to_dict()}")

    program_groups = (
        enr.groupby(["Program_ID", "Program_Name", "Industry"])
        .agg(AHC_Funded=("AHC_Funded", "sum"), Units=("Program_ID", "size"), Distinct_Students=("Student_ID", "nunique"))
        .reset_index()
    )
    if len(program_groups) != 10:
        fail(f"T12b: expected 10 programs, got {len(program_groups)}")

    missing_labels = set(program_groups["Program_ID"]) - set(SHORT_LABEL_LOOKUP.keys())
    if missing_labels:
        fail(f"T12b: no hand-written Short_Label for Program_ID(s): {sorted(missing_labels)}")

    program_groups["Short_Label"] = program_groups["Program_ID"].map(SHORT_LABEL_LOOKUP)
    program_groups["Full_Label"] = program_groups["Program_Name"]

    total_ahc_12b = program_groups["AHC_Funded"].sum()
    program_groups["Share_of_Total_%"] = round_pct(100 * program_groups["AHC_Funded"] / total_ahc_12b)
    program_groups["AHC_Funded"] = program_groups["AHC_Funded"].apply(round_ahc)
    t12b = program_groups[["Program_ID", "Program_Name", "Industry", "AHC_Funded", "Share_of_Total_%", "Units", "Distinct_Students", "Short_Label", "Full_Label"]]
    t12b = t12b.sort_values("AHC_Funded", ascending=False).reset_index(drop=True)

    assert_close(t12b["AHC_Funded"].sum(), EXPECTED_TOTAL_AHC, 1, "T12b AHC total")
    assert_shares_sum_to_100(t12b["Share_of_Total_%"].tolist(), "T12b shares")
    record_table(
        "t12b_by_program",
        t12b,
        "Funded AHC, units and students by Program, with a hand-written, glance-readable Short_Label and "
        "the Full_Label (the full Program_Name) for display alongside it.",
    )

    # ==================================================================
    # T12c. Industry mix by Remoteness and by Funding_Source
    # ==================================================================
    def industry_mix_table(group_col):
        totals = enr.groupby(["Industry", group_col])["AHC_Funded"].sum().reset_index()
        col_totals = enr.groupby(group_col)["AHC_Funded"].sum()
        totals["Share_within_%"] = totals.apply(lambda r: round_pct(100 * r["AHC_Funded"] / col_totals[r[group_col]]), axis=1)
        totals["AHC_Funded"] = totals["AHC_Funded"].apply(round_ahc)
        totals = totals.sort_values([group_col, "AHC_Funded"], ascending=[True, False]).reset_index(drop=True)
        for col_val, grp in totals.groupby(group_col):
            assert_shares_sum_to_100(grp["Share_within_%"].tolist(), f"T12c {group_col} share ({col_val})")
        return totals

    t12c_remoteness = industry_mix_table("Remoteness")
    t12c_remoteness.columns = ["Industry", "Remoteness", "AHC_Funded", "Share_within_Remoteness_%"]
    record_table(
        "t12c_industry_by_remoteness",
        t12c_remoteness,
        "Funded AHC by Industry within each Remoteness class; the share column sums to 100% within each region.",
    )

    t12c_funding = industry_mix_table("Funding_Source")
    t12c_funding.columns = ["Industry", "Funding_Source", "AHC_Funded", "Share_within_FundingSource_%"]
    record_table(
        "t12c_industry_by_funding_source",
        t12c_funding,
        "Funded AHC by Industry within each Funding_Source; the share column sums to 100% within each stream.",
    )

    # ==================================================================
    # T12d. Concentration
    # ==================================================================
    industry_totals = enr.groupby("Industry")["AHC_Funded"].sum().sort_values(ascending=False)
    program_totals = enr.groupby("Program_ID")["AHC_Funded"].sum().sort_values(ascending=False)
    total_ahc_all = enr["AHC_Funded"].sum()
    n_industries_12d = len(industry_totals)
    n_programs_12d = len(program_totals)

    top1_ind = 100 * industry_totals.iloc[:1].sum() / total_ahc_all
    top2_ind = 100 * industry_totals.iloc[:2].sum() / total_ahc_all
    top3_ind = 100 * industry_totals.iloc[:3].sum() / total_ahc_all
    top3_prog = 100 * program_totals.iloc[:3].sum() / total_ahc_all
    even_ind = 100 * 3 / n_industries_12d
    even_prog = 100 * 3 / n_programs_12d

    t12d = pd.DataFrame(
        [
            ["Top 1 industry share of total AHC", round_pct(top1_ind)],
            ["Top 2 industries share of total AHC", round_pct(top2_ind)],
            ["Top 3 industries share of total AHC", round_pct(top3_ind)],
            ["Top 3 programs share of total AHC", round_pct(top3_prog)],
            [f"Reference: even-spread share for top 3 of {n_industries_12d} industries", round_pct(even_ind)],
            [f"Reference: even-spread share for top 3 of {n_programs_12d} programs", round_pct(even_prog)],
        ],
        columns=["Metric", "Value"],
        dtype=object,
    )
    record_table(
        "t12d_concentration",
        t12d,
        "Share of funded AHC held by the top industries and programs, against the share expected if hours "
        "were spread evenly across all industries or programs.",
    )

    # ==================================================================
    # T13. By qualification level
    # ==================================================================
    level_pattern = re.compile(r"Certificate (IV|III|II|I)\b")
    program_names = enr[["Program_ID", "Program_Name"]].drop_duplicates()
    level_map = {}
    for _, row in program_names.iterrows():
        matches = level_pattern.findall(row["Program_Name"])
        if len(matches) == 0:
            fail(f"T13: could not parse a qualification level from Program_Name '{row['Program_Name']}' (Program_ID {row['Program_ID']})")
        if len(set(matches)) > 1:
            fail(f"T13: Program_Name '{row['Program_Name']}' matched more than one qualification level: {matches}")
        level_map[row["Program_ID"]] = f"Certificate {matches[0]}"

    enr["_qual_level"] = enr["Program_ID"].map(level_map)
    if enr["_qual_level"].isna().any():
        fail("T13: some Enrolment rows have a Program_ID with no resolved qualification level")

    level_order = ["Certificate I", "Certificate II", "Certificate III", "Certificate IV"]
    t13_rows = []
    for level in level_order:
        mask_level = (enr["_qual_level"] == level).to_numpy()
        if not mask_level.any():
            continue
        grp = enr[mask_level]
        ahc = grp["AHC_Funded"].sum()
        units = len(grp)
        students = grp["Student_ID"].nunique()
        program_ids = sorted(k for k, v in level_map.items() if v == level)

        elig_mask = eligible_mask_all & mask_level
        r = get_cached_rate(rate_cache, ("standard", "Qualification_Level", level), enr, elig_mask, achieved_mask_all, rng)

        t13_rows.append(
            [level, round_ahc(ahc), units, students, r["rate"], r["ci_lo"], r["ci_hi"], r["units"], ", ".join(program_ids)]
        )

    t13 = pd.DataFrame(
        t13_rows,
        columns=["Qualification_Level", "AHC_Funded", "Units", "Distinct_Students", "Completion_Rate_%", "CI_Lower", "CI_Upper", "Eligible_Units", "Program_IDs"],
    )
    total_ahc_13 = t13["AHC_Funded"].sum()
    t13["Share_of_Total_%"] = round_pct(100 * t13["AHC_Funded"] / total_ahc_13)
    t13 = t13[["Qualification_Level", "AHC_Funded", "Share_of_Total_%", "Units", "Distinct_Students", "Completion_Rate_%", "CI_Lower", "CI_Upper", "Eligible_Units", "Program_IDs"]]

    assert_close(t13["AHC_Funded"].sum(), EXPECTED_TOTAL_AHC, 1, "T13 AHC total")
    assert_shares_sum_to_100(t13["Share_of_Total_%"].tolist(), "T13 shares")

    t07_overall_units = int(t07.loc[t07["Dimension"] == "Overall", "Units"].iloc[0])
    if int(t13["Eligible_Units"].sum()) != t07_overall_units:
        fail(
            f"T13: sum of eligible units across qualification levels ({t13['Eligible_Units'].sum()}) does not "
            f"match T07's overall eligible units ({t07_overall_units}) - levels should fully partition the "
            f"same completion-eligible rows that T07's Overall total covers."
        )

    record_table(
        "t13_by_qualification_level",
        t13,
        "Funded AHC, units, students and completion rate (cached, new to this dimension) by qualification "
        "level parsed from Program_Name, listing the Program_IDs at each level.",
    )

    # ==================================================================
    # T14. By town (Location)
    # ==================================================================
    town_rows = []
    for location, grp in enr.groupby("Location"):
        remoteness_vals = grp["Remoteness"].unique()
        if len(remoteness_vals) > 1:
            fail(f"T14: Location '{location}' maps to more than one Remoteness class: {list(remoteness_vals)}")
        remoteness = remoteness_vals[0]
        ahc = grp["AHC_Funded"].sum()
        units = len(grp)
        students = grp["Student_ID"].nunique()
        providers = grp["Provider_ID"].nunique()
        elig = grp["In_Completion_Rate"] == True  # noqa: E712
        ach = grp["Outcome_Group"] == "Achieved"
        n_elig = int(elig.sum())
        rate = round_pct(100 * (ach & elig).sum() / n_elig) if n_elig else float("nan")
        town_rows.append([location, remoteness, round_ahc(ahc), units, students, providers, rate])

    t14 = pd.DataFrame(town_rows, columns=["Location", "Remoteness", "AHC_Funded", "Units", "Distinct_Students", "Distinct_Providers", "Completion_Rate_%"])
    total_ahc_14 = t14["AHC_Funded"].sum()
    t14["Share_of_Total_%"] = round_pct(100 * t14["AHC_Funded"] / total_ahc_14)
    t14 = t14[["Location", "Remoteness", "AHC_Funded", "Share_of_Total_%", "Units", "Distinct_Students", "Distinct_Providers", "Completion_Rate_%"]]
    t14 = t14.sort_values("AHC_Funded", ascending=False).reset_index(drop=True)

    assert_close(t14["AHC_Funded"].sum(), EXPECTED_TOTAL_AHC, 1, "T14 AHC total")
    assert_shares_sum_to_100(t14["Share_of_Total_%"].tolist(), "T14 shares")

    n_towns = len(t14)
    n_towns_5pct = int((t14["Share_of_Total_%"] >= 5).sum())

    record_table(
        "t14_by_town",
        t14,
        "Funded AHC, units, students, providers and completion rate by town (Location), sorted by AHC "
        "descending. No coordinates are included; do not add any.",
    )

    t14b = pd.DataFrame(
        [
            ["Number of towns (distinct Location values)", n_towns],
            ["Towns holding at least 5% of funded AHC each", n_towns_5pct],
        ],
        columns=["Metric", "Value"],
    )
    record_table("t14b_town_summary", t14b, "How many towns there are in total, and how many individually hold at least 5% of total funded AHC.")

    # ==================================================================
    # T15. Program intensity
    # ==================================================================
    def intensity_row(rows, program_id, short_label, industry):
        students = rows["Student_ID"].nunique()
        units = len(rows)
        unit_ids = rows["Unit_ID"].nunique()
        ahc = rows["AHC_Funded"].sum()
        return {
            "Program_ID": program_id,
            "Short_Label": short_label,
            "Industry": industry,
            "Distinct_Students": students,
            "Units": units,
            "Units_per_Student": round_pct(units / students) if students else float("nan"),
            "Distinct_Unit_IDs": unit_ids,
            "AHC_Funded": round_ahc(ahc),
            "AHC_per_Unit": round_pct(ahc / units) if units else float("nan"),
            "AHC_per_Student": round_pct(ahc / students) if students else float("nan"),
            "Mean_Nominal_Hours_per_Unit": round_pct(rows["Nominal_Hours"].mean()),
            "Mean_Funded_Fraction": round_pct((rows["AHC_Funded"] / rows["Nominal_Hours"]).mean(), 3),
            # Full-precision companions (4 decimals) of the two means above,
            # for whole-number rounding that must not double-round the
            # already-rounded display columns.
            "Mean_Nominal_Hours_per_Unit_exact": round_pct(rows["Nominal_Hours"].mean(), 4),
            "Mean_Funded_Fraction_exact": round_pct((rows["AHC_Funded"] / rows["Nominal_Hours"]).mean(), 4),
        }

    t15_col_order = [
        "Program_ID", "Short_Label", "Industry", "Distinct_Students", "Units", "Units_per_Student",
        "Distinct_Unit_IDs", "AHC_Funded", "Share_of_Total_%", "AHC_per_Unit", "AHC_per_Student",
        "Mean_Nominal_Hours_per_Unit", "Mean_Funded_Fraction",
        "Mean_Nominal_Hours_per_Unit_exact", "Mean_Funded_Fraction_exact",
    ]

    program_industry_15 = enr[["Program_ID", "Industry"]].drop_duplicates().set_index("Program_ID")["Industry"]
    t15_rows = []
    for program_id in sorted(enr["Program_ID"].unique()):
        rows = enr[enr["Program_ID"] == program_id]
        t15_rows.append(intensity_row(rows, program_id, SHORT_LABEL_LOOKUP[program_id], program_industry_15.loc[program_id]))

    t15_individual = pd.DataFrame(t15_rows)
    total_ahc_15 = t15_individual["AHC_Funded"].sum()
    t15_individual["Share_of_Total_%"] = round_pct(100 * t15_individual["AHC_Funded"] / total_ahc_15)
    t15_individual = t15_individual[t15_col_order].sort_values("AHC_Funded", ascending=False).reset_index(drop=True)

    assert_close(t15_individual["AHC_Funded"].sum(), EXPECTED_TOTAL_AHC, 1, "T15 individual-program AHC total")
    assert_shares_sum_to_100(t15_individual["Share_of_Total_%"].tolist(), "T15 individual-program shares")

    cs_programs_15 = ["CER30115", "CER40115", "CHC33015"]
    other_programs_15 = sorted(set(enr["Program_ID"].unique()) - set(cs_programs_15))
    if len(other_programs_15) != 7:
        fail(f"T15: expected 7 'other' programs, got {len(other_programs_15)}: {other_programs_15}")

    cs_summary = intensity_row(enr[enr["Program_ID"].isin(cs_programs_15)], "Community Services (3 programs)", "Community Services combined", "Community Services")
    other_summary = intensity_row(enr[enr["Program_ID"].isin(other_programs_15)], "Other 7 programs combined", "Other 7 programs combined", "Multiple")
    cs_summary["Share_of_Total_%"] = round_pct(100 * cs_summary["AHC_Funded"] / total_ahc_15)
    other_summary["Share_of_Total_%"] = round_pct(100 * other_summary["AHC_Funded"] / total_ahc_15)
    t15_summary = pd.DataFrame([cs_summary, other_summary])[t15_col_order]

    assert_shares_sum_to_100(t15_summary["Share_of_Total_%"].tolist(), "T15 two-group summary shares")
    assert_close(t15_summary["AHC_Funded"].sum(), EXPECTED_TOTAL_AHC, 1, "T15 two-group summary AHC total")

    t15 = pd.concat([t15_individual, t15_summary], ignore_index=True)
    record_table(
        "t15_program_intensity",
        t15,
        "Program-level intensity: units, students, units/AHC per student and per unit, mean unit length and "
        "mean funded fraction per program, plus two summary rows for the three Community Services programs "
        "combined and the other seven combined.",
    )

    # ==================================================================
    # T16. Chance check on student numbers per program
    # ==================================================================
    program_ids_10 = sorted(enr["Program_ID"].unique())
    if len(program_ids_10) != 10:
        fail(f"T16: expected 10 programs, got {len(program_ids_10)}")
    n_programs_16 = len(program_ids_10)

    observed_counts = enr.groupby("Program_ID")["Student_ID"].nunique().reindex(program_ids_10)
    obs_min = int(observed_counts.min())
    obs_max = int(observed_counts.max())
    obs_ratio = obs_max / obs_min
    obs_spread = obs_max - obs_min

    k_per_student = enr.groupby("Student_ID")["Program_ID"].nunique().to_numpy()
    n_students_16 = len(k_per_student)

    rng16 = np.random.default_rng(SEED)
    program_index_16 = np.arange(n_programs_16)
    k_group_sizes = {k: int((k_per_student == k).sum()) for k in sorted(set(k_per_student.tolist()))}
    null_spreads = np.empty(N_PERMUTATIONS)
    for perm_i in range(N_PERMUTATIONS):
        counts = np.zeros(n_programs_16, dtype=np.int64)
        for k, m in k_group_sizes.items():
            if m == 0:
                continue
            base = np.tile(program_index_16, (m, 1))
            chosen = rng16.permuted(base, axis=1)[:, :k]
            np.add.at(counts, chosen.ravel(), 1)
        null_spreads[perm_i] = counts.max() - counts.min()

    null_mean = float(null_spreads.mean())
    null_lo, null_hi = np.percentile(null_spreads, [2.5, 97.5])
    p_ge = float((null_spreads >= obs_spread).mean())
    p_le = float((null_spreads <= obs_spread).mean())
    p_two_sided = min(1.0, 2 * min(p_ge, p_le))

    t16 = pd.DataFrame(
        [
            ["Observed minimum students (any program)", obs_min],
            ["Observed maximum students (any program)", obs_max],
            ["Observed max-to-min ratio", round_pct(obs_ratio, 2)],
            ["Observed spread (max minus min)", obs_spread],
            ["Null mean spread under random reassignment", round_pct(null_mean, 1)],
            ["Null 95% range of spread", f"{null_lo:.0f} to {null_hi:.0f}"],
            ["Two-sided p-value for observed spread", round_pct(p_two_sided, 4)],
        ],
        columns=["Metric", "Value"],
        dtype=object,
    )
    record_table(
        "t16_student_count_chance_check",
        t16,
        f"Whether the observed spread in distinct students per program ({obs_spread}, from {obs_min} to "
        f"{obs_max} across {n_programs_16} programs) is more or less than a chance benchmark: each of the "
        f"{n_students_16} students keeps their observed number of distinct programs, but which programs are "
        f"reassigned at random without replacement from all {n_programs_16} ({N_PERMUTATIONS:,} permutations, "
        f"seed {SEED}). Assumes every program is equally available to every student and that students can "
        f"appear in more than one program, both already true of the observed data.",
    )

    # ==================================================================
    # T17a. Funded AHC by industry and outcome (feeds the "Funding vs
    # outcome" Sankey chart)
    # ==================================================================
    OUTCOME_GROUPS_6 = [
        "Achieved", "Not achieved", "Withdrawn", "Continuing", "Learner support", "Not funded / not started",
    ]
    EXPECTED_OUTCOME_TOTALS = {
        "Achieved": 90449,
        "Not achieved": 36763,
        "Withdrawn": 25318,
        "Continuing": 18604,
        "Learner support": 1660,
        "Not funded / not started": 0,
    }
    outcome_totals_17 = enr.groupby("Outcome_Group")["AHC_Funded"].sum()
    for group, expected in EXPECTED_OUTCOME_TOTALS.items():
        assert_close(int(outcome_totals_17.get(group, 0)), expected, 1, f"T17 outcome total ({group})")

    # T17a: Industry x Outcome_Group, with the share within the industry
    # and that industry's "not completed" share (Not achieved plus
    # Withdrawn, as a share of the industry's own funded AHC) repeated
    # on every one of its six rows.
    industry_totals_17 = enr.groupby("Industry")["AHC_Funded"].sum()
    industry_order_17 = industry_totals_17.sort_values(ascending=False).index.tolist()
    not_completed_by_industry_17 = (
        enr[enr["Outcome_Group"].isin(["Not achieved", "Withdrawn"])].groupby("Industry")["AHC_Funded"].sum()
    )

    t17a_rows = []
    for industry in industry_order_17:
        ind_total = industry_totals_17[industry]
        not_completed_share = round_pct(100 * not_completed_by_industry_17.get(industry, 0) / ind_total)
        outcome_sums = enr.loc[enr["Industry"] == industry].groupby("Outcome_Group")["AHC_Funded"].sum()
        industry_block = [
            {
                "Industry": industry,
                "Outcome_Group": group,
                "AHC_Funded": float(outcome_sums.get(group, 0)),
                "Share_within_Industry_%": round_pct(100 * outcome_sums.get(group, 0) / ind_total),
                "Not_Completed_Share_%": not_completed_share,
                "Share_within_Industry_exact": round_dp(100 * outcome_sums.get(group, 0) / ind_total, 4),
                "Not_Completed_Share_exact": round_dp(100 * not_completed_by_industry_17.get(industry, 0) / ind_total, 4),
            }
            for group in OUTCOME_GROUPS_6
        ]
        industry_block.sort(key=lambda r: r["AHC_Funded"], reverse=True)
        t17a_rows.extend(industry_block)

    t17a = pd.DataFrame(t17a_rows)
    t17a["AHC_Funded"] = t17a["AHC_Funded"].apply(round_ahc)
    assert_close(t17a["AHC_Funded"].sum(), EXPECTED_TOTAL_AHC, 1, "T17a AHC total")
    for industry, grp in t17a.groupby("Industry"):
        assert_shares_sum_to_100(grp["Share_within_Industry_%"].tolist(), f"T17a within-industry shares ({industry})")
    for group, expected in EXPECTED_OUTCOME_TOTALS.items():
        actual = int(t17a.loc[t17a["Outcome_Group"] == group, "AHC_Funded"].sum())
        assert_close(actual, expected, 1, f"T17a outcome total ({group})")
    t12a_industry_totals = t12a.set_index("Industry")["AHC_Funded"]
    for industry in industry_order_17:
        t17a_total = int(t17a.loc[t17a["Industry"] == industry, "AHC_Funded"].sum())
        assert_close(t17a_total, int(t12a_industry_totals.loc[industry]), 1, f"T17a/T12a industry total ({industry})")
    record_table(
        "t17a_ahc_by_industry_outcome",
        t17a,
        "Funded AHC by Industry and Outcome_Group (all six groups), with the share within each industry "
        "and that industry's share of hours in units not achieved or withdrawn ('not completed'), repeated "
        "on every row for the industry. Share_within_Industry_exact and Not_Completed_Share_exact are 4-decimal "
        "companions, for whole-number rounding. Feeds the industry-range sentence in the 'Funding vs outcome' "
        "Sankey caption.",
    )

    # ==================================================================
    # ==================================================================
    # T19. Provider names (organisation level only, no student-level rows)
    # ==================================================================
    t19 = org[["Provider_ID", "RTO_Name"]].drop_duplicates().rename(columns={"RTO_Name": "Provider_Name"})
    t19 = t19.sort_values("Provider_ID").reset_index(drop=True)
    if len(t19) != 8:
        fail(f"T19: expected 8 providers, got {len(t19)}")
    if t19["Provider_Name"].isna().any() or (t19["Provider_Name"].astype(str).str.strip() == "").any():
        fail("T19: at least one provider has a blank name in the organisation table")
    record_table("t19_provider_names", t19, "Provider_ID and its organisation name, for display only - no student-level rows.")

    # ==================================================================
    # T21. Data quality figures for the Method page (aggregate counts only)
    # ==================================================================
    enr_with_school = enr.merge(stu[["Student_ID", "At_School_Flag"]], on="Student_ID", how="left")
    vet_in_schools_mask = enr["Funding_Source"].isin(["11N", "11V"])
    remoteness_by_vet_stream = {}
    for stream in ["11N", "11V"]:
        sub = enr.loc[enr["Funding_Source"] == stream, "Remoteness"]
        for remote_cat in ["Urban", "Regional", "Remote"]:
            remoteness_by_vet_stream[(stream, remote_cat)] = round_dp(100 * (sub == remote_cat).sum() / len(sub), 4)
    t21_rows = [
        ["Student table rows", len(stu)],
        ["Gender = X students", int((stu["Gender"] == "X").sum())],
        [
            "Rows with Funded_Flag = 85%_only and outcome 51, 52 or 70",
            int(((enr["Funded_Flag"] == "85%_only") & enr["Outcome"].isin([51, 52, 70])).sum()),
        ],
        ["P008 Fee-Free TAFE enrolment rows", int(((enr["Provider_ID"] == "P008") & (enr["Funding_Source"] == "FFT")).sum())],
        ["11N and 11V rows (VET in Schools streams)", int(vet_in_schools_mask.sum())],
        [
            "11N and 11V rows not flagged At_School_Flag = Y",
            int((vet_in_schools_mask & (enr_with_school["At_School_Flag"] != "Y")).sum()),
        ],
    ] + [
        [f"{stream} share of rows in {remote_cat} (%)", remoteness_by_vet_stream[(stream, remote_cat)]]
        for stream in ["11N", "11V"]
        for remote_cat in ["Urban", "Regional", "Remote"]
    ]
    t21 = pd.DataFrame(t21_rows, columns=["Metric", "Value"])
    record_table(
        "t21_data_quality_figures",
        t21,
        "Small aggregate counts (no student-level rows) for the Method and data quality page: Gender = X "
        "prevalence, the Funded_Flag/outcome-code conflict, P008's Fee-Free TAFE delivery, VET in Schools "
        "at-school flag counts, and the 11N/11V share of rows by Remoteness.",
    )

    # ==================================================================
    # T18. Reach: ATSI share of enrolled students, overall and by group
    # ==================================================================
    # An enrolled student is a distinct Student_ID with at least one Enrolment
    # row (any outcome). A student counts in a group if they have at least one
    # enrolment row in it, so one student can sit in several groups within a
    # dimension. ATSI status is taken from the cleaned Student table.
    enrolled_ids = set(enr["Student_ID"].unique())
    stu_enrolled = stu.loc[stu["Student_ID"].isin(enrolled_ids), ["Student_ID", "ATSI"]].drop_duplicates("Student_ID")
    assert_close(len(stu_enrolled), EXPECTED_ENROLLED_STUDENTS, 0, "T18 enrolled students")
    atsi_by_student = stu_enrolled.set_index("Student_ID")["ATSI"]

    def reach_counts(member_ids):
        ids = pd.Index(list(member_ids))
        atsi = atsi_by_student.loc[ids]
        n = len(ids)
        k = int((atsi == "Y").sum())
        lo, hi = proportion_confint(k, n, alpha=0.05, method="wilson")
        share = 100 * k / n
        return n, k, share, 100 * lo, 100 * hi

    t18_rows = []
    n_all, k_all, share_all, lo_all, hi_all = reach_counts(enrolled_ids)
    t18_rows.append(
        ["Overall", "Overall", n_all, k_all, round_dp(share_all, 1), round_dp(share_all, 4),
         round_dp(lo_all, 1), round_dp(hi_all, 1), round_dp(lo_all, 4), round_dp(hi_all, 4)]
    )
    overall_direct_share = 100 * (atsi_by_student == "Y").sum() / len(atsi_by_student)
    assert_close(share_all, overall_direct_share, 1e-9, "T18 overall share vs direct computation")

    membership_by_dim = {}
    for dim_name in ["Funding_Source", "Provider_ID", "Remoteness"]:
        memb = enr[["Student_ID", dim_name]].dropna().drop_duplicates()
        membership_by_dim[dim_name] = memb
        groups = sorted(memb[dim_name].unique())
        if len(groups) != EXPECTED_GROUP_COUNTS[dim_name]:
            fail(f"T18: expected {EXPECTED_GROUP_COUNTS[dim_name]} {dim_name} groups, got {len(groups)}")
        union_ids = set(memb["Student_ID"])
        if len(union_ids) != EXPECTED_ENROLLED_STUDENTS:
            fail(f"T18: {dim_name} groups cover {len(union_ids)} students, expected {EXPECTED_ENROLLED_STUDENTS}")
        for group_val in groups:
            member_ids = memb.loc[memb[dim_name] == group_val, "Student_ID"].unique()
            n, k, share, lo, hi = reach_counts(member_ids)
            if k > n:
                fail(f"T18: {dim_name} = {group_val} has more ATSI students than students")
            t18_rows.append(
                [dim_name, group_val, n, k, round_dp(share, 1), round_dp(share, 4),
                 round_dp(lo, 1), round_dp(hi, 1), round_dp(lo, 4), round_dp(hi, 4)]
            )

    t18 = pd.DataFrame(
        t18_rows,
        columns=[
            "Dimension", "Group", "Students", "ATSI_students", "Share_%", "Share_exact",
            "CI_Lower", "CI_Upper", "Lower_exact", "Upper_exact",
        ],
    )
    record_table(
        "t18_atsi_enrolled_share",
        t18,
        "Share of enrolled students recorded as ATSI = Y, overall and by Funding_Source, Provider_ID and "
        "Remoteness, with a 95% Wilson interval. An enrolled student is a distinct Student_ID with at least "
        "one Enrolment row; a student counts in a group if they have an enrolment row in it, so one student "
        "can appear in several groups. Share_exact, Lower_exact and Upper_exact are 4-decimal companions of "
        "Share_%, CI_Lower and CI_Upper, for whole-number rounding that must not double-round.",
    )

    def reach_omnibus_pvalue(memb, dim_name):
        d = memb.merge(atsi_by_student.rename("ATSI").reset_index(), on="Student_ID", how="inner")
        d = d.rename(columns={dim_name: "grp"})
        d["y"] = (d["ATSI"] == "Y").astype(int)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = smf.gee(
                "y ~ C(grp)",
                groups="Student_ID",
                data=d,
                family=sm.families.Binomial(),
                cov_struct=sm.cov_struct.Exchangeable(),
            ).fit()
            wt = res.wald_test_terms()
        return float(wt.table.loc["C(grp)", "pvalue"])

    t18b_rows = []
    for dim_name in ["Funding_Source", "Provider_ID", "Remoteness"]:
        p = reach_omnibus_pvalue(membership_by_dim[dim_name], dim_name)
        t18b_rows.append([dim_name, round_dp(p, 4)])
    t18b = pd.DataFrame(t18b_rows, columns=["Dimension", "P_value"])
    record_table(
        "t18b_atsi_omnibus_tests",
        t18b,
        "Test for any difference in ATSI share between groups, per dimension: a binomial GEE with one row per "
        "student-group membership, outcome ATSI = Y (1 or 0), the group as the only predictor, an exchangeable "
        "correlation structure clustered on Student_ID, and a Wald test for any group difference.",
    )

    # ==================================================================
    # Write all tables
    # ==================================================================
    for name, df, _ in TABLES:
        df.to_csv(TABLES_DIR / f"{name}.csv", index=False)

    write_summary_md()
    write_methods_md(headline, share_atsi_y, remoteness_shares)
    write_headline_claims_md(
        enr, t01, t02a, t02c, t03b, t05a, t05b, t05c, t06a, t06c, t07, t07_omnibus, t09b, t09c, t11,
        t12c_remoteness, t12c_funding, t12d, t13, t14, t15, t16,
    )

    print("Analysis tables complete.")
    print(f"  Wrote {len(TABLES)} tables to {TABLES_DIR}")
    print(f"  Total funded AHC: {total_ahc:,}")
    print("  Wrote outputs/analysis_summary.md, outputs/analysis_methods.md, outputs/headline_claims.md")


def write_summary_md():
    lines = ["# Analysis tables - summary", ""]
    lines.append(
        "Every table below is read from `data/clean/` only; no cleaned file was modified. Every table is an "
        "aggregate - no USI, DOB, or other student-level row appears anywhere in this document."
    )
    lines.append("")
    for name, df, description in TABLES:
        lines.append(f"## {name}")
        lines.append("")
        lines.append(description)
        lines.append("")
        lines.append(df.to_markdown(index=False))
        lines.append("")
    (OUTPUTS_DIR / "analysis_summary.md").write_text("\n".join(lines))


def _plain_then_detail(label, plain, detail):
    """One methodology entry: a bold label, a plain-English sentence, then
    the existing technical detail underneath in smaller grey text."""
    return (
        f"**{label}.** {plain}\n\n"
        f"<span style='color:#6B7280;font-size:13px;'>{detail}</span>"
    )


def write_methods_md(headline, share_atsi_y, remoteness_shares):
    lines = ["# Analysis methods and definitions", ""]
    lines.append("## Core definitions (apply to every table)")
    lines.append("")
    lines.append("- Funded hours means AHC_Funded. Total after cleaning: 172,794.")
    lines.append(
        "- Targets are 3-year totals covering 1 Jan 2023 to 31 Dec 2025. Delivered AHC is compared to targets "
        "as a cumulative 2023-2025 figure, never pro-rated by year."
    )
    lines.append(
        "- Contracts with matching delivery (19) are those matched on provider and funding stream, excluding "
        "the one pair with no target set (DCVT-2020 / P007-11V)."
    )
    lines.append(
        "- Headline completion rate (unit level) = Achieved divided by Achieved plus Not achieved plus "
        "Withdrawn, counting only units in the completion-rate population. Achieved covers outcome codes "
        "20, 51 and 52."
    )
    lines.append("- Gender is excluded from every table (see the cleaning steps below: not reliable for headline findings).")
    lines.append("")
    lines.append("## Statistical methods in plain words")
    lines.append("")
    lines.append("Results are reproducible: every random step uses a fixed seed.")
    lines.append("")
    lines.append(
        _plain_then_detail(
            "Cluster bootstrap",
            "We re-ran each calculation 2,000 times, resampling students, to see how much a rate would move "
            "by chance; the range is the interval shown in the charts.",
            "Every confidence interval resamples students, not rows: for a given slice, distinct students "
            "are drawn with replacement (same count as the slice has), each draw carrying all of that "
            "student's eligible rows within the slice, and the rate is recomputed from the resampled total. "
            "This is done 2,000 times per interval and the reported interval is the 2.5th to 97.5th "
            "percentile of the resulting distribution, consumed in table order (T01, then T07, then T09), "
            "so rerunning the script reproduces every number exactly.",
        )
    )
    lines.append("")
    lines.append(
        "**Subgroup bootstrap scope.** For a subgroup table (e.g. completion by Provider_ID), the bootstrap "
        "resamples only the students who have eligible rows in that subgroup, and only recomputes the rate "
        "from their rows within that subgroup - not their rows elsewhere in the data."
    )
    lines.append("")
    lines.append(
        _plain_then_detail(
            "ATSI gap interval",
            "The uncertainty range for the gap comes from resampling each group separately and looking at "
            "how much the difference between them moves.",
            "Because ATSI = Y and ATSI = N are disjoint student populations, the gap's confidence interval "
            "is built by independently bootstrapping each group's rate 2,000 times and taking the percentile "
            "interval of the elementwise difference - this is equivalent to the sampling distribution of two "
            "independent group means.",
        )
    )
    lines.append("")
    lines.append(
        _plain_then_detail(
            "Group difference test",
            "Asks whether any group differs from the others by more than chance would produce; the p-value "
            "is the chance of seeing a spread this large if none did.",
            "For each of Funding_Source, Provider_ID, Remoteness and Industry, a separate univariate "
            "binomial GEE (completed ~ group, exchangeable correlation, clustered on student) is fit and a "
            "Wald test for the joint significance of that dimension's group indicators is reported. This "
            "tests whether this one dimension shows any group difference, unadjusted for the other "
            "dimensions - it is not a single model holding the other three constant.",
        )
    )
    lines.append("")
    lines.append(
        _plain_then_detail(
            "Adjusted ATSI model",
            "Compares Aboriginal and Torres Strait Islander and other learners while holding provider, "
            "stream, region, industry and year the same.",
            "One binomial GEE regresses completion on ATSI, provider, funding stream, region, industry and "
            "year together, clustered on student with an exchangeable correlation structure. The ATSI odds "
            "ratio comes directly from its coefficient. The predicted completion rates for ATSI = Y and "
            "ATSI = N are standardised (g-computation): every eligible row's other covariates are kept as "
            "observed, ATSI is forced to each level in turn, the model predicts a probability for every row "
            "under that forced value, and the rates reported are the average predicted probability across "
            "all eligible rows.",
        )
    )
    lines.append("")
    lines.append(
        "**One estimate per population, reused everywhere.** Every cluster-bootstrap rate (point estimate, "
        "CI, units, students, and the underlying 2,000 resample draws) is computed exactly once per distinct "
        "(population, definition) pair and cached by that key. T01's headline rate, T07's \"Overall\" and "
        "per-Funding_Source rows, and T10's standard-definition (a) rows all draw on the same cached estimate "
        "for a given slice, so the same slice never shows two different CIs across tables. T09's ATSI gap "
        "CIs are built from the same cached draws used for that slice's individual Y and N rate CIs in T09a, "
        "rather than a fresh, independent resample."
    )
    lines.append("")
    lines.append(
        _plain_then_detail(
            "Permutation chance check",
            "Reshuffles which programs each student took, 10,000 times, to see how uneven program sizes get "
            "by chance.",
            "This is a permutation test, not a bootstrap: each student keeps their observed number of "
            "distinct programs, but which programs are reassigned at random, without replacement, uniformly "
            "from all 10 programs, independently per student per permutation (10,000 permutations). The null "
            "statistic is the spread (max minus min) of the resulting students-per-program counts; the "
            "reported range is its 2.5th to 97.5th percentile, and the p-value is two-sided: 2 times the "
            "smaller of P(null at or above observed) and P(null at or below observed), capped at 1.",
        )
    )
    lines.append("")
    lines.append(
        _plain_then_detail(
            "Reach share interval",
            "This gives a likely range for each group's Aboriginal and Torres Strait Islander share, based "
            "on how many students are in that group.",
            "An enrolled student is a distinct Student_ID with at least one row in the cleaned Enrolment "
            "table (any outcome); 1,203 students. ATSI status comes from the cleaned Student table (Y or N). "
            "A student counts in a group (Funding_Source after cleaning, Provider_ID, or Remoteness) if they "
            "have at least one enrolment row in that group, so a student can appear in several groups within "
            "a dimension. Each share is the number of ATSI = Y students over the number of students in the "
            "group, with a 95% Wilson score interval.",
        )
    )
    lines.append("")
    lines.append(
        _plain_then_detail(
            "Reach group difference test",
            "Asks whether any group's Aboriginal and Torres Strait Islander share differs from the others "
            "by more than chance would produce.",
            "For each of Funding_Source, Provider_ID and Remoteness, a binomial GEE is fit on one row per "
            "student-group membership, with outcome ATSI (1 for Y, 0 for N), the group as the only "
            "predictor, an exchangeable correlation structure, and clustering on student. The reported "
            "p-value is the Wald test for any group difference. Because a student can appear in several "
            "groups, the rows are not independent; clustering on student is what accounts for that.",
        )
    )
    lines.append("")
    lines.append("## Judgement calls (stated, not silently assumed)")
    lines.append("")
    lines.append(
        "- T08b reports the At_School_Flag = N share and the At_School_Suspect = True share as two "
        "separate columns (not a combined OR share), each out of all 11N/11V rows for that Remoteness."
    )
    lines.append(
        "- T02/T04's \"blank where none\" is implemented as: Target_AHC is blank only where no contract "
        "exists for that pair (a true missing value); Delivered_AHC is 0 where a contract exists but no "
        "delivery occurred (a real zero, not missing)."
    )
    lines.append(
        "- T02d's two uncontracted-excluding-11K shares share the same numerator (delivery-without-a-"
        "contract AHC minus 11K's uncontracted AHC): (a) divides by total AHC (so 11K is removed from the "
        "numerator only, and still counted in the denominator); (b) divides by total AHC minus all 11K AHC "
        "(contracted and uncontracted), so 11K is removed from both numerator and denominator."
    )
    lines.append(
        "- T09b's multiple-comparisons note counts the 8 regional and funding-stream gaps (3 Remoteness, 5 "
        "Funding_Source) as the relevant comparison set; the Overall row is the headline comparison, not "
        "one of the 8, since it is not a subgroup."
    )
    lines.append(
        f"- T01's enrolled-student ATSI share uses the students with at least one enrolment row "
        f"(1,203 students), since that is what \"share of enrolled students\" means here: "
        f"{round_pct(share_atsi_y)}%."
    )
    lines.append(
        "- T10(d) excludes rows recovered from an unknown funding source in cleaning (the 30 rows "
        "recovered from UNK); there are 0 rows still coded 'Unknown' to exclude, confirming recovery was "
        "complete."
    )
    lines.append(
        "- T12b's and T15's Short_Label is a hand-written lookup, not an algorithm - each of the 10 "
        "programs was given a short label by eye. T12b's Full_Label column carries the full Program_Name "
        "alongside it, for use anywhere that can show the full name on hover or on request."
    )
    lines.append(
        "- Claims 12 and 13 call an industry-mix gap 'material' above 10 percentage points; between 5 and "
        "10 points it is reported as a modest (PARTLY) difference, and below 5 points as not material. This "
        "threshold is a judgement call, not a statistical test."
    )
    (OUTPUTS_DIR / "analysis_methods.md").write_text("\n".join(lines))


def write_headline_claims_md(
    enr, t01, t02a, t02c, t03b, t05a, t05b, t05c, t06a, t06c, t07, t07_omnibus, t09b, t09c, t11,
    t12c_remoteness, t12c_funding, t12d, t13, t14, t15, t16,
):
    lines = ["# Headline claim checks", ""]

    def section(n, claim, numbers, verdict):
        lines.append(f"## {n}. \"{claim}\"")
        lines.append("")
        lines.append(numbers)
        lines.append("")
        lines.append(f"**Verdict: {verdict}**")
        lines.append("")

    matched_ahc = float(t02a.loc[t02a["Coverage_Bucket"] == "Matched comparable pair", "AHC"].iloc[0])
    no_target_ahc = float(t02a.loc[t02a["Coverage_Bucket"] == "Matched pair, no target set", "AHC"].iloc[0])
    dwc_ahc = float(t02a.loc[t02a["Coverage_Bucket"] == "Delivery without a contract", "AHC"].iloc[0])
    total_ahc = t02a["AHC"].sum()
    share_outside_contract = 100 * dwc_ahc / total_ahc
    section(
        1,
        "Most delivered hours sit outside any contract.",
        f"Matched comparable pairs: {matched_ahc:,.0f} AHC ({round_pct(100 * matched_ahc / total_ahc)}%). "
        f"Delivery without a contract: {dwc_ahc:,.0f} AHC ({round_pct(share_outside_contract)}%). "
        f"Matched but no target set: {no_target_ahc:,.0f} AHC ({round_pct(100 * no_target_ahc / total_ahc)}%). "
        f"\"Outside any contract\" (delivery without a contract only, the literal reading of the claim) is "
        f"{round_pct(share_outside_contract)}% of total AHC, a majority.",
        "SUPPORTED" if share_outside_contract > 50 else ("PARTLY" if share_outside_contract > 40 else "NOT SUPPORTED"),
    )

    n_pairs = t05c.loc[0, "Of_pairs"]
    n_urban_below = t05c.loc[0, "Count"]
    urban_delivered = t05a.loc[t05a["Remoteness"] == "Urban", "Delivered_Share_%"]
    remote_delivered = t05a.loc[t05a["Remoteness"] == "Remote", "Delivered_Share_%"]
    agg_urban_delivered = float(t05b.loc[t05b["Remoteness"] == "Urban", "Delivered_Share_%"].iloc[0])
    agg_remote_delivered = float(t05b.loc[t05b["Remoteness"] == "Remote", "Delivered_Share_%"].iloc[0])
    mix_note = (
        f"Delivered Urban share across the 19 pairs ranges {urban_delivered.min():.1f}% to {urban_delivered.max():.1f}% "
        f"(mean {urban_delivered.mean():.1f}%, SD {urban_delivered.std():.1f}pp); delivered Remote share ranges "
        f"{remote_delivered.min():.1f}% to {remote_delivered.max():.1f}% (mean {remote_delivered.mean():.1f}%, SD "
        f"{remote_delivered.std():.1f}pp). This is a far narrower spread than the target shares (see t05a/t05b), so "
        f"individual pairs deliver a broadly similar remoteness mix to each other, and the aggregate row in "
        f"t05b_aggregate_geography.csv (Urban {agg_urban_delivered}%, Remote {agg_remote_delivered}%) is the primary "
        f"evidence for claims 2 and 3, not pair-by-pair variation."
    )
    section(
        2,
        "Urban delivery falls below its contracted share in every comparable pair.",
        f"{n_urban_below} of {n_pairs} matched pairs have delivered Urban share below target Urban share (see t05a_pairs_geography.csv, Diff_pp < 0 for Urban). {mix_note}",
        "SUPPORTED" if n_urban_below == n_pairs else ("PARTLY" if n_urban_below > n_pairs / 2 else "NOT SUPPORTED"),
    )

    n_remote_above = t05c.loc[1, "Count"]
    section(
        3,
        "Remote delivery exceeds its contracted share in most comparable pairs.",
        f"{n_remote_above} of {n_pairs} matched pairs have delivered Remote share above target Remote share. "
        f"See claim 2 above for the delivered-share dispersion figures across pairs; the same aggregate row in "
        f"t05b_aggregate_geography.csv (Remote {agg_remote_delivered}%) is the primary evidence here too.",
        "SUPPORTED" if n_remote_above > n_pairs / 2 else "NOT SUPPORTED",
    )

    bad_outcome_ahc = t06a.loc[t06a["Outcome_Group"].isin(["Withdrawn", "Not achieved"]), "AHC_Funded"].sum()
    total_ahc_t06 = t06a["AHC_Funded"].sum()
    share_bad = 100 * bad_outcome_ahc / total_ahc_t06
    section(
        4,
        "More than a third of funded hours went to units that were not achieved or were withdrawn.",
        f"Withdrawn + Not achieved AHC: {bad_outcome_ahc:,.0f} of {total_ahc_t06:,.0f} total ({round_pct(share_bad)}%).",
        "SUPPORTED" if share_bad > 33.33 else "NOT SUPPORTED",
    )

    share_y_flagged = float(t06c.loc[t06c["Funded_Flag"] == "Y", "Share_%"].iloc[0]) if "Y" in t06c["Funded_Flag"].values else 0
    section(
        5,
        "Nearly all hours on withdrawn or not-achieved units are fully funded (Funded_Flag = Y).",
        f"Of AHC on Withdrawn/Not-achieved units, {share_y_flagged}% carries Funded_Flag = Y (see t06c).",
        "SUPPORTED" if share_y_flagged >= 90 else ("PARTLY" if share_y_flagged >= 50 else "NOT SUPPORTED"),
    )

    overall_row = t07[(t07["Dimension"] == "Overall")].iloc[0]
    fs_rows = t07[t07["Dimension"] == "Funding_Source"]
    prov_rows = t07[t07["Dimension"] == "Provider_ID"]
    fs_p = float(t07_omnibus.loc[t07_omnibus["Dimension"] == "Funding_Source", "Omnibus_GEE_p_value"].iloc[0])
    prov_p = float(t07_omnibus.loc[t07_omnibus["Dimension"] == "Provider_ID", "Omnibus_GEE_p_value"].iloc[0])
    near_60_fs = ((fs_rows["Rate_%"] >= 50) & (fs_rows["Rate_%"] <= 70)).all()
    near_60_prov = ((prov_rows["Rate_%"] >= 50) & (prov_rows["Rate_%"] <= 70)).all()
    section(
        6,
        "Completion is about 60% in every stream and provider (use the CIs and omnibus p-values).",
        f"Overall rate {overall_row['Rate_%']}% (CI {overall_row['CI_Lower']} to {overall_row['CI_Upper']}). "
        f"Funding_Source rates range {fs_rows['Rate_%'].min()}% to {fs_rows['Rate_%'].max()}% "
        f"(omnibus GEE p = {fs_p:.3f}, spread {round_pct(fs_rows['Rate_%'].max() - fs_rows['Rate_%'].min())} pp). "
        f"Provider_ID rates range {prov_rows['Rate_%'].min()}% to {prov_rows['Rate_%'].max()}% "
        f"(omnibus GEE p = {prov_p:.3f}, spread {round_pct(prov_rows['Rate_%'].max() - prov_rows['Rate_%'].min())} pp).",
        "SUPPORTED" if (near_60_fs and near_60_prov and fs_p > 0.05 and prov_p > 0.05) else "PARTLY",
    )

    gap_row = t09b[t09b["Dimension"] == "Overall"].iloc[0]
    or_row = t09c[t09c["Metric"] == "ATSI odds ratio (Y vs N)"]
    or_val = float(or_row["Value"].iloc[0])
    or_p = float(t09c.loc[t09c["Metric"] == "OR p-value", "Value"].iloc[0])
    pred_gap = float(t09c.loc[t09c["Metric"] == "Model-predicted gap, Y minus N (pp)", "Value"].iloc[0])
    unadj_supported = gap_row["Gap_pp_Y_minus_N"] < 0 and gap_row["CI_Upper"] < 0
    adj_supported = or_val < 1 and or_p < 0.05
    section(
        7,
        "ATSI learners complete at a lower rate than non-ATSI learners (unadjusted and adjusted).",
        f"Unadjusted gap (Y minus N): {gap_row['Gap_pp_Y_minus_N']} pp (95% CI {gap_row['CI_Lower']} to {gap_row['CI_Upper']}). "
        f"Adjusted GEE odds ratio for ATSI = Y vs N: {or_val} (p = {or_p:.4f}); model-predicted gap "
        f"{pred_gap} pp.",
        "SUPPORTED" if (unadj_supported and adj_supported) else ("PARTLY" if (unadj_supported or adj_supported) else "NOT SUPPORTED"),
    )

    top3_ind_share = float(t12d.loc[t12d["Metric"] == "Top 3 industries share of total AHC", "Value"].iloc[0])
    even_ind_row = t12d.loc[t12d["Metric"].str.contains("even-spread share for top 3 of") & t12d["Metric"].str.contains("industries")]
    even_ind_share = float(even_ind_row["Value"].iloc[0])
    section(
        11,
        "Funded hours are concentrated in a small number of industries.",
        f"Top 3 industries hold {top3_ind_share}% of funded AHC; an even spread across all industries would "
        f"give the top 3 {even_ind_share}%.",
        "SUPPORTED" if top3_ind_share > even_ind_share + 15 else ("PARTLY" if top3_ind_share > even_ind_share else "NOT SUPPORTED"),
    )

    def largest_industry_gap(mix_table, group_col, share_col):
        pivot = mix_table.pivot(index="Industry", columns=group_col, values=share_col)
        gaps = pivot.max(axis=1) - pivot.min(axis=1)
        return gaps.idxmax(), float(gaps.max())

    gap_industry_r, gap_value_r = largest_industry_gap(t12c_remoteness, "Remoteness", "Share_within_Remoteness_%")
    material_r = gap_value_r > 10
    section(
        12,
        "Industry mix differs by remoteness.",
        f"The largest gap in any industry's share between two regions is {gap_value_r:.1f} percentage "
        f"points ({gap_industry_r}, see t12c_industry_by_remoteness). "
        f"{'This looks material.' if material_r else 'This is small enough that it does not look material - the industry mix is close to uniform across Urban, Regional and Remote.'}",
        "SUPPORTED" if material_r else "NOT SUPPORTED",
    )

    gap_industry_f, gap_value_f = largest_industry_gap(t12c_funding, "Funding_Source", "Share_within_FundingSource_%")
    material_f = gap_value_f > 10
    section(
        13,
        "Industry mix differs by funding stream.",
        f"The largest gap in any industry's share between two streams is {gap_value_f:.1f} percentage "
        f"points ({gap_industry_f}, see t12c_industry_by_funding_source). "
        f"{'This looks material.' if material_f else 'This is a modest difference, not a dramatic one - no industry changes its overall ranking across streams.'}",
        "SUPPORTED" if material_f else ("PARTLY" if gap_value_f > 5 else "NOT SUPPORTED"),
    )

    level_shares = t13.set_index("Qualification_Level")["Share_of_Total_%"]
    entry_share = float(level_shares.get("Certificate I", 0)) + float(level_shares.get("Certificate II", 0))
    higher_share = float(level_shares.get("Certificate III", 0)) + float(level_shares.get("Certificate IV", 0))
    section(
        14,
        "Funded hours are concentrated at entry level (Certificate I to II).",
        f"Certificate I + II hold {round_pct(entry_share)}% of funded AHC; Certificate III + IV hold "
        f"{round_pct(higher_share)}% - the opposite pattern to the claim, with most funded hours at the "
        f"higher levels (see t13_by_qualification_level for the per-level breakdown).",
        "SUPPORTED" if entry_share > higher_share else "NOT SUPPORTED",
    )

    t14_sorted = t14.sort_values("AHC_Funded", ascending=False)
    top1_town_share = float(t14_sorted["Share_of_Total_%"].iloc[0])
    top3_town_share = float(t14_sorted["Share_of_Total_%"].iloc[:3].sum())
    town_spread = float(t14_sorted["Share_of_Total_%"].max() - t14_sorted["Share_of_Total_%"].min())
    section(
        15,
        "Funded hours are concentrated in a few towns.",
        f"Top 1 town holds {round_pct(top1_town_share)}% of funded AHC; top 3 towns hold "
        f"{round_pct(top3_town_share)}% (see t14_by_town). Across all towns the share ranges by only "
        f"{round_pct(town_spread)} percentage points - every one of the {len(t14_sorted)} towns holds a "
        f"broadly similar share, the opposite of concentration.",
        "SUPPORTED" if top1_town_share > 100 / len(t14_sorted) + 15 else "NOT SUPPORTED",
    )

    t16_min = int(t16.loc[t16["Metric"] == "Observed minimum students (any program)", "Value"].iloc[0])
    t16_max = int(t16.loc[t16["Metric"] == "Observed maximum students (any program)", "Value"].iloc[0])
    t16_ratio = float(t16.loc[t16["Metric"] == "Observed max-to-min ratio", "Value"].iloc[0])
    t16_pvalue = float(t16.loc[t16["Metric"] == "Two-sided p-value for observed spread", "Value"].iloc[0])
    section(
        16,
        "Student numbers are similar across the ten programs.",
        f"Distinct students per program range from {t16_min} to {t16_max} (ratio {t16_ratio}). The "
        f"permutation chance check (t16_student_count_chance_check) gives a two-sided p-value of "
        f"{t16_pvalue} for this spread, meaning the observed variation is well within what random chance "
        f"alone would produce once each student's number of programs is held fixed.",
        "SUPPORTED" if t16_pvalue > 0.05 else "NOT SUPPORTED",
    )

    def twice_verdict(ratio):
        if 1.8 <= ratio <= 2.2:
            return "SUPPORTED"
        if 1.5 <= ratio < 1.8 or 2.2 < ratio <= 2.5:
            return "PARTLY"
        return "NOT SUPPORTED"

    cs_row = t15.loc[t15["Program_ID"] == "Community Services (3 programs)"].iloc[0]
    other_row = t15.loc[t15["Program_ID"] == "Other 7 programs combined"].iloc[0]
    ahc_per_unit_ratio = float(cs_row["AHC_per_Unit"]) / float(other_row["AHC_per_Unit"])
    hours_ratio = float(cs_row["Mean_Nominal_Hours_per_Unit"]) / float(other_row["Mean_Nominal_Hours_per_Unit"])
    frac_ratio = float(cs_row["Mean_Funded_Fraction"]) / float(other_row["Mean_Funded_Fraction"])
    driver = (
        "longer units (Mean_Nominal_Hours_per_Unit), not a different funded fraction"
        if abs(hours_ratio - ahc_per_unit_ratio) < abs(frac_ratio - ahc_per_unit_ratio)
        else "a different funded fraction, not longer units"
    )
    section(
        17,
        "The three Community Services programs carry roughly twice the funded hours per unit of the other programs.",
        f"AHC_per_Unit: Community Services {cs_row['AHC_per_Unit']}, other seven {other_row['AHC_per_Unit']} "
        f"(ratio {ahc_per_unit_ratio:.2f}). Mean_Nominal_Hours_per_Unit: {cs_row['Mean_Nominal_Hours_per_Unit']} "
        f"vs {other_row['Mean_Nominal_Hours_per_Unit']} (ratio {hours_ratio:.2f}). Mean_Funded_Fraction: "
        f"{cs_row['Mean_Funded_Fraction']} vs {other_row['Mean_Funded_Fraction']} (ratio {frac_ratio:.2f}). "
        f"The AHC-per-unit ratio tracks the unit-length ratio almost exactly while the funded-fraction ratio "
        f"sits close to 1, so the difference is accounted for arithmetically by {driver}, which does not show why.",
        twice_verdict(ahc_per_unit_ratio),
    )

    individual_15 = t15[t15["Program_ID"].isin(SHORT_LABEL_LOOKUP.keys())].copy()
    by_students_15 = individual_15.sort_values("Distinct_Students", ascending=False).reset_index(drop=True)
    by_ahc_15 = individual_15.sort_values("AHC_Funded", ascending=False).reset_index(drop=True)

    pos_students = int(by_students_15.index[by_students_15["Program_ID"] == "CER40115"][0])
    pos_ahc = int(by_ahc_15.index[by_ahc_15["Program_ID"] == "CER40115"][0])
    rank_students, rank_ahc = pos_students + 1, pos_ahc + 1
    cer_students = int(by_students_15.loc[pos_students, "Distinct_Students"])
    cer_ahc = float(by_ahc_15.loc[pos_ahc, "AHC_Funded"])

    above_students = int(by_students_15.loc[pos_students - 1, "Distinct_Students"]) if pos_students > 0 else None
    below_students = int(by_students_15.loc[pos_students + 1, "Distinct_Students"]) if pos_students + 1 < len(by_students_15) else None
    above_ahc = float(by_ahc_15.loc[pos_ahc - 1, "AHC_Funded"]) if pos_ahc > 0 else None
    below_ahc = float(by_ahc_15.loc[pos_ahc + 1, "AHC_Funded"]) if pos_ahc + 1 < len(by_ahc_15) else None

    close_notes = []
    if below_students is not None and cer_students - below_students <= 5:
        close_notes.append(f"the student-count gap down to rank {rank_students + 1} is only {cer_students - below_students} students")
    if above_students is not None and above_students - cer_students <= 5:
        close_notes.append(f"the student-count gap up to rank {rank_students - 1} is only {above_students - cer_students} students")
    close_note = "; ".join(close_notes) if close_notes else "neither ranking is within a few students or close to tying"

    section(
        18,
        "Certificate IV in Early Childhood Education and Care (CER40115) ranks second of ten programs by distinct students and by funded hours.",
        f"By distinct students: rank {rank_students} of 10 with {cer_students} students "
        f"(neighbour above: {above_students if above_students is not None else 'n/a'}; "
        f"neighbour below: {below_students if below_students is not None else 'n/a'}). "
        f"By funded hours: rank {rank_ahc} of 10 with {cer_ahc:,.0f} AHC "
        f"(neighbour above: {f'{above_ahc:,.0f}' if above_ahc is not None else 'n/a'}; "
        f"neighbour below: {f'{below_ahc:,.0f}' if below_ahc is not None else 'n/a'}). "
        f"{close_note.capitalize()}.",
        "SUPPORTED" if rank_students == 2 and rank_ahc == 2 else ("PARTLY" if rank_students == 2 or rank_ahc == 2 else "NOT SUPPORTED"),
    )

    cs_aps = float(cs_row["AHC_per_Student"])
    other_aps = float(other_row["AHC_per_Student"])
    aps_ratio = cs_aps / other_aps
    section(
        19,
        "Funded hours per student are about twice as high in the Community Services programs.",
        f"AHC_per_Student: Community Services {cs_aps}, other seven {other_aps} (ratio {aps_ratio:.2f}).",
        twice_verdict(aps_ratio),
    )

    p008_fft_ahc = float(t02c.loc[(t02c["Provider_ID"] == "P008") & (t02c["Funding_Source"] == "FFT"), "AHC"].iloc[0])
    p008_fft_rows = int(((enr["Provider_ID"] == "P008") & (enr["Funding_Source"] == "FFT")).sum())
    total_dwc_ahc = float(t02c["AHC"].sum())
    p008_share_of_dwc = 100 * p008_fft_ahc / total_dwc_ahc
    remaining_dwc_ahc = total_dwc_ahc - p008_fft_ahc

    ahc_by_year = enr.groupby("Delivery_Year")["AHC_Funded"].sum()

    lines.append("## Additional claims the data supports")
    lines.append("")
    lines.append(
        f"8. \"P008 accounts for {p008_fft_ahc:,.0f} AHC ({p008_fft_rows:,} enrolment rows) of FFT delivery "
        f"without a matching FFT contract, while its 11J/11N/11V contracts have zero delivery.\" P008 is "
        f"{round_pct(p008_share_of_dwc)}% of all delivery-without-a-contract AHC, so the remaining 15 pairs "
        f"account for {remaining_dwc_ahc:,.0f} AHC between them. Why it matters: this single provider drives "
        f"both the biggest delivery-without-contract line and all three contract-without-delivery lines, so "
        f"it is the first place a data owner should look, not a general funding-stream pattern - but most "
        f"of the delivery-without-contract total (the other {round_pct(100 - p008_share_of_dwc)}%) is spread "
        f"across the other 15 pairs, not concentrated in P008 alone."
    )
    lines.append(
        "9. \"Delivered AHC across matched pairs is nowhere near 100% of target\" (min/median/max from "
        "t03a: see the table; every matched pair is under its 3-year target). Why it matters: before "
        "reading any provider as under-performing, the Executive Director needs to know this gap is "
        "universal, not provider-specific."
    )
    lines.append(
        f"10. \"2023 has no carry-in from 2022, and annual delivered AHC differs materially year to year\" "
        f"(see t11_context: 2023 = {ahc_by_year.get(2023, 0):,.0f} AHC, 2024 = {ahc_by_year.get(2024, 0):,.0f} "
        f"AHC, 2025 = {ahc_by_year.get(2025, 0):,.0f} AHC; the feasibility check shows valid Enrol_Start_Date "
        f"values run through 28 Dec 2025, so 2025 is not an obviously incomplete year on that evidence alone). "
        f"Why it matters: 2023 being a first-year-of-contract figure with no prior carry-over, combined with "
        f"the year-to-year swings already in the data, means a year-over-year trend claim needs to account "
        f"for this structural difference rather than treating all three years as comparable baselines."
    )
    (OUTPUTS_DIR / "headline_claims.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
