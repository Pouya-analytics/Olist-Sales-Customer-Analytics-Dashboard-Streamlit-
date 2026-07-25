Olist Sales & Customer Analytics Dashboard (Streamlit)

I built this because analysis that lives in a notebook is only useful to other analysts. A client needs something they can actually open, click through, and filter themselves. This is that — a live, deployable dashboard, not a demo that only runs on my machine.

What it does
KPI cards: revenue, orders, customers, AOV — all recalculate live as filters change
Revenue trend by month
Revenue by category and by state
Payment method breakdown
Full RFM segmentation — same methodology as Project 1, reimplemented in pandas so it runs without a SQL connection on every filter change

Sidebar filters: date range, customer state, product category. Every chart responds to all three.

It actually works

Tested with Streamlit's official AppTest framework — not just "the server started." Six tests, all passing:

App runs without exceptions
All four KPI metrics render correctly
Filtering to one state correctly drops revenue from R$1,400,914 to R$49,539 — proves the filters are wired to the data, not decorative
Empty filter selection shows a warning instead of crashing
One bug caught before shipping

This dataset has a 97% one-time-buyer rate. A naive pandas qcut() call on purchase frequency throws a "bin edges must be unique" error when 97% of values are identical. Fixed by ranking frequency first before binning. Small detail, only caught by running against real data.

Dataset

Same synthetic Olist dataset as Project 1 — calibrated to real published statistics, disclosed explicitly. Generator is included so the repo runs end-to-end without any external dependencies.

How to run it
bash
pip install -r requirements.txt
python scripts/generate_data.py
streamlit run app.py
python -m pytest test_app.py -v
Stack

Streamlit · Plotly · pandas · SQLite · pytest (AppTest)
