"""
Pipeline Metrics
Tracks latency, success rates, and usage patterns for each pipeline stage.
"""

import time
import logging
from collections import defaultdict, deque
from typing import Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class StageMetrics:
    name: str
    call_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    latency_samples: deque = field(default_factory=lambda: deque(maxlen=100))

    @property
    def avg_latency_ms(self) -> float:
        if not self.latency_samples:
            return 0.0
        return sum(self.latency_samples) / len(self.latency_samples)

    @property
    def p95_latency_ms(self) -> float:
        if not self.latency_samples:
            return 0.0
        sorted_samples = sorted(self.latency_samples)
        idx = int(len(sorted_samples) * 0.95)
        return sorted_samples[min(idx, len(sorted_samples) - 1)]

    @property
    def success_rate(self) -> float:
        if self.call_count == 0:
            return 1.0
        return (self.call_count - self.error_count) / self.call_count


class PipelineMetrics:
    """Track and report pipeline performance metrics"""

    def __init__(self):
        self._stages: Dict[str, StageMetrics] = {}
        self._session_latencies: deque = deque(maxlen=1000)
        self._total_sessions: int = 0
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._start_time: float = time.time()

        # Initialize stage trackers
        for stage in [
            "stt", "language_detection", "translation", "nlp",
            "sentiment", "skill_manager", "action_handler",
            "response_generation", "response_translation", "tts"
        ]:
            self._stages[stage] = StageMetrics(name=stage)

    def record_stage(self, stage: str, duration_seconds: float):
        """Record a stage completion"""
        latency_ms = duration_seconds * 1000
        if stage not in self._stages:
            self._stages[stage] = StageMetrics(name=stage)

        metrics = self._stages[stage]
        metrics.call_count += 1
        metrics.total_latency_ms += latency_ms
        metrics.latency_samples.append(latency_ms)

    def record_error(self, stage: str):
        """Record an error in a stage"""
        if stage in self._stages:
            self._stages[stage].error_count += 1
        self._error_counts[stage] += 1

    def record_session(self, ctx: Any):
        """Record a completed pipeline session"""
        self._total_sessions += 1
        self._session_latencies.append(ctx.latency_ms)

        if ctx.error:
            self.record_error("pipeline_cycle")

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        uptime_hours = (time.time() - self._start_time) / 3600

        # Session stats
        if self._session_latencies:
            avg_latency = sum(self._session_latencies) / len(self._session_latencies)
            sorted_latencies = sorted(self._session_latencies)
            p95_idx = int(len(sorted_latencies) * 0.95)
            p95_latency = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]
        else:
            avg_latency = 0.0
            p95_latency = 0.0

        return {
            "uptime_hours": round(uptime_hours, 2),
            "total_sessions": self._total_sessions,
            "avg_end_to_end_latency_ms": round(avg_latency, 1),
            "p95_end_to_end_latency_ms": round(p95_latency, 1),
            "stages": {
                name: {
                    "calls": m.call_count,
                    "errors": m.error_count,
                    "avg_latency_ms": round(m.avg_latency_ms, 1),
                    "p95_latency_ms": round(m.p95_latency_ms, 1),
                    "success_rate": round(m.success_rate, 3),
                }
                for name, m in self._stages.items()
                if m.call_count > 0
            }
        }

    def reset(self):
        """Reset all metrics"""
        for metrics in self._stages.values():
            metrics.call_count = 0
            metrics.error_count = 0
            metrics.total_latency_ms = 0.0
            metrics.latency_samples.clear()
        self._session_latencies.clear()
        self._total_sessions = 0
        self._error_counts.clear()
        self._start_time = time.time()
