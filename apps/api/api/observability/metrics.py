from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass(slots=True)
class Counter:
    name: str
    labels: tuple[str, ...]
    _value: int = 0
    _label_values: dict[tuple[str, ...], int] = field(
        default_factory=lambda: defaultdict(int),
    )

    def inc(self, amount: int = 1, **labels: str) -> None:
        if labels:
            key = tuple(labels.get(lbl, "") for lbl in self.labels)
            self._label_values[key] += amount
        self._value += amount

    @property
    def value(self) -> int:
        return self._value

    def snapshot(self) -> dict[str, Any]:
        result: dict[str, Any] = {"name": self.name, "value": self._value}
        if self._label_values:
            result["by_labels"] = [
                {
                    "labels": dict(zip(self.labels, key, strict=False)),
                    "value": val,
                }
                for key, val in sorted(self._label_values.items())
            ]
        return result


@dataclass(slots=True)
class Gauge:
    name: str
    _value: int = 0

    def set(self, value: int) -> None:
        self._value = value

    def inc(self, amount: int = 1) -> None:
        self._value += amount

    def dec(self, amount: int = 1) -> None:
        self._value -= amount

    @property
    def value(self) -> int:
        return self._value

    def snapshot(self) -> dict[str, Any]:
        return {"name": self.name, "value": self._value}


class MetricsCollector:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}

        self._init_default_metrics()

    def _init_default_metrics(self) -> None:
        c = self._counters
        c["workflow_started"] = Counter(
            "workflow_started",
            ("workflow_name",),
        )
        c["workflow_succeeded"] = Counter(
            "workflow_succeeded",
            ("workflow_name",),
        )
        c["workflow_failed"] = Counter(
            "workflow_failed",
            ("workflow_name",),
        )
        c["claim_created"] = Counter("claim_created", ())
        c["claim_reclaimed"] = Counter("claim_reclaimed", ())
        c["claim_released"] = Counter("claim_released", ())
        c["executor_dispatched"] = Counter(
            "executor_dispatched",
            ("executor",),
        )
        c["executor_succeeded"] = Counter(
            "executor_succeeded",
            ("executor",),
        )
        c["executor_retryable_failure"] = Counter(
            "executor_retryable_failure",
            ("executor",),
        )
        c["executor_terminal_failure"] = Counter(
            "executor_terminal_failure",
            ("executor",),
        )
        c["approval_requested"] = Counter(
            "approval_requested",
            ("approval_type",),
        )
        c["approval_resolved"] = Counter(
            "approval_resolved",
            ("approval_type", "decision"),
        )
        c["memory_write_attempted"] = Counter(
            "memory_write_attempted",
            ("provider",),
        )
        c["memory_write_accepted"] = Counter(
            "memory_write_accepted",
            ("provider",),
        )
        c["memory_write_rejected"] = Counter(
            "memory_write_rejected",
            ("provider", "reason"),
        )
        c["memory_recall_requested"] = Counter(
            "memory_recall_requested",
            ("provider",),
        )
        c["memory_recall_hit"] = Counter(
            "memory_recall_hit",
            ("provider",),
        )
        c["eval_suite_run"] = Counter(
            "eval_suite_run",
            ("suite",),
        )
        c["eval_case_passed"] = Counter(
            "eval_case_passed",
            ("suite", "case_id"),
        )
        c["eval_case_failed"] = Counter(
            "eval_case_failed",
            ("suite", "case_id"),
        )
        self._gauges["approval_pending"] = Gauge("approval_pending")

    def counter(self, name: str) -> Counter:
        with self._lock:
            return self._counters[name]

    def gauge(self, name: str) -> Gauge:
        with self._lock:
            return self._gauges[name]

    def inc_counter(self, name: str, amount: int = 1, **labels: str) -> None:
        with self._lock:
            self._counters[name].inc(amount, **labels)

    def set_gauge(self, name: str, value: int) -> None:
        with self._lock:
            self._gauges[name].set(value)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "counters": [c.snapshot() for c in self._counters.values()],
                "gauges": [g.snapshot() for g in self._gauges.values()],
            }


_metrics: MetricsCollector | None = None


def get_metrics() -> MetricsCollector:
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics
