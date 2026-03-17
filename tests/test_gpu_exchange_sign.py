from coupling.adapters_anuga_gpu import TwoDAnugaGpuAdapter
from tests.gpu_case_utils import assert_real_gpu_ready, make_circle_region, make_real_gpu_domain


def test_negative_q_uses_gpu_inlets_apply_and_not_legacy_path(monkeypatch):
    assert_real_gpu_ready()
    domain = make_real_gpu_domain()
    adapter = TwoDAnugaGpuAdapter(domain=domain, multiprocessor_mode=4)
    adapter.initialize_gpu()
    region = make_circle_region(domain)
    adapter.register_exchange_region('lat', region, mode='fast')

    legacy_calls = {'count': 0}

    def forbidden_legacy(*args, **kwargs):
        legacy_calls['count'] += 1
        raise AssertionError('legacy apply_inlets_gpu must never be called in coupling path')

    monkeypatch.setattr(domain.gpu_interface, 'apply_inlets_gpu', forbidden_legacy, raising=False)
    domain.fractional_step_volume_integral = 0.0
    before = adapter.get_total_volume()

    adapter.set_exchange_Q('lat', -2.0)
    domain.timestep = 1.0
    domain.relative_time = 0.0
    domain.gpu_interface.set_gpu_update_timestep(domain.timestep)
    applied_dv = domain.gpu_inlets.apply()
    after = adapter.get_total_volume()

    assert applied_dv < 0.0
    assert after < before
    assert domain.fractional_step_volume_integral < 0.0
    assert legacy_calls['count'] == 0


def test_negative_q_mass_accounting_matches_volume_change():
    assert_real_gpu_ready()
    domain = make_real_gpu_domain()
    adapter = TwoDAnugaGpuAdapter(domain=domain, multiprocessor_mode=4)
    adapter.initialize_gpu()
    region = make_circle_region(domain)
    adapter.register_exchange_region('lat', region, mode='fast')

    domain.fractional_step_volume_integral = 0.0
    before = adapter.get_total_volume()

    adapter.set_exchange_Q('lat', -1.5)
    domain.timestep = 2.0
    domain.relative_time = 0.0
    domain.gpu_interface.set_gpu_update_timestep(domain.timestep)
    applied_dv = domain.gpu_inlets.apply()
    after = adapter.get_total_volume()

    volume_delta = after - before
    assert applied_dv < 0.0
    assert volume_delta < 0.0
    assert abs(domain.fractional_step_volume_integral - applied_dv) < 1.0e-9
    assert abs(volume_delta - applied_dv) < 1.0e-6
