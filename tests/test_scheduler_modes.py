import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from experiments.cases import ExperimentCase, prepare_case
from coupling.config import SchedulerConfig
from coupling.scheduler import ExchangeScheduler


def test_fixed_interval_event_series_aligns_exactly():
    scheduler = ExchangeScheduler(SchedulerConfig(mode='fixed_interval', exchange_interval=2.5))
    assert scheduler.event_series(0.0, 10.0) == [2.5, 5.0, 7.5, 10.0]


def test_yield_schedule_uses_union_without_drift():
    scheduler = ExchangeScheduler(
        SchedulerConfig(
            mode='yield_schedule',
            one_d_yields=[1.0, 3.0, 6.0],
            two_d_yields=[2.0, 3.0, 5.0],
        )
    )
    assert scheduler.event_series(0.0, 8.0) == [1.0, 2.0, 3.0, 5.0, 6.0, 8.0]


def test_strict_global_min_dt_uses_smaller_cfl():
    scheduler = ExchangeScheduler(SchedulerConfig(mode='strict_global_min_dt'))
    next_t = scheduler.next_exchange_time(1.0, 5.0, one_d_dt=0.7, two_d_dt=0.4)
    assert next_t == 1.4


def test_fixed_interval_next_exchange_reaches_final_time():
    scheduler = ExchangeScheduler(SchedulerConfig(mode='fixed_interval', exchange_interval=1.5))
    current = 0.0
    end = 5.0
    times = []
    while current < end - scheduler.time_eps:
        current = scheduler.next_exchange_time(current, end)
        times.append(current)
    assert times == [1.5, 3.0, 4.5, 5.0]


@pytest.mark.parametrize(
    ('mode', 'exchange_interval'),
    [
        ('strict_global_min_dt', None),
        ('yield_schedule', None),
        ('fixed_interval', 2.0),
    ],
)
def test_real_gpu_scheduler_modes_reach_exact_end_time(tmp_path: Path, mode: str, exchange_interval: float | None):
    output_path = tmp_path / f'scheduler_{mode}.json'
    script = textwrap.dedent(
        """
        import json
        import sys
        from pathlib import Path

        from experiments.cases import ExperimentCase, prepare_case

        mode = sys.argv[1]
        interval_arg = sys.argv[2]
        output_path = Path(sys.argv[3])
        exchange_interval = None if interval_arg == 'None' else float(interval_arg)
        case = ExperimentCase(
            case_name=f'test_{mode}',
            scheduler_mode=mode,
            exchange_interval=exchange_interval,
            coupling_type='mixed',
            direction='bidirectional',
            waveform='pulse',
            duration=6.0,
            one_d_yields=[2.0, 4.0, 6.0],
            two_d_yields=[3.0, 6.0],
        )
        prepared = prepare_case(case, output_path.parent / case.case_name)
        manager = prepared['manager']
        manager.run()
        output_path.write_text(
            json.dumps(
                {
                    'one_d_time': manager.one_d.network.current_sim_time,
                    'two_d_time': manager.two_d.domain.relative_time,
                    'dt_history_count': len(manager.dt_history),
                }
            ),
            encoding='utf-8',
        )
        """
    )
    subprocess.run(
        [
            sys.executable,
            '-c',
            script,
            mode,
            'None' if exchange_interval is None else str(exchange_interval),
            str(output_path),
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    payload = json.loads(output_path.read_text(encoding='utf-8'))
    assert abs(float(payload['one_d_time']) - 6.0) < 1.0e-9
    assert abs(float(payload['two_d_time']) - 6.0) < 1.0e-9
    assert int(payload['dt_history_count']) > 0
