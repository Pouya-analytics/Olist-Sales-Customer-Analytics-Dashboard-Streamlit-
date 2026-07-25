# Olist Sales & Customer Analytics Dashboard

An interactive Streamlit dashboard for the Olist-style e-commerce
dataset built in [Project 1](https://github.com/) of this portfolio —
date-range and category/state filters, revenue trends, geographic
breakdown, payment mix, and full RFM customer segmentation, all
client-side filterable in real time.

## Why this project

A SQL query that produces correct numbers is one deliverable. A tool a
non-technical client can actually click through, filter, and explore
themselves is a different one — and it's the deliverable freelance
clients usually want, because they don't read `.sql` files. This
project turns Project 1's static SQL analysis into something
interactive and shareable via a single link.

## Live demo

**[Add your Streamlit Cloud URL here after deploying — see instructions below]**

## What's in it

- **KPI cards**: total revenue, order count, unique customers, average
  order value — all recalculated live as filters change
- **Revenue trend** (monthly line chart)
- **Revenue by category** (top 8, horizontal bar)
- **Revenue by state** and **payment method mix**
- **RFM customer segmentation** — the exact same methodology as
  Project 1's SQL analysis (Recency/Frequency/Monetary quintile
  scoring → 5 segments), reimplemented in pandas so the dashboard
  doesn't need a live SQL connection per interaction
- **Sidebar filters**: date range, customer state, product category —
  all of the above recalculates from these filters in real time

## Proof this actually works

This isn't just "the server booted." Every claim below is reproducible
by running `python -m pytest test_app.py -v`:

```
test_app_runs_without_exceptions      PASSED
test_kpi_metrics_render               PASSED
test_sidebar_filters_present          PASSED
test_state_filter_changes_kpis        PASSED
test_category_filter_changes_kpis     PASSED
test_empty_filter_shows_warning_not_crash   PASSED

======================= 6 passed in 3.40s =======================
```

These tests use Streamlit's own `AppTest` framework (`streamlit.testing.v1`)
— the official way to verify a Streamlit script runs cleanly, as opposed
to just hitting the HTTP health endpoint, which only proves the server
process started.

The filter test specifically proves interactivity isn't cosmetic: in a
real run, narrowing the state filter to a single state correctly
dropped total revenue from **R$1,400,914** (all states) to **R$49,539**
(one state, 339 orders) — the filters are actually wired into the data,
not decorative widgets sitting next to a static chart.

## About the data

Same synthetic, Olist-calibrated dataset as Project 1 in this
portfolio. See that project's README for the full disclosure on why
it's synthetic (no Kaggle API access in the dev environment) and how
it's calibrated to match the real Olist Brazilian E-Commerce dataset's
published statistics. `scripts/generate_data.py` here is the identical
generator — this repo is self-contained and doesn't depend on Project 1
being present.

## How to run it locally

```bash
pip install -r requirements.txt
python scripts/generate_data.py   # builds data/ecommerce.db (skip if already present)
streamlit run app.py
```

Opens at `http://localhost:8501`.

## How to run the tests

```bash
python -m pytest test_app.py -v
```

## How to deploy it (Streamlit Community Cloud — free)

1. Push this repo to GitHub (public or private).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in
   with your GitHub account.
3. Click **"Create app"** in your workspace.
4. Fill in your repository, branch, and the path to `app.py` (or paste
   the GitHub URL directly to `app.py`).
5. Optionally pick a custom subdomain (otherwise you get an
   auto-generated one based on your repo name).
6. Click **Deploy**. Most apps go live within a few minutes — Community
   Cloud handles all the containerization.

Once deployed, pushing changes to `app.py` on GitHub updates the live
app automatically — no redeploy step needed.

## Repo structure

```
.
├── app.py                    # the dashboard itself
├── test_app.py                # AppTest-based test suite (6 tests)
├── scripts/
│   └── generate_data.py       # synthetic data generator (same as Project 1)
├── data/
│   └── ecommerce.db           # SQLite DB (generated, included for immediate use)
├── .streamlit/
│   └── config.toml            # theme config
└── requirements.txt
```

## What I'd add with more time

- A page for the cohort retention analysis from Project 1 (currently
  only RFM is reproduced here — cohort retention needs a heatmap
  component that's a bit more involved in Plotly)
- Drill-down: clicking a segment in the RFM chart filters the rest of
  the dashboard to that segment
- Caching tuned with `st.cache_data(ttl=...)` for a version connected
  to a live, regularly-updating database rather than a static file

## Tech stack

Streamlit · Plotly · pandas · SQLite · pytest (via `streamlit.testing.v1`)
