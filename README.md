# NT VET Performance app

A Streamlit app presenting the NT VET Performance analysis as a readable
briefing document, built only from aggregate tables, never from
student-level data. The app is laptop-only: one fixed desktop layout,
not a responsive narrow/phone variant.

## How to run

The app must be run from the project root (the directory containing this
README and `.streamlit/`), not from inside `app/`. Streamlit only picks
up `.streamlit/config.toml` (the light theme) when it is launched from
the directory that contains it, and `app/Home.py` imports `lib.*` on the
assumption that `app/` is the script's own directory, not the current
working directory.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/Home.py
```

Run the tests with:

```bash
pytest tests/
```

## How to deploy

The app reads only from `app/data/`, which is a plain directory of CSV
and Markdown files checked into the repo (it is not covered by the
`/data/` entry in `.gitignore`, which only excludes the top-level
`data/raw/` and `data/clean/` folders containing student-level
information). This means `app/` is self-contained and deployable as-is:

- **Streamlit Community Cloud**: point it at this repo, set the main
  file path to `app/Home.py`, and it will install `requirements.txt`
  automatically.
- **Any other host that runs a Streamlit app** (a container, a VM, an
  internal PaaS): install `requirements.txt` into the environment and
  run `streamlit run app/Home.py --server.port <port>`.

Nothing in `app/` reads from `data/raw/` or `data/clean/`, and the test
suite (`tests/test_data_privacy.py`) fails the build if that ever
changes, so it is safe to deploy `app/` on its own without the rest of
the project's raw or cleaned data.

## What is in app/assets

`app/assets/ntg_logo.svg`: the Northern Territory Government logo shown
at the top of the Briefing page, embedded inline (not loaded from a
URL). The only other file the app reads at runtime is `app/data/`.

## What is in app/data

Every file in `app/data/` is a copy of an aggregate output already
produced by the cleaning and analysis scripts (`scripts/clean_data.py`
and `scripts/analysis_tables.py`). Nothing here is read directly from
`data/raw/` or `data/clean/`, and no file contains a USI, a date of
birth, a Student_ID, or any other row-level identifier.

- `t01_kpis.csv` through `t21_data_quality_figures.csv`: every analysis
  table, copied unchanged from `outputs/analysis_tables/`.
- `cleaning_log.csv`: the rule-by-rule cleaning log, copied from
  `outputs/cleaning_log.csv`.
- `data_quality_summary.md`: the plain-English cleaning summary, copied
  from `outputs/data_quality_summary.md`.
- `analysis_methods.md`: the analysis definitions and statistical
  methodology notes, copied from `outputs/analysis_methods.md`.

**Never copy a file into `app/data/` by hand.** The only sanctioned way
to refresh it is:

```bash
python3 scripts/sync_app_data.py
```

This copies exactly the explicit whitelist defined in that script (every
file listed above, nothing else) from `outputs/`, refuses to copy any
CSV with a USI/DOB/Student_ID-like column, and prints what was added,
updated, or already up to date. `tests/test_data_sync.py` fails the
build if `app/data/` ever drifts from that whitelist (a stale file, a
missing one, or an extra one that didn't come from the sync script).

## App structure

- `app/Home.py`: the Briefing page - executive summary, the eight chart
  sections (Coverage, Delivered vs target, Geography, What is being
  delivered, Funding vs outcome, Completion, Equity, Reach), and the
  "So what" action cards.
- `app/pages/2_Method_and_data_quality.py`: renders the data quality
  summary, analysis methods, and cleaning log.
- `app/lib/data_access.py`: cached CSV/text loaders, one function per
  table, all reading from `app/data/` only, plus content-based `find_*`
  functions for chart code that must not assume a filename.
- `app/lib/theme.py`: the palette, the shared `nt_vet` Plotly template,
  page layout, the NTG logo helper, and the `chart_card` rendering
  helper.
- `app/lib/privacy.py`: the single definition of "forbidden,
  identifier-like column name", shared by the data-privacy test and the
  data-sync script so the two can never drift apart.
- `app/lib/titles.py`: one function per headline title. Every number in
  a title is computed fresh from the source CSVs; if the data no longer
  supports a title's claim (for example the completion rate drifting
  well away from 60%, or a p-value crossing 0.05), the function raises
  `TitleAssumptionError` instead of returning stale or misleading
  wording.
- `app/lib/chart_*.py`: one module per chart section (Coverage,
  Delivered vs target, Geography, Programs, Funding vs outcome,
  Completion, Equity, Reach) - each builds its own figure, caption and
  expander table from tables located by their columns/content rather
  than by filename.
- `app/lib/so_what.py`: the executive summary bullets and the four
  "So what" action cards.
- `scripts/sync_app_data.py`: the only sanctioned way to populate
  `app/data/` (see "What is in app/data" above).

Chart visual review is manual, in the browser - see CLAUDE.md for the
working agreement. There is no screenshot or pixel-measurement tooling
in this repo; the test suite is data-integrity only.
