"""Streamlit dashboard for visualizing crypto sentiment and price data."""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple

import boto3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from botocore.exceptions import BotoCoreError, ClientError
from streamlit_autorefresh import st_autorefresh

DEFAULT_REGION = os.getenv("AWS_REGION", "us-east-1")
DEFAULT_PROFILE = os.getenv("AWS_PROFILE")
COIN_ORDER = ["bitcoin", "ethereum", "dogecoin"]
COIN_NAME_MAP: Dict[str, str] = {
    "bitcoin": "Bitcoin",
    "ethereum": "Ethereum",
    "dogecoin": "Dogecoin",
}
REQUIRED_COLUMNS = {"coin", "sentiment_label", "sentiment_score", "price_usd", "current_ts"}
NUMERIC_COLUMNS = ["sentiment_score", "price_usd", "price_sample_count"]
DATETIME_COLUMNS = ["current_ts", "timestamp"]
DEFAULT_DYNAMO_TABLE = os.getenv("PROCESSED_DATA_TABLE", "sparkling-water-dev-crypto-sentiment")
DEFAULT_DYNAMO_LIMIT = int(os.getenv("DYNAMO_SCAN_LIMIT", "2500"))


def _get_dynamo_table(table_name: str):
    session = boto3.Session(profile_name=DEFAULT_PROFILE) if DEFAULT_PROFILE else boto3.Session()
    dynamo_resource = session.resource("dynamodb", region_name=DEFAULT_REGION)
    return dynamo_resource.Table(table_name)


def _build_sample_data() -> pd.DataFrame:
    """Return an in-memory demo dataset for quick UI previews."""
    base_time = pd.Timestamp.utcnow().floor("H") - pd.Timedelta(hours=23)
    records: List[Dict[str, object]] = []
    sentiments = ["positive", "neutral", "negative"]
    scores = [0.68, 0.04, -0.42]
    prices = {
        "bitcoin": 67000,
        "ethereum": 3500,
        "dogecoin": 0.19,
    }

    for idx, coin in enumerate(COIN_ORDER):
        for step in range(24):
            ts = base_time + pd.Timedelta(hours=step)
            records.append(
                {
                    "coin": coin,
                    "current_ts": ts.isoformat(),
                    "sentiment_label": sentiments[(idx + step) % len(sentiments)],
                    "sentiment_score": scores[(idx + step) % len(scores)] + (step % 4) * 0.015,
                    "price_usd": prices[coin] * (1 + (step - 12) * 0.002),
                    "price_sample_count": 12,
                }
            )

    return pd.DataFrame.from_records(records)


def _coerce_datetime_columns(df: pd.DataFrame) -> pd.DataFrame:
    for column in DATETIME_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], utc=True, errors="coerce")
    if "timestamp" not in df.columns and "current_ts" in df.columns:
        df["timestamp"] = df["current_ts"]
    if "timestamp" in df.columns:
        df = df.dropna(subset=["timestamp"])
    return df


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        missing_str = ", ".join(sorted(missing))
        raise RuntimeError(
            "Dataset is missing required columns. Expected at least: "
            f"coin, sentiment_label, sentiment_score. Missing {missing_str}."
        )

    for col_name in NUMERIC_COLUMNS:
        if col_name in df.columns:
            df[col_name] = pd.to_numeric(df[col_name], errors="coerce")

    df = _coerce_datetime_columns(df)

    df["coin_key"] = df["coin"].astype(str).str.strip().str.lower()
    df["coin_display"] = df["coin_key"].map(COIN_NAME_MAP).fillna(
        df["coin_key"].str.replace("_", " ").str.title()
    )

    if "timestamp" in df.columns:
        df = df.sort_values("timestamp")
    return df.reset_index(drop=True)


