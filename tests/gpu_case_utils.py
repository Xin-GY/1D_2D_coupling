from __future__ import annotations

from pathlib import Path

from coupling.runtime_env import configure_runtime_environment


configure_runtime_environment(Path('/tmp/1d_2d_coupling_tests'))

import anuga
import cupy as cp


def assert_real_gpu_ready() -> None:
    driver = int(cp.cuda.runtime.driverGetVersion())
    device_count = int(cp.cuda.runtime.getDeviceCount())
    assert driver > 0, f'Expected a visible CUDA driver in direct Python, got driverGetVersion={driver}'
    assert device_count > 0, f'Expected at least one CUDA device, got device_count={device_count}'


def make_real_gpu_domain():
    assert_real_gpu_ready()
    domain = anuga.create_domain_from_regions(
        [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]],
        boundary_tags={'bottom': [0], 'right': [1], 'top': [2], 'left': [3]},
        maximum_triangle_area=4.0,
        minimum_triangle_angle=28.0,
        use_cache=False,
        verbose=False,
    )
    domain.set_name('gpu_test_domain')
    domain.set_minimum_storable_height(0.001)
    domain.set_minimum_allowed_height(0.001)
    domain.set_quantity('elevation', 0.0)
    domain.set_quantity('friction', 0.03, location='centroids')
    domain.set_quantity('stage', 1.0, location='centroids')
    boundary = anuga.Reflective_boundary(domain)
    domain.set_boundary({'left': boundary, 'right': boundary, 'top': boundary, 'bottom': boundary})
    return domain


def make_circle_region(domain, center=(10.0, 10.0), radius=6.0):
    return anuga.Region(domain=domain, center=list(center), radius=float(radius))
