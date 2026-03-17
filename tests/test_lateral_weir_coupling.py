import math

from coupling.config import LateralLinkConfig
from coupling.links import LateralWeirLink
from demo.river_for_net import River


def make_link() -> LateralWeirLink:
    return LateralWeirLink.from_config(
        LateralLinkConfig(
            link_id='lat1',
            river_name='river',
            region_id='region',
            river_cells=[2, 3],
            segment_lengths=[5.0, 7.0],
            crest_levels=[1.0, 1.0],
            discharge_coefficient=0.8,
            two_d_sample=[0, 1],
        )
    )


def test_lateral_weir_positive_flow_matches_formula():
    link = make_link()
    q = link.compute_exchange([2.0, 1.8], [0.5, 1.0])
    expected = (
        0.8 * 5.0 * math.sqrt(2.0 * 9.81) * (1.0 ** 1.5)
        + 0.8 * 7.0 * math.sqrt(2.0 * 9.81) * (0.8 ** 1.5)
    )
    assert math.isclose(q, expected, rel_tol=1.0e-9)
    assert len(link.last_segment_Q) == 2
    assert link.last_segment_Q[0] > 0.0 and link.last_segment_Q[1] > 0.0


def test_lateral_weir_negative_flow_reverses_sign():
    link = make_link()
    q = link.compute_exchange([0.6, 0.7], [1.4, 1.6])
    assert q < 0.0
    assert all(val <= 0.0 for val in link.last_segment_Q)


def test_lateral_weir_stays_dry_when_crest_above_water():
    link = LateralWeirLink.from_config(
        LateralLinkConfig(
            link_id='lat2',
            river_name='river',
            region_id='region',
            river_cells=[2],
            segment_lengths=[10.0],
            crest_levels=[5.0],
            discharge_coefficient=1.0,
        )
    )
    q = link.compute_exchange([1.0], [1.1])
    assert q == 0.0
    record = link.finalize_exchange(10.0, 2.0, 'fixed_interval')
    assert record['dV_exchange'] == 0.0
    assert record['cumulative_dV'] == 0.0


def test_positive_cellwise_side_inflow_increases_river_volume(tmp_path):
    river = River(
        river_data={
            'cell_num': 2,
            'pos': [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [20.0, 0.0, 0.0]],
            'section_name': ['s1', 's2'],
        },
        section_data={
            's1': [[0.0, 4.0], [0.0, 0.0], [4.0, 0.0], [4.0, 4.0]],
            's2': [[0.0, 4.0], [0.0, 0.0], [4.0, 0.0], [4.0, 4.0]],
        },
        section_pos={'s1': [5.0, 0.0], 's2': [15.0, 0.0]},
        sim_data={
            'model_name': 'river_sign_test',
            'sim_start_time': '2024-01-01 00:00:00',
            'sim_end_time': '2024-01-01 00:00:10',
            'time_step': 1.0,
            'output_path': str(tmp_path),
            'CFL': 0.3,
            'n': 0.03,
        },
    )
    river.Set_init_water_level(1.0)
    river.initialize_for_coupling(save_outputs=False)
    volume_before = river.get_total_volume()
    river.apply_cellwise_side_inflow([1], [0.5])
    river.advance_one_step(0.1)
    volume_after = river.get_total_volume()
    assert volume_after > volume_before
