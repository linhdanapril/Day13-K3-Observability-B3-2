"""
Metrics Collection Module - CP1

Collects and aggregates observability metrics for the chat application:
- Request latency tracking (P50, P95, P99)
- Cost and token usage tracking
- Error rate calculation with breakdown by type
- Traffic counting
- Quality score aggregation

These metrics feed into the dashboard and SLO monitoring.
"""
from __future__ import annotations

from collections import Counter
from statistics import mean

# -----------------------------------------------------------------------------
# Global metric storage
# Using module-level globals for simplicity. In production, consider using
# a proper metrics library (e.g., prometheus_client) for thread-safety and
# cardinality management.
# -----------------------------------------------------------------------------

REQUEST_LATENCIES: list[int] = []   # Latency of each request in milliseconds
REQUEST_COSTS: list[float] = []      # Cost in USD for each request
REQUEST_TOKENS_IN: list[int] = []    # Input tokens per request
REQUEST_TOKENS_OUT: list[int] = []   # Output tokens per request
ERRORS: Counter[str] = Counter()     # Error count by error type (e.g., "timeout", "validation")
TRAFFIC: int = 0                      # Total successful request count
QUALITY_SCORES: list[float] = []      # Quality scores for each response


def record_request(
    latency_ms: int,
    cost_usd: float,
    tokens_in: int,
    tokens_out: int,
    quality_score: float
) -> None:
    """
    Record metrics for a single successful request.

    Accumulates all metrics into global lists/counters for later aggregation.

    Args:
        latency_ms: Request processing time in milliseconds
        cost_usd: LLM API cost for this request in USD
        tokens_in: Number of input tokens consumed
        tokens_out: Number of output tokens generated
        quality_score: Quality score for the response (0.0 - 1.0)
    """
    global TRAFFIC
    TRAFFIC += 1
    REQUEST_LATENCIES.append(latency_ms)
    REQUEST_COSTS.append(cost_usd)
    REQUEST_TOKENS_IN.append(tokens_in)
    REQUEST_TOKENS_OUT.append(tokens_out)
    QUALITY_SCORES.append(quality_score)


def record_error(error_type: str) -> None:
    """
    Record an error occurrence.

    Used to track error rates and identify error patterns.
    The error_type should be a short, descriptive string like:
    "validation_error", "timeout", "rate_limit", "internal_error"

    Args:
        error_type: Categorical identifier for the error type
    """
    ERRORS[error_type] += 1


def percentile(values: list[int], p: int) -> float:
    """
    Calculate the p-th percentile of a list of values.

    Uses nearest-rank method: sort values, then pick the value at
    index (p/100 * n + 0.5) - 1.

    Args:
        values: List of numeric values (e.g., latencies)
        p: Percentile to calculate (e.g., 95 for P95)

    Returns:
        The value at the p-th percentile
    """
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])


def snapshot() -> dict:
    """
    Generate a snapshot of all current metrics.

    Calculates aggregated metrics from accumulated data:
    - Traffic and error rate
    - Latency percentiles (P50, P95, P99)
    - Cost and token totals/averages
    - Quality score average
    - Error breakdown by type

    This snapshot is typically called periodically (e.g., every 30s)
    and fed into the monitoring dashboard.

    Returns:
        Dictionary containing all current metrics
    """
    # Calculate error rate as percentage of total requests (success + errors)
    total_errors = sum(ERRORS.values())
    total_requests = TRAFFIC + total_errors
    error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0.0

    return {
        "traffic": TRAFFIC,                        # Total successful requests
        "latency_p50": percentile(REQUEST_LATENCIES, 50),  # Median latency
        "latency_p95": percentile(REQUEST_LATENCIES, 95),  # 95th percentile latency
        "latency_p99": percentile(REQUEST_LATENCIES, 99),  # 99th percentile latency
        "avg_cost_usd": round(mean(REQUEST_COSTS), 4) if REQUEST_COSTS else 0.0,
        "total_cost_usd": round(sum(REQUEST_COSTS), 4),
        "tokens_in_total": sum(REQUEST_TOKENS_IN),
        "tokens_out_total": sum(REQUEST_TOKENS_OUT),
        "error_rate_pct": round(error_rate, 2),    # Error rate as percentage
        "error_breakdown": dict(ERRORS),           # Errors by type
        "quality_avg": round(mean(QUALITY_SCORES), 4) if QUALITY_SCORES else 0.0,
    }
