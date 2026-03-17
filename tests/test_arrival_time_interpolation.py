from __future__ import annotations

import math

import numpy as np

from experiments.metrics import _crossing_diagnostic, _phase_lag_seconds, compute_case_analysis


def _stage_rows(series_id: str, values: list[float]) -> list[dict[str, float | str]]:
    return [{'time': float(idx), 'control_id': series_id, 'stage': float(value)} for idx, value in enumerate(values)]


def test_crossing_diagnostic_uses_exact_sample_when_threshold_hits_sample():
    crossing = _crossing_diagnostic(
        np.asarray([0.0, 1.0, 2.0], dtype=float),
        np.asarray([0.0, 0.5, 1.0], dtype=float),
        0.5,
    )
    assert crossing['found_crossing'] is True
    assert crossing['crossing_time_interp'] == 1.0


def test_crossing_diagnostic_linearly_interpolates_between_samples():
    crossing = _crossing_diagnostic(
        np.asarray([0.0, 2.0], dtype=float),
        np.asarray([0.0, 1.0], dtype=float),
        0.25,
    )
    assert crossing['found_crossing'] is True
    assert math.isclose(float(crossing['crossing_time_interp']), 0.5, rel_tol=1.0e-9)


def test_crossing_diagnostic_reports_missing_crossing_without_bucket_snap():
    crossing = _crossing_diagnostic(
        np.asarray([0.0, 1.0, 2.0], dtype=float),
        np.asarray([0.0, 0.1, 0.2], dtype=float),
        0.5,
    )
    assert crossing['found_crossing'] is False
    assert crossing['crossing_time_interp'] == 2.0


def test_case_analysis_reuses_reference_threshold_for_arrival():
    reference = {
        'stage_1d_rows': _stage_rows('mainstem_mid', [0.0, 0.4, 1.0]),
        'stage_2d_rows': _stage_rows('floodplain_probe', [0.0, 0.2, 0.5]),
        'discharge_rows': [
            {'time': 0.0, 'series_id': 'exchange_q_total', 'discharge': 0.0},
            {'time': 1.0, 'series_id': 'exchange_q_total', 'discharge': 1.0},
            {'time': 2.0, 'series_id': 'exchange_q_total', 'discharge': 0.0},
        ],
    }
    analysis = compute_case_analysis(
        case_name='candidate',
        wall_clock_seconds=1.0,
        simulated_duration=2.0,
        exchange_history=[],
        mass_balance_rows=[{'time': 2.0, 'system_mass_error': 0.0, 'system_volume': 1.0}],
        stage_1d_rows=_stage_rows('mainstem_mid', [0.0, 0.6, 0.7]),
        stage_2d_rows=_stage_rows('floodplain_probe', [0.0, 0.3, 0.4]),
        discharge_rows=[
            {'time': 0.0, 'series_id': 'exchange_q_total', 'discharge': 0.0},
            {'time': 1.0, 'series_id': 'exchange_q_total', 'discharge': 1.0},
            {'time': 2.0, 'series_id': 'exchange_q_total', 'discharge': 0.0},
        ],
        reference=reference,
    )
    expected_ref_crossing = 1.1666666666666667
    expected_case_crossing = 0.8333333333333334
    assert math.isclose(
        float(analysis['summary']['arrival_time_diff_vs_reference']),
        expected_case_crossing - expected_ref_crossing,
        rel_tol=1.0e-9,
    )


def test_phase_lag_uses_meaningful_overlap_instead_of_edge_saturation():
    reference = np.asarray([0.0] * 20 + [1.0] * 20 + [0.0] * 20, dtype=float)
    shifted = np.asarray([0.0] * 24 + [1.0] * 20 + [0.0] * 16, dtype=float)
    phase_lag = _phase_lag_seconds(reference, shifted, dt=0.5)
    assert math.isclose(float(phase_lag), 2.0, rel_tol=1.0e-9)
