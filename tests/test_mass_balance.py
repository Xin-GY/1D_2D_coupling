from pathlib import Path

from coupling.config import CouplingConfig, LateralLinkConfig, SchedulerConfig
from coupling.links import LateralWeirLink
from coupling.manager import CouplingManager

from tests.test_frontal_coupling import FakeOneDAdapter, FakeTwoDAdapter


def test_manager_keeps_total_volume_balanced(tmp_path: Path):
    one_d = FakeOneDAdapter(stage=2.0, discharge=0.0, regime='sub', volume=100.0)
    two_d = FakeTwoDAdapter(boundary_stage=0.5, volume=40.0)
    lateral_link = LateralWeirLink.from_config(
        LateralLinkConfig(
            link_id='lat',
            river_name='river',
            region_id='lat_region',
            river_cells=[2],
            segment_lengths=[1.0],
            crest_levels=[0.0],
            discharge_coefficient=1.0,
            two_d_sample=[[0]],
        )
    )
    config = CouplingConfig(
        start_time=0.0,
        end_time=2.0,
        scheduler=SchedulerConfig(mode='fixed_interval', exchange_interval=1.0),
        diagnostics_dir=str(tmp_path),
    )
    manager = CouplingManager(one_d=one_d, two_d=two_d, config=config, lateral_links=[lateral_link], frontal_links=[])
    manager.run()
    total_initial = 140.0
    total_final = one_d.get_total_volume() + two_d.get_total_volume()
    assert abs(total_final - total_initial) < 1.0e-9
    assert (tmp_path / 'coupling_exchange_history.csv').exists()
    assert (tmp_path / 'coupling_mass_balance.csv').exists()
    assert (tmp_path / 'coupling_dt_history.csv').exists()
