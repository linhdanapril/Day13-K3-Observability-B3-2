"""Sinh dashboard HTML 6 panel tu data/logs.jsonl theo config/dashboard.yaml.

Cach dung:
    python scripts/build_dashboard.py            # ghi submission/evidence/dashboard.html
    python scripts/build_dashboard.py --out docs/dashboard.html
"""
from __future__ import annotations

import argparse
import html
import json
import math
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, math.ceil(len(ordered) * p / 100) - 1)
    return ordered[idx]


def _fmt(v: float) -> str:
    if v >= 1000:
        return f"{v:,.0f}"
    if v >= 100:
        return f"{v:,.1f}"
    return f"{v:,.3f}"


def _status_class(current: float, threshold: float, operator: str) -> str:
    if operator == "lte":
        return "ok" if current <= threshold else "bad"
    return "ok" if current >= threshold else "bad"


def build() -> dict:
    dashboard_cfg = yaml.safe_load(
        (REPO_ROOT / "config" / "dashboard.yaml").read_text(encoding="utf-8")
    )["dashboard"]
    slo_cfg = yaml.safe_load((REPO_ROOT / "config" / "slo.yaml").read_text(encoding="utf-8"))

    records = []
    log_path = REPO_ROOT / "data" / "logs.jsonl"
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    received = [r for r in records if r.get("event") == "request_received"]
    sent = [r for r in records if r.get("event") == "response_sent"]
    failed = [r for r in records if r.get("event") == "request_failed"]

    latencies = [r.get("latency_ms", 0) for r in sent if isinstance(r.get("latency_ms"), (int, float))]
    costs = [r.get("cost_usd", 0) for r in sent if isinstance(r.get("cost_usd"), (int, float))]
    tokens_in = [r.get("tokens_in", 0) for r in sent if isinstance(r.get("tokens_in"), (int, float))]
    tokens_out = [r.get("tokens_out", 0) for r in sent if isinstance(r.get("tokens_out"), (int, float))]
    quality = [r.get("quality_score", 0) for r in sent if isinstance(r.get("quality_score"), (int, float))]

    ts_list = []
    for r in records:
        try:
            ts_list.append(datetime.fromisoformat(r["ts"].replace("Z", "+00:00")))
        except (KeyError, ValueError):
            continue
    if ts_list:
        now = max(ts_list)
        t0 = now - timedelta(minutes=dashboard_cfg["time_range_minutes"])
        window_records = [r for r in records if _ts(r) is not None and t0 <= _ts(r) <= now]
    else:
        window_records = records
        now = datetime.now(timezone.utc)

    w_received = [r for r in window_records if r.get("event") == "request_received"]
    w_failed = [r for r in window_records if r.get("event") == "request_failed"]

    error_rate = (len(w_failed) / len(w_received) * 100) if w_received else 0.0
    error_breakdown: dict[str, int] = {}
    for r in w_failed:
        et = r.get("error_type") or "unknown"
        error_breakdown[et] = error_breakdown.get(et, 0) + 1

    minutes = dashboard_cfg["time_range_minutes"]
    cost_per_min = [0.0] * minutes
    for r in sent:
        ts = _ts(r)
        if ts is None or (ts_list and not (t0 <= ts <= now)):
            continue
        slot = min(max(int((ts - t0).total_seconds() // 60), 0), minutes - 1)
        cost_per_min[slot] += r.get("cost_usd", 0)

    traffic_per_min = [0] * minutes
    for r in received:
        ts = _ts(r)
        if ts is None or (ts_list and not (t0 <= ts <= now)):
            continue
        slot = min(max(int((ts - t0).total_seconds() // 60), 0), minutes - 1)
        traffic_per_min[slot] += 1

    panels = {
        "latency": {
            "p50": _percentile(latencies, 50),
            "p95": _percentile(latencies, 95),
            "p99": _percentile(latencies, 99),
            "threshold": 3000,
            "operator": "lte",
            "unit": "ms",
        },
        "traffic": {
            "count": len(received),
            "rate_per_min": len(received) / minutes,
            "threshold": 1,
            "operator": "gte",
            "unit": "req/min",
        },
        "errors": {
            "error_rate_pct": error_rate,
            "breakdown": error_breakdown,
            "threshold": 2,
            "operator": "lte",
            "unit": "%",
        },
        "cost": {
            "total": sum(costs),
            "per_min": cost_per_min,
            "threshold": 2.5,
            "operator": "lte",
            "unit": "USD",
        },
        "tokens": {
            "tokens_in": sum(tokens_in),
            "tokens_out": sum(tokens_out),
            "threshold": 50000,
            "operator": "lte",
            "unit": "tokens",
        },
        "quality": {
            "mean": statistics.mean(quality) if quality else 0.0,
            "threshold": 0.75,
            "operator": "gte",
            "unit": "0-1",
        },
    }

    return {
        "cfg": dashboard_cfg,
        "slo": slo_cfg,
        "now": now,
        "t0": t0 if ts_list else None,
        "total_records": len(records),
        "traffic_per_min": traffic_per_min,
        "cost_per_min": cost_per_min,
        "panels": panels,
    }


def _ts(r: dict):
    try:
        return datetime.fromisoformat(r["ts"].replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return None


def _bar_chart(values: list[float], height: int = 120, fmt: str = "{:.1f}") -> str:
    if not values or max(values) <= 0:
        return f'<svg width="100%" height="{height}"><text x="10" y="20">No data</text></svg>'
    vmax = max(values)
    bars = []
    width = max(2, 600 // len(values))
    for i, v in enumerate(values):
        h = max(2, int(v / vmax * (height - 20)))
        x = i * (width + 2)
        bars.append(
            f'<rect x="{x}" y="{height - h}" width="{width}" height="{h}" '
            f'fill="#4f9cf9" rx="2"><title>{fmt.format(v)}</title></rect>'
        )
    return f'<svg viewBox="0 0 600 {height}" width="100%" height="{height}">{"" .join(bars)}</svg>'


def render(data: dict) -> str:
    cfg = data["cfg"]
    panels = data["panels"]
    unit_color = {
        "latency": "#f9a94f",
        "traffic": "#4f9cf9",
        "errors": "#f95f6b",
        "cost": "#3fbe9a",
        "tokens": "#b07df9",
        "quality": "#f9d34f",
    }

    cards = []
    for pid in ("latency", "traffic", "errors", "cost", "tokens", "quality"):
        p = panels[pid]
        thr = p["threshold"]
        op = p["operator"]
        cls = _status_class(_current_value(p), thr, op)
        color = unit_color[pid]

        if pid == "latency":
            body = (
                f'<div class="metric-line"><span class="metric-val">{_fmt(p["p50"])}</span><span class="unit">P50</span></div>'
                f'<div class="metric-line"><span class="metric-val">{_fmt(p["p95"])}</span><span class="unit">P95</span></div>'
                f'<div class="metric-line"><span class="metric-val">{_fmt(p["p99"])}</span><span class="unit">P99</span></div>'
            )
        elif pid == "traffic":
            body = (
                f'<div class="metric-line"><span class="metric-val">{p["count"]}</span><span class="unit">requests</span></div>'
                f'<div class="metric-line"><span class="metric-val">{p["rate_per_min"]:.2f}</span><span class="unit">req/min</span></div>'
                + _bar_chart(data["traffic_per_min"])
            )
        elif pid == "errors":
            bd = "".join(
                f'<span class="err-chip">{html.escape(k)}: {v}</span>' for k, v in sorted(p["breakdown"].items())
            ) or "<span class='err-chip'>none</span>"
            body = (
                f'<div class="metric-line"><span class="metric-val">{p["error_rate_pct"]:.2f}%</span><span class="unit">error rate</span></div>'
                f'<div class="err-row">{bd}</div>'
            )
        elif pid == "cost":
            body = (
                f'<div class="metric-line"><span class="metric-val">${p["total"]:.4f}</span><span class="unit">total</span></div>'
                + _bar_chart(p["per_min"], fmt="${:.4f}")
            )
        elif pid == "tokens":
            body = (
                f'<div class="metric-line"><span class="metric-val">{_fmt(p["tokens_in"])}</span><span class="unit">tokens in</span></div>'
                f'<div class="metric-line"><span class="metric-val">{_fmt(p["tokens_out"])}</span><span class="unit">tokens out</span></div>'
            )
        else:
            body = (
                f'<div class="metric-line"><span class="metric-val">{p["mean"]:.3f}</span><span class="unit">mean quality</span></div>'
            )

        op_symbol = "<=" if op == "lte" else ">="
        cards.append(
            f"""
<div class="card">
  <div class="card-head">
    <span class="dot" style="background:{color}"></span>
    <span class="card-title">{pid.title()}</span>
    <span class="badge {cls}">{'OK' if cls == 'ok' else 'BREACH'}</span>
  </div>
  <div class="card-body">{body}</div>
  <div class="card-foot">threshold: {op_symbol} {thr} {p['unit']}</div>
</div>"""
        )

    t0 = data["t0"]
    trange = (
        f"{t0:%H:%M} - {data['now']:%H:%M} UTC ({cfg['time_range_minutes']} min)"
        if t0
        else "no ts"
    )
    slo_lines = "".join(
        f'<tr><td>{html.escape(k)}</td><td>{v.get("objective")} {v.get("unit", "")}</td><td>target {v.get("target")}%</td></tr>'
        for k, v in data["slo"]["slis"].items()
    )

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>{html.escape(cfg['title'])}</title>
<style>
  :root {{ --bg:#0f1524; --card:#171f31; --text:#e8edf7; --muted:#8b96ad; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text); font-family:Inter,system-ui,sans-serif; padding:24px; }}
  h1 {{ font-size:20px; }}
  .meta {{ color:var(--muted); font-size:12px; margin:6px 0 20px; }}
  .grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }}
  @media (max-width:900px) {{ .grid {{ grid-template-columns:1fr; }} }}
  .card {{ background:var(--card); border:1px solid #24304a; border-radius:12px; padding:16px; }}
  .card-head {{ display:flex; align-items:center; gap:8px; margin-bottom:12px; }}
  .dot {{ width:10px; height:10px; border-radius:50%; }}
  .card-title {{ font-weight:600; font-size:14px; text-transform:capitalize; }}
  .badge {{ margin-left:auto; font-size:11px; padding:2px 8px; border-radius:999px; }}
  .badge.ok {{ background:#16382a; color:#5ad493; }}
  .badge.bad {{ background:#44232b; color:#ff8f98; }}
  .card-body {{ min-height:120px; }}
  .metric-line {{ display:flex; align-items:baseline; gap:8px; margin-bottom:6px; }}
  .metric-val {{ font-size:22px; font-weight:700; }}
  .unit {{ color:var(--muted); font-size:11px; }}
  .card-foot {{ color:var(--muted); font-size:11px; margin-top:12px; border-top:1px dashed #24304a; padding-top:8px; }}
  svg {{ display:block; margin-top:8px; }}
  .err-row {{ display:flex; gap:6px; flex-wrap:wrap; margin-top:8px; }}
  .err-chip {{ background:#2a2438; color:#c9b8f7; font-size:11px; padding:2px 8px; border-radius:6px; }}
  table {{ width:100%; border-collapse:collapse; margin-top:12px; font-size:12px; }}
  td,th {{ border:1px solid #24304a; padding:6px 8px; text-align:left; }}
  th {{ color:var(--muted); font-weight:500; }}
</style>
</head>
<body>
  <h1>{html.escape(cfg['title'])}</h1>
  <div class="meta">
    Source: <code>data/logs.jsonl</code> | Time range: {html.escape(trange)} |
    Auto-refresh: every {cfg['refresh_seconds']}s |
    Records in file: {data['total_records']} |
    Schema v{cfg['schema_version']}
  </div>
  <div class="grid">
    {''.join(cards)}
  </div>
  <h1 style="margin-top:28px">SLO</h1>
  <table>
    <tr><th>SLI</th><th>Objective</th><th>Target</th></tr>
    {slo_lines}
  </table>
  <script>
    setTimeout(function() {{ location.reload(); }}, {cfg['refresh_seconds'] * 1000});
  </script>
</body>
</html>"""


def _current_value(p: dict) -> float:
    if "error_rate_pct" in p:
        return p["error_rate_pct"]
    if "total" in p:
        return p["total"]
    if "mean" in p:
        return p["mean"]
    if "rate_per_min" in p:
        return p["rate_per_min"]
    return p.get("p95", 0)


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "submission" / "evidence" / "dashboard.html")
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(build()), encoding="utf-8")
    print(f"Dashboard written: {args.out}")


if __name__ == "__main__":
    main()
