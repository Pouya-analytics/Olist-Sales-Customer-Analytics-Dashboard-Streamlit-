"""
app.py
-------
Interactive sales & customer analytics dashboard for the Olist-calibrated
e-commerce dataset (same synthetic database built in Project 1 of this
portfolio -- see that project's README for how it was generated and why
it's synthetic rather than a raw download).

Run locally with:  streamlit run app.py
Deployed live at:  <add your Streamlit Cloud URL here after deploying>
"""
import os
import sqlite3
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ecommerce.db")

st.set_page_config(
    page_title="Olist Sales Analytics",
    page_icon="📦",
    layout="wide",
)


# ---------------------------------------------------------------------
# DATA LOADING (cached so filters don't re-hit the DB on every interaction)
# ---------------------------------------------------------------------
@st.cache_data
def load_orders():
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT
            o.order_id,
            o.customer_id,
            o.order_status,
            o.order_purchase_timestamp,
            c.customer_state,
            oi.product_category,
            oi.price,
            oi.freight_value,
            p.payment_type
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        LEFT JOIN payments p ON o.order_id = p.order_id
        WHERE o.order_status = 'delivered'
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"])
    df["order_date"] = df["order_purchase_timestamp"].dt.date
    df["order_month"] = df["order_purchase_timestamp"].dt.to_period("M").astype(str)
    df["total_value"] = df["price"] + df["freight_value"]
    return df


@st.cache_data
def load_rfm():
    """
    Re-implements the same RFM segmentation logic as Project 1's
    sql/02_rfm_segmentation.sql, in pandas this time, so the dashboard
    doesn't need a live SQL connection per filter interaction. The
    segment definitions are IDENTICAL to Project 1 -- this is the same
    analysis, just rendered differently.
    """
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT
            o.customer_id,
            o.order_id,
            DATE(o.order_purchase_timestamp) AS order_date,
            (oi.price + oi.freight_value) AS item_total
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    order_value = df.groupby(["customer_id", "order_id", "order_date"])["item_total"].sum().reset_index()
    order_value.columns = ["customer_id", "order_id", "order_date", "order_total"]

    max_date = pd.to_datetime(order_value["order_date"]).max()
    customer_agg = order_value.groupby("customer_id").agg(
        last_order=("order_date", "max"),
        frequency=("order_id", "count"),
        monetary=("order_total", "sum"),
    ).reset_index()
    customer_agg["recency_days"] = (max_date - pd.to_datetime(customer_agg["last_order"])).dt.days

    customer_agg["r_score"] = 6 - pd.qcut(customer_agg["recency_days"], 5, labels=False, duplicates="drop") - 1
    customer_agg["f_score"] = pd.qcut(customer_agg["frequency"].rank(method="first"), 5, labels=False, duplicates="drop") + 1
    customer_agg["m_score"] = pd.qcut(customer_agg["monetary"], 5, labels=False, duplicates="drop") + 1

    def segment(row):
        if row.r_score >= 4 and row.f_score >= 4 and row.m_score >= 4:
            return "Champion"
        elif row.r_score >= 4 and row.f_score <= 2:
            return "New / Promising"
        elif row.r_score <= 2 and row.f_score >= 4 and row.m_score >= 4:
            return "At Risk (high value)"
        elif row.r_score <= 2 and row.f_score <= 2:
            return "Lost"
        else:
            return "Regular"

    customer_agg["segment"] = customer_agg.apply(segment, axis=1)
    return customer_agg


orders_df = load_orders()
rfm_df = load_rfm()

# ---------------------------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------------------------
st.sidebar.title("📦 Filters")

