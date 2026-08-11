from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
DASHBOARD_CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"


def load_dashboard_config() -> dict:
    payload = yaml.safe_load(DASHBOARD_CONFIG_PATH.read_text(encoding="utf-8"))
    return payload["dashboard"]


def panel_by_id(config: dict, panel_id: str) -> dict:
    return next(p for p in config["panels"] if p["id"] == panel_id)


def load_logs() -> pd.DataFrame:
    if not LOG_PATH.exists():
        return pd.DataFrame()
    rows = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    return df.dropna(subset=["ts"])


def render_threshold(label: str, value: float | None, threshold: dict, unit: str) -> None:
    if value is None or pd.isna(value):
        st.metric(label, "no data")
        return
    op = threshold["operator"]
    ok = value <= threshold["value"] if op == "lte" else value >= threshold["value"]
    cmp_symbol = "≤" if op == "lte" else "≥"
    st.metric(
        label,
        f"{value:,.2f} {unit}",
        delta=("OK" if ok else "VI PHAM SLO") + f" (nguong {cmp_symbol} {threshold['value']} {unit})",
        delta_color="normal" if ok else "inverse",
    )


def main() -> None:
    config = load_dashboard_config()
    window_minutes = config["time_range_minutes"]
    refresh_seconds = config["refresh_seconds"]

    st.set_page_config(page_title=config["title"], layout="wide")
    st.markdown(
        f"<script>setTimeout(() => window.location.reload(), {refresh_seconds * 1000});</script>",
        unsafe_allow_html=True,
    )

    st.title(config["title"])

    show_all = st.sidebar.checkbox(
        "Bo qua time range, hien toan bo log (debug)", value=False
    )
    st.sidebar.caption(f"Nguon du lieu: {LOG_PATH.relative_to(REPO_ROOT)}")
    st.sidebar.caption(f"Refresh moi {refresh_seconds}s")

    df = load_logs()
    if df.empty:
        st.warning(
            "Chua co data/logs.jsonl hoac file rong. "
            "Chay API va `python scripts/load_test.py` truoc."
        )
        return

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=window_minutes)
    windowed = df if show_all else df[df["ts"] >= window_start]

    range_label = "toan bo log" if show_all else f"{window_minutes} phut gan nhat"
    st.caption(
        f"Time range: {range_label} | Cap nhat luc {now.strftime('%Y-%m-%d %H:%M:%S UTC')} "
        f"| {len(windowed)} log record trong khoang xem"
    )

    if windowed.empty:
        st.warning(
            f"Khong co log nao trong {window_minutes} phut gan nhat. "
            "Bat 'Bo qua time range' o sidebar de xem du lieu cu, hoac chay load test lai."
        )
        return

    requests = windowed[windowed["event"] == "request_received"]
    responses = windowed[windowed["event"] == "response_sent"]
    failures = windowed[windowed["event"] == "request_failed"]

    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)

    # 1. Latency
    with col1:
        p = panel_by_id(config, "latency")
        st.subheader(p["title"])
        if not responses.empty:
            quantiles = responses["latency_ms"].quantile([0.5, 0.95, 0.99])
            c1, c2, c3 = st.columns(3)
            c1.metric("P50", f"{quantiles[0.5]:,.0f} ms")
            c2.metric("P95", f"{quantiles[0.95]:,.0f} ms")
            c3.metric("P99", f"{quantiles[0.99]:,.0f} ms")
            render_threshold("P95 vs SLO", quantiles[0.95], p["threshold"], p["unit"])
            fig = px.line(responses.sort_values("ts"), x="ts", y="latency_ms", markers=True)
            fig.add_hline(y=p["threshold"]["value"], line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Chua co response_sent")

    # 2. Traffic
    with col4:
        p = panel_by_id(config, "traffic")
        st.subheader(p["title"])
        if not requests.empty:
            per_minute = requests.set_index("ts").resample("1min").size()
            rate = len(requests) / max(window_minutes, 1)
            render_threshold("Request/phut (trung binh)", rate, p["threshold"], p["unit"])
            st.plotly_chart(
                px.bar(per_minute.reset_index(name="count"), x="ts", y="count"),
                use_container_width=True,
            )
        else:
            st.info("Chua co request_received")

    # 3. Errors
    with col2:
        p = panel_by_id(config, "errors")
        st.subheader(p["title"])
        total_requests = len(requests)
        error_rate = (len(failures) / total_requests * 100) if total_requests else None
        render_threshold("Error rate", error_rate, p["threshold"], p["unit"])
        if not failures.empty and "error_type" in failures:
            st.plotly_chart(
                px.bar(failures["error_type"].value_counts().reset_index(), x="error_type", y="count"),
                use_container_width=True,
            )
        else:
            st.success("Khong co request_failed trong khoang xem")

    # 4. Cost
    with col5:
        p = panel_by_id(config, "cost")
        st.subheader(p["title"])
        if not responses.empty:
            total_cost = responses["cost_usd"].sum()
            render_threshold("Tong cost", total_cost, p["threshold"], p["unit"])
            per_minute_cost = responses.set_index("ts")["cost_usd"].resample("1min").sum()
            st.plotly_chart(
                px.line(per_minute_cost.reset_index(), x="ts", y="cost_usd", markers=True),
                use_container_width=True,
            )
        else:
            st.info("Chua co response_sent")

    # 5. Tokens
    with col3:
        p = panel_by_id(config, "tokens")
        st.subheader(p["title"])
        if not responses.empty:
            sum_in = responses["tokens_in"].sum()
            sum_out = responses["tokens_out"].sum()
            render_threshold("Tong token (in+out)", sum_in + sum_out, p["threshold"], p["unit"])
            st.plotly_chart(
                px.bar(
                    pd.DataFrame({"loai": ["tokens_in", "tokens_out"], "so_luong": [sum_in, sum_out]}),
                    x="loai",
                    y="so_luong",
                ),
                use_container_width=True,
            )
        else:
            st.info("Chua co response_sent")

    # 6. Quality
    with col6:
        p = panel_by_id(config, "quality")
        st.subheader(p["title"])
        if not responses.empty:
            mean_quality = responses["quality_score"].mean()
            render_threshold("Quality trung binh", mean_quality, p["threshold"], p["unit"])
            st.plotly_chart(
                px.line(responses.sort_values("ts"), x="ts", y="quality_score", markers=True),
                use_container_width=True,
            )
        else:
            st.info("Chua co response_sent")


if __name__ == "__main__":
    main()
