from __future__ import annotations

from dataclasses import dataclass

from .config import SchedulerConfig

TIME_EPS = 1.0e-12


@dataclass(slots=True)
class ExchangeScheduler:
    config: SchedulerConfig

    def __post_init__(self) -> None:
        if self.config.mode not in {'strict_global_min_dt', 'yield_schedule', 'fixed_interval'}:
            raise ValueError(f'Unsupported scheduler mode: {self.config.mode}')

    @property
    def time_eps(self) -> float:
        return float(self.config.time_eps or TIME_EPS)

    def _normalize_events(self, events: list[float], start_time: float, end_time: float) -> list[float]:
        clean = []
        for event in events:
            event_f = float(event)
            if event_f <= start_time + self.time_eps or event_f > end_time + self.time_eps:
                continue
            clean.append(event_f)
        clean.append(float(end_time))
        return sorted({round(event, 12) for event in clean})

    def event_series(self, start_time: float, end_time: float) -> list[float]:
        mode = self.config.mode
        start = float(start_time)
        end = float(end_time)
        if mode == 'fixed_interval':
            interval = float(self.config.exchange_interval or 0.0)
            if interval <= 0.0:
                raise ValueError('fixed_interval 模式必须提供正的 exchange_interval')
            events = []
            t = start + interval
            while t < end - self.time_eps:
                events.append(t)
                t += interval
            return self._normalize_events(events, start, end)
        if mode == 'yield_schedule':
            union_events = list(self.config.one_d_yields) + list(self.config.two_d_yields)
            return self._normalize_events(union_events, start, end)
        return self._normalize_events([], start, end)

    def next_exchange_time(
        self,
        current_time: float,
        end_time: float,
        one_d_dt: float | None = None,
        two_d_dt: float | None = None,
    ) -> float:
        current = float(current_time)
        end = float(end_time)
        if self.config.mode == 'strict_global_min_dt':
            if one_d_dt is None or two_d_dt is None:
                raise ValueError('strict_global_min_dt 模式必须提供 one_d_dt 和 two_d_dt')
            return min(current + float(one_d_dt), current + float(two_d_dt), end)

        for event in self.event_series(current, end):
            if event > current + self.time_eps:
                return float(event)
        return float(end)