min_date, max_date = orders_df["order_date"].min(), orders_df["order_date"].max()
date_range = st.sidebar.date_input(
    "Order date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

all_states = sorted(orders_df["customer_state"].unique())
selected_states = st.sidebar.multiselect("Customer state", all_states, default=all_states)

all_categories = sorted(orders_df["product_category"].dropna().unique())
selected_categories = st.sidebar.multiselect(
    "Product category", all_categories, default=all_categories
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Data: synthetic e-commerce dataset calibrated to real Olist "
    "Brazilian E-Commerce published statistics. See "
    "[Project 1](https://github.com/) for generation methodology."
)

# Apply filters
mask = (
    (orders_df["order_date"] >= start_date)
    & (orders_df["order_date"] <= end_date)
    & (orders_df["customer_state"].isin(selected_states))
    & (orders_df["product_category"].isin(selected_categories))
)
filtered = orders_df[mask]

# ---------------------------------------------------------------------
# HEADER + KPI CARDS
# ---------------------------------------------------------------------
st.title("📦 Olist Sales & Customer Analytics")
st.caption(
    "Interactive dashboard | Data through "
    f"{filtered['order_date'].max() if len(filtered) else 'N/A'} | "
    f"{len(filtered):,} order line items in current filter"
)

if filtered.empty:
    st.warning("No data matches the current filters. Try widening the date range or selections.")
    st.stop()

total_revenue = filtered["total_value"].sum()
n_orders = filtered["order_id"].nunique()
n_customers = filtered["customer_id"].nunique()
aov = total_revenue / n_orders if n_orders else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Revenue", f"R$ {total_revenue:,.0f}")
col2.metric("Orders", f"{n_orders:,}")
col3.metric("Unique Customers", f"{n_customers:,}")
col4.metric("Avg Order Value", f"R$ {aov:,.2f}")

st.markdown("---")

# ---------------------------------------------------------------------
# ROW 1: Revenue trend + category breakdown
# ---------------------------------------------------------------------
left, right = st.columns([2, 1])

with left:
    st.subheader("Revenue Trend (Monthly)")
    monthly = filtered.groupby("order_month")["total_value"].sum().reset_index()
    fig_trend = px.line(
        monthly, x="order_month", y="total_value", markers=True,
        labels={"order_month": "Month", "total_value": "Revenue (R$)"},
    )
    fig_trend.update_layout(height=350, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_trend, width='stretch')

with right:
    st.subheader("Revenue by Category (Top 8)")
    cat_revenue = (
        filtered.groupby("product_category")["total_value"]
        .sum().sort_values(ascending=False).head(8).reset_index()
    )
    fig_cat = px.bar(
        cat_revenue, x="total_value", y="product_category", orientation="h",
        labels={"total_value": "Revenue (R$)", "product_category": ""},
    )
    fig_cat.update_layout(height=350, margin=dict(l=10, r=10, t=30, b=10),
                           yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_cat, width='stretch')

# ---------------------------------------------------------------------
# ROW 2: Geographic breakdown + payment type
# ---------------------------------------------------------------------
left2, right2 = st.columns([2, 1])

with left2:
    st.subheader("Revenue by State")
    state_revenue = (
        filtered.groupby("customer_state")["total_value"]
        .sum().sort_values(ascending=False).reset_index()
    )
    fig_state = px.bar(
        state_revenue, x="customer_state", y="total_value",
        labels={"customer_state": "State", "total_value": "Revenue (R$)"},
    )
    fig_state.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_state, width='stretch')

with right2:
    st.subheader("Payment Method Mix")
    pay_mix = filtered.drop_duplicates("order_id")["payment_type"].value_counts().reset_index()
    pay_mix.columns = ["payment_type", "count"]
    fig_pay = px.pie(pay_mix, names="payment_type", values="count", hole=0.45)
    fig_pay.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_pay, width='stretch')

st.markdown("---")

# ---------------------------------------------------------------------
# ROW 3: RFM Customer Segmentation (re-using Project 1's logic)
# ---------------------------------------------------------------------
st.subheader("Customer Segmentation (RFM)")
st.caption(
    "Same RFM methodology as Project 1's SQL analysis — Recency, "
    "Frequency, Monetary value, scored into quintiles and labeled into "
    "five segments."
)

seg_summary = rfm_df.groupby("segment").agg(
    num_customers=("customer_id", "count"),
    total_revenue=("monetary", "sum"),
    avg_revenue=("monetary", "mean"),
).reset_index().sort_values("total_revenue", ascending=False)

seg_col1, seg_col2 = st.columns([1, 1])

with seg_col1:
    fig_seg_rev = px.bar(
        seg_summary, x="segment", y="total_revenue", color="segment",
        labels={"segment": "Segment", "total_revenue": "Total Revenue (R$)"},
        title="Revenue by Segment",
    )
    fig_seg_rev.update_layout(height=380, showlegend=False, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_seg_rev, width='stretch')

with seg_col2:
    fig_seg_count = px.pie(
        seg_summary, names="segment", values="num_customers", hole=0.45,
        title="Customer Count by Segment",
    )
    fig_seg_count.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_seg_count, width='stretch')

st.dataframe(
    seg_summary.rename(columns={
        "segment": "Segment", "num_customers": "# Customers",
        "total_revenue": "Total Revenue (R$)", "avg_revenue": "Avg Revenue/Customer (R$)",
    }).style.format({
        "Total Revenue (R$)": "{:,.2f}", "Avg Revenue/Customer (R$)": "{:,.2f}",
    }),
    width='stretch',
    hide_index=True,
)

champion_at_risk_pct_customers = (
    seg_summary[seg_summary["segment"].isin(["Champion", "At Risk (high value)"])]["num_customers"].sum()
    / seg_summary["num_customers"].sum() * 100
)
champion_at_risk_pct_revenue = (
    seg_summary[seg_summary["segment"].isin(["Champion", "At Risk (high value)"])]["total_revenue"].sum()
    / seg_summary["total_revenue"].sum() * 100
)
st.info(
    f"💡 **Champion + At Risk (high value)** segments make up "
    f"**{champion_at_risk_pct_customers:.1f}%** of customers but "
    f"**{champion_at_risk_pct_revenue:.1f}%** of total revenue. "
    f"The At Risk group is the highest-leverage target for a retention campaign — "
    f"same historical value as Champions, but losable."
)

st.markdown("---")
st.caption(
    "Built with Streamlit + Plotly. Data: synthetic dataset calibrated to "
    "real Olist Brazilian E-Commerce statistics (see Project 1 in this "
    "portfolio for full methodology). Source: "
    "[GitHub repo link]"
)