@st.cache_data(show_spinner=False, ttl=300)
def load_data_from_dynamo(table_name: str, scan_limit: int) -> pd.DataFrame:
    if not table_name:
        raise ValueError("DynamoDB table name is required.")
    if scan_limit <= 0:
        raise ValueError("Scan limit must be a positive integer.")

    table = _get_dynamo_table(table_name)
    items: List[Dict[str, object]] = []
    last_evaluated_key = None
    retrieved = 0

    try:
        while retrieved < scan_limit:
            batch_limit = min(scan_limit - retrieved, 1000)
            if batch_limit <= 0:
                break
            scan_kwargs = {"Limit": batch_limit}
            if last_evaluated_key:
                scan_kwargs["ExclusiveStartKey"] = last_evaluated_key
            response = table.scan(**scan_kwargs)
            batch = response.get("Items", [])
            items.extend(batch)
            retrieved += len(batch)
            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break
    except (ClientError, BotoCoreError) as exc:
        raise RuntimeError(f"Failed to scan DynamoDB table {table_name}: {exc}") from exc

    if not items:
        raise RuntimeError(
            "No records returned from DynamoDB. Ensure the table contains processed data."
        )

    def _convert(value):
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, list):
            return [_convert(v) for v in value]
        if isinstance(value, dict):
            return {k: _convert(v) for k, v in value.items()}
        return value

    normalized_items = [{k: _convert(v) for k, v in item.items()} for item in items]
    df = pd.DataFrame(normalized_items)
    return _normalize_columns(df)


def _compute_date_range(df: pd.DataFrame) -> Tuple[datetime, datetime]:
    """Return min/max timestamps with slight padding for UI controls."""
    if "timestamp" not in df.columns or df["timestamp"].isna().all():
        now = pd.Timestamp.utcnow()
        return (now - timedelta(days=7), now)

    min_ts = df["timestamp"].min()
    max_ts = df["timestamp"].max()
    if pd.isna(min_ts) or pd.isna(max_ts):
        now = pd.Timestamp.utcnow()
        return (now - timedelta(days=7), now)
    return (min_ts.to_pydatetime(), max_ts.to_pydatetime())


def _format_sentiment_label(label: str) -> str:
    """Return sentiment label with first letter capitalized for display."""
    if not isinstance(label, str):
        return "Unknown"
    return label.capitalize()


st.set_page_config(
    page_title="Crypto Sentiment Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
)

st.sidebar.title("Configuration")
st.sidebar.caption(
    "Choose between demo data or the processed dataset stored in DynamoDB."
)

data_source = st.sidebar.radio(
    "Data source",
    options=("Sample (demo)", "DynamoDB"),
    index=0,
)

auto_refresh = st.sidebar.checkbox(
    "Auto-refresh",
    value=False,
    help="Reload the dashboard automatically to capture new data arrivals.",
)
if auto_refresh:
    refresh_interval_seconds = st.sidebar.slider(
        "Refresh interval (seconds)",
        min_value=30,
        max_value=300,
        value=60,
        step=15,
        help="How frequently to rerun the dashboard when auto-refresh is enabled.",
    )
    st_autorefresh(interval=refresh_interval_seconds * 1000, limit=None, key="auto_refresh_counter")


dynamo_table = DEFAULT_DYNAMO_TABLE
dynamo_limit = DEFAULT_DYNAMO_LIMIT
if data_source == "DynamoDB":
    dynamo_table = st.sidebar.text_input("Table name", value=DEFAULT_DYNAMO_TABLE)
    dynamo_limit = st.sidebar.slider(
        "Max items to fetch",
        min_value=100,
        max_value=5000,
        value=min(DEFAULT_DYNAMO_LIMIT, 2000),
        step=100,
        help="Adjust to balance load vs. fidelity."
    )

reload_requested = st.sidebar.button("Clear cache & reload")
if reload_requested:
    load_data_from_dynamo.clear()
    st.rerun()

try:
    if data_source == "Sample (demo)":
        dataset = _normalize_columns(_build_sample_data())
    else:
        dataset = load_data_from_dynamo(dynamo_table.strip() or DEFAULT_DYNAMO_TABLE, int(dynamo_limit))
except Exception as err:  
    st.error(str(err))
    st.stop()

coin_options = (
    dataset[["coin_key", "coin_display"]]
    .drop_duplicates()
    .sort_values("coin_display")
)

preferred_display_order: List[str] = []
for coin in COIN_ORDER:
    matches = coin_options.loc[coin_options["coin_key"] == coin, "coin_display"].tolist()
    preferred_display_order.extend(matches)

remaining_displays = [
    display
    for display in coin_options["coin_display"].tolist()
    if display not in preferred_display_order
]
coin_display_options = preferred_display_order + sorted(remaining_displays)

if not coin_display_options:
    st.error("No coins available in the dataset.")
    st.stop()

