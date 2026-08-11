from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .incidents import STATE


REQUIRED_QUERY_FIELDS = {"user_id", "session_id", "feature", "message"}


@dataclass(frozen=True)
class ChallengeConfig:
    cohort: str
    challenge_id: str
    incident: str
    seed: int
    affected_feature: str
    latency_threshold_ms: int
    queries: tuple[dict[str, str], ...]


def _require_text(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} phải là chuỗi không rỗng")
    return value.strip()


def _require_int(payload: dict[str, Any], field: str, *, positive: bool = False) -> int:
    value = payload.get(field)
    if not isinstance(value, int) or (positive and value <= 0):
        suffix = "số nguyên dương" if positive else "số nguyên"
        raise ValueError(f"{field} phải là {suffix}")
    return value


def _require_queries(payload: dict[str, Any]) -> list[dict[str, str]]:
    raw_queries = payload.get("queries")
    if not isinstance(raw_queries, list) or not raw_queries:
        raise ValueError("queries phải là danh sách không rỗng")

    queries: list[dict[str, str]] = []
    for index, query in enumerate(raw_queries):
        if not isinstance(query, dict) or not REQUIRED_QUERY_FIELDS.issubset(query):
            raise ValueError(f"queries[{index}] thiếu trường bắt buộc")
        normalized = {field: query[field] for field in REQUIRED_QUERY_FIELDS}
        if any(not isinstance(value, str) or not value.strip() for value in normalized.values()):
            raise ValueError(f"queries[{index}] phải chứa các chuỗi không rỗng")
        queries.append(normalized)
    return queries


def _load_payload(challenge_path: Path) -> dict[str, Any]:
    if not challenge_path.exists():
        raise FileNotFoundError(
            f"{challenge_path} chưa được Lab Coach release. "
            "Hãy tiếp tục phần practice và chờ thông báo."
        )

    try:
        payload = json.loads(challenge_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("challenge.json không phải JSON hợp lệ") from exc

    if not isinstance(payload, dict):
        raise ValueError("challenge.json phải chứa một JSON object")
    return payload


def load_challenge(path: str | Path = "config/challenge.json") -> ChallengeConfig:
    payload = _load_payload(Path(path))

    cohort = _require_text(payload, "cohort")
    if cohort not in {"K3", "K4"}:
        raise ValueError("cohort phải là K3 hoặc K4")

    incident = _require_text(payload, "incident")
    if incident not in STATE:
        raise ValueError(f"incident không hợp lệ: {incident}")

    seed = _require_int(payload, "seed")
    latency_threshold_ms = _require_int(payload, "latency_threshold_ms", positive=True)
    queries = _require_queries(payload)

    return ChallengeConfig(
        cohort=cohort,
        challenge_id=_require_text(payload, "challenge_id"),
        incident=incident,
        seed=seed,
        affected_feature=_require_text(payload, "affected_feature"),
        latency_threshold_ms=latency_threshold_ms,
        queries=tuple(queries),
    )


def resolve_incident(
    explicit_scenario: str | None,
    challenge_path: str | Path = "config/challenge.json",
) -> str:
    if explicit_scenario is not None:
        if explicit_scenario not in STATE:
            raise ValueError(f"incident không hợp lệ: {explicit_scenario}")
        return explicit_scenario
    return load_challenge(challenge_path).incident


def ordered_queries(challenge: ChallengeConfig) -> list[dict[str, str]]:
    queries = [dict(query) for query in challenge.queries]
    random.Random(challenge.seed).shuffle(queries)
    return queries
