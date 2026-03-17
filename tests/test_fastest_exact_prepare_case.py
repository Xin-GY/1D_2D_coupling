from __future__ import annotations

from pathlib import Path

from dataclasses import replace

from experiments.cases import generate_all_cases, prepare_case
from experiments.chapter_cases import generate_small_mechanism_cases, prepare_chapter_case


def test_legacy_prepare_case_can_switch_to_fastest_exact_backend(tmp_path: Path):
    case = next(c for c in generate_all_cases() if c.case_name == 'mixed_bidirectional_pulse_strict_global_min_dt')
    case = replace(case, one_d_backend='fastest_exact')
    payload = prepare_case(case, tmp_path / 'legacy_case')
    network = payload['manager'].one_d.network
    assert type(network).__module__.startswith('fastest_exact_handoff.source.handoff_network_model_20260312')
    assert type(network).__name__ == 'Rivernet'


def test_chapter_prepare_case_defaults_to_fastest_exact_backend(tmp_path: Path):
    case = next(c for c in generate_small_mechanism_cases(profile='test') if c.case_name == 'frontal_basin_fill_strict_global_min_dt')
    payload = prepare_chapter_case(case, tmp_path / 'chapter_case')
    network = payload['manager'].one_d.network
    assert case.one_d_backend == 'fastest_exact'
    assert type(network).__module__.startswith('fastest_exact_handoff.source.handoff_network_model_20260312')
    assert type(network).__name__ == 'Rivernet'
