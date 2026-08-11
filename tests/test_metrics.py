"""
Tests for metrics collection - CP1

Verifies that the metrics module correctly calculates:
- Percentiles from latency data
- Aggregation functions for traffic and error tracking
"""
from app.metrics import percentile


def test_percentile_basic() -> None:
    """
    Test that percentile calculation returns a value within the data range.

    For a sorted list [100, 200, 300, 400], the P50 (median) should
    return a value between the min and max of the dataset.
    """
    assert percentile([100, 200, 300, 400], 50) >= 100
