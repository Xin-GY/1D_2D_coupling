from __future__ import annotations

from pathlib import Path

import pytest

from coupling.adapters_anuga_gpu import TwoDAnugaGpuAdapter
from tests.gpu_case_utils import assert_real_gpu_ready, make_circle_region, make_real_gpu_domain


def test_adapter_rejects_non_fast_mode():
    assert_real_gpu_ready()
    domain = make_real_gpu_domain()
    adapter = TwoDAnugaGpuAdapter(domain=domain, multiprocessor_mode=4)
    adapter.initialize_gpu()
    with pytest.raises(ValueError, match='fast mode'):
        adapter.register_exchange_region('lat', make_circle_region(domain), mode='cpu_compatible')


def test_default_inlet_mode_is_fast_and_used_for_registration():
    assert_real_gpu_ready()
    domain = make_real_gpu_domain()
    adapter = TwoDAnugaGpuAdapter(domain=domain, multiprocessor_mode=4)
    adapter.initialize_gpu()
    adapter.register_exchange_region('lat', make_circle_region(domain))
    inlet = adapter._exchange_regions['lat']
    assert getattr(inlet, 'mode', None) == 'fast'


def test_example_and_demo_do_not_reference_cpu_compatible_mode():
    targets = [
        Path('examples/islam_1d2d_coupled_demo.py'),
        Path('demo/demo.py'),
        Path('coupling/adapters_anuga_gpu.py'),
    ]
    for path in targets:
        text = path.read_text(encoding='utf-8')
        assert 'cpu_compatible' not in text