selected_coin_display = st.sidebar.selectbox("Select coin", options=coin_display_options)
selected_coin_key = (
    coin_options.loc[coin_options["coin_display"] == selected_coin_display, "coin_key"].iloc[0]
)

min_date, max_date = _compute_date_range(dataset)

# Create datetime range inputs with separate date and time inputs
st.sidebar.markdown("**DateTime range**")

st.sidebar.markdown("Start date & time")
start_col1, start_col2 = st.sidebar.columns(2)
with start_col1:
    start_date = st.date_input(
        "Date",
        value=min_date.date(),
        min_value=min_date.date(),
        max_value=max_date.date(),
        help="Select start date",
        key="start_date"
    )
with start_col2:
    start_time = st.time_input(
        "Time",
        value=min_date.time(),
        help="Select start time",
        key="start_time"
    )

st.sidebar.markdown("End date & time")
end_col1, end_col2 = st.sidebar.columns(2)
with end_col1:
    end_date = st.date_input(
        "Date",
        value=max_date.date(),
        min_value=min_date.date(),
        max_value=max_date.date(),
        help="Select end date",
        key="end_date"
    )
with end_col2:
    end_time = st.time_input(
        "Time",
        value=max_date.time(),
        help="Select end time",
        key="end_time"
    )

# Combine date and time into datetime objects
start_datetime = datetime.combine(start_date, start_time)
end_datetime = datetime.combine(end_date, end_time)

# Ensure start is before end
if start_datetime > end_datetime:
    start_datetime, end_datetime = end_datetime, start_datetime

mask_coin = dataset["coin_key"] == selected_coin_key
if "timestamp" in dataset.columns:
    # Convert to timezone-aware datetime for comparison
    start_ts = pd.Timestamp(start_datetime, tz='UTC')
    end_ts = pd.Timestamp(end_datetime, tz='UTC')
    mask_date = dataset["timestamp"].between(start_ts, end_ts, inclusive='both')
else:
    mask_date = pd.Series(True, index=dataset.index)

filtered = dataset.loc[mask_coin & mask_date].copy()

if filtered.empty:
    st.warning("No records match the current selections. Try expanding the filters.")
    st.stop()

aggregated = pd.DataFrame()
if "timestamp" in filtered.columns:
    aggregated = (
        filtered.set_index("timestamp")
        .resample("H")
        .agg({"price_usd": "mean", "sentiment_score": "mean"})
        .dropna(how="all")
    )

sentiment_distribution = (
    filtered.groupby("sentiment_label").size().rename("count").reset_index()
)
sentiment_distribution["sentiment_label"] = sentiment_distribution["sentiment_label"].apply(
    _format_sentiment_label
)

sentiment_trend = pd.Series(dtype=float)
if "timestamp" in filtered.columns:
    sentiment_trend = (
        filtered.set_index("timestamp")
        .resample("H")["sentiment_score"]
        .mean()
        .dropna()
    )

correlation = pd.NA
price_sentiment_df = filtered[["price_usd", "sentiment_score"]].dropna()
if not price_sentiment_df.empty and price_sentiment_df.shape[0] > 1:
    correlation = price_sentiment_df.corr().iloc[0, 1]

if "timestamp" in filtered.columns:
    latest_row = filtered.sort_values("timestamp").iloc[-1]
else:
    latest_row = filtered.iloc[-1]
latest_price = latest_row.get("price_usd", float("nan"))
avg_sentiment = filtered["sentiment_score"].mean()
price_sample_count = latest_row.get("price_sample_count")

st.title("Crypto Sentiment Intelligence Dashboard")
st.markdown(
    "Explore the relationship between Reddit sentiment and market performance "
    "for major crypto assets. Data reflects processed outputs captured by the "
    "Spark job and persisted in DynamoDB (sample mode uses synthetic data)."
)

kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
kpi_col1.metric(
    "Latest price (USD)",
    f"{latest_price:,.2f}" if pd.notna(latest_price) else "Unavailable",
)
kpi_col2.metric("Avg sentiment score", f"{avg_sentiment:.2f}")
if pd.notna(correlation):
    kpi_col3.metric("Price ↔ Sentiment correlation", f"{correlation:.2f}")
else:
    kpi_col3.metric("Price ↔ Sentiment correlation", "Insufficient data")

if price_sample_count is not None and not pd.isna(price_sample_count):
    st.caption(f"Price sample count for latest hour: {int(price_sample_count)}")

