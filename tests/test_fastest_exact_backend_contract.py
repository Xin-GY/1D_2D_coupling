from __future__ import annotations

from pathlib import Path

from experiments.cases import ExperimentCase, prepare_case


def _make_case() -> ExperimentCase:
    return ExperimentCase(
        case_name='fastest_exact_backend_contract',
        coupling_type='mixed',
        scheduler_mode='strict_global_min_dt',
        exchange_interval=None,
        direction='bidirectional',
        waveform='pulse',
        duration=20.0,
        one_d_backend='fastest_exact',
    )


def test_fastest_exact_backend_satisfies_oned_adapter_contract(tmp_path: Path):
    payload = prepare_case(_make_case(), tmp_path / 'case')
    manager = payload['manager']
    one_d = manager.one_d
    network = one_d.network

    required_network_methods = {
        'initialize_for_coupling',
        'predict_cfl_dt',
        'advance_one_step',
        'advance_to',
        'get_total_volume',
        'snapshot',
        'restore',
        'get_river',
    }
    for method_name in required_network_methods:
        assert hasattr(network, method_name), method_name

    river = network.get_river('mainstem')
    required_river_methods = {
        'apply_cellwise_side_inflow',
        'get_total_volume',
        'snapshot',
        'restore',
    }
    for method_name in required_river_methods:
        assert hasattr(river, method_name), method_name

    one_d.initialize()
    initial_time = float(network.current_sim_time)
    requested_dt = float(one_d.predict_cfl_dt())
    snapshot = one_d.snapshot()
    used_dt = float(one_d.advance_one_step(requested_dt))

    assert used_dt > 0.0
    assert abs(float(network.current_sim_time) - (initial_time + used_dt)) < 1.0e-12

    one_d.restore(snapshot)
    assert abs(float(network.current_sim_time) - initial_time) < 1.0e-12