# Dual-axis price vs sentiment chart
if not aggregated.empty:
    fig_price_sentiment = go.Figure()
    fig_price_sentiment.add_trace(
        go.Scatter(
            x=aggregated.index,
            y=aggregated["price_usd"],
            mode="lines",
            name="Avg price (USD)",
            line=dict(color="#29b5e8", width=3),
        )
    )
    fig_price_sentiment.add_trace(
        go.Scatter(
            x=aggregated.index,
            y=aggregated["sentiment_score"],
            mode="lines",
            name="Avg sentiment score",
            line=dict(color="#f9c74f", width=3, dash="dot"),
            yaxis="y2",
        )
    )
    fig_price_sentiment.update_layout(
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="Timestamp"),
        yaxis=dict(title="Price (USD)", showgrid=False),
        yaxis2=dict(
            title="Sentiment score",
            overlaying="y",
            side="right",
            showgrid=False,
            zeroline=True,
        ),
    )
    st.plotly_chart(fig_price_sentiment, use_container_width=True)
else:
    st.info("Not enough data to plot price vs sentiment for the selected range.")

col_left, col_right = st.columns(2)
with col_left:
    if not sentiment_distribution.empty:
        fig_distribution = px.bar(
            sentiment_distribution,
            x="sentiment_label",
            y="count",
            color="sentiment_label",
            color_discrete_map={
                "Positive": "#43aa8b",
                "Neutral": "#577590",
                "Negative": "#f94144",
            },
            title="Sentiment distribution",
            labels={"sentiment_label": "Sentiment", "count": "Count"},
        )
        fig_distribution.update_layout(showlegend=False, margin=dict(l=40, r=20, t=60, b=40))
        st.plotly_chart(fig_distribution, use_container_width=True)
    else:
        st.info("Sentiment label distribution unavailable for this selection.")

with col_right:
    if not sentiment_trend.empty:
        fig_trend = px.line(
            sentiment_trend.reset_index(),
            x="timestamp",
            y="sentiment_score",
            title=f"Hourly average sentiment",
            labels={"timestamp": "Timestamp", "sentiment_score": "Sentiment score"},
        )
        fig_trend.update_traces(line=dict(color="#f3722c", width=3))
        fig_trend.update_layout(margin=dict(l=40, r=20, t=60, b=40))
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Not enough points to render a sentiment trend.")

# Sentiment highlights section
st.subheader("Sentiment highlights")
highlights_col1, highlights_col2 = st.columns(2)

positive_records = filtered.dropna(subset=["sentiment_score"]).nlargest(5, "sentiment_score")
negative_records = filtered.dropna(subset=["sentiment_score"]).nsmallest(5, "sentiment_score")


def _render_record(record: pd.Series) -> str:
    ts_value = record.get("timestamp")
    ts_display = ts_value.strftime("%Y-%m-%d %H:%M UTC") if pd.notna(ts_value) else "Unknown"
    price_display = record.get("price_usd")
    price_str = f"${price_display:,.2f}" if pd.notna(price_display) else "n/a"
    return (
        f"Time: `{ts_display}`  \n"
        f"Sentiment score: `{record['sentiment_score']:.2f}`  \n"
        f"Price: `{price_str}`"
    )


with highlights_col1:
    st.markdown("### Highest sentiment snapshots")
    if positive_records.empty:
        st.info("No positive sentiment samples found in the selected range.")
    else:
        for _, row in positive_records.iterrows():
            st.markdown(_render_record(row))
            st.markdown("---")

with highlights_col2:
    st.markdown("### Lowest sentiment snapshots")
    if negative_records.empty:
        st.info("No negative sentiment samples found in the selected range.")
    else:
        for _, row in negative_records.iterrows():
            st.markdown(_render_record(row))
            st.markdown("---")

with st.expander("Peek at underlying data"):
    display_cols = [
        col
        for col in [
            "timestamp",
            "coin",
            "price_usd",
            "price_sample_count",
            "sentiment_label",
            "sentiment_score",
        ]
        if col in filtered.columns
    ]
    st.dataframe(
        filtered[display_cols].tail(500),
        use_container_width=True,
        height=400,
    )

st.caption(
    "Dashboard built with Streamlit, Plotly, pandas, and boto3. Switch the data "
    "source in the sidebar to view DynamoDB records or sample data."
)
