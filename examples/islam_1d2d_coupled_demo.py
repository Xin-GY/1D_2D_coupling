from __future__ import annotations

from pathlib import Path

from coupling.adapters_anuga_gpu import TwoDAnugaGpuAdapter
from coupling.adapters_rivernet import OneDNetworkAdapter
from coupling.config import CouplingConfig, FrontalLinkConfig, LateralLinkConfig, MeshRefinementConfig, SchedulerConfig
from coupling.links import FrontalBoundaryLink, LateralWeirLink
from coupling.manager import CouplingManager
from coupling.mesh_builder import RiverAwareMeshBuilder
from coupling.runtime_env import configure_runtime_environment
from demo.Rivernet import Rivernet


def build_islam_like_topology(output_path: str):
    model_data = {
        'model_name': 'coupled_demo',
        'sim_start_time': '2024-01-01 00:00:00',
        'sim_end_time': '2024-01-01 00:10:00',
        'time_step': 60,
        'output_path': output_path,
        'CFL': 0.3,
    }
    river_data = {
        'cell_num': 8,
        'pos': [[i * 50.0, 0.0, 1.2 - 0.02 * i] for i in range(9)],
        'section_name': [f'se{i + 1}' for i in range(8)],
    }
    section_data = {
        name: [[0.0, 4.0], [0.0, 0.0], [8.0, 0.0], [8.0, 4.0]]
        for name in river_data['section_name']
    }
    section_pos = {
        name: [25.0 + idx * 50.0, 0.0]
        for idx, name in enumerate(river_data['section_name'])
    }
    topology = {
        ('n1', 'n2'): {
            'name': 'mainstem',
            'river_data': river_data,
            'section_data': section_data,
            'section_pos': section_pos,
            'model_data': model_data,
            'manning': 0.025,
        }
    }
    return topology, model_data


def build_two_d_domain(mesh_filename: Path):
    configure_runtime_environment()
    import anuga

    builder = RiverAwareMeshBuilder(
        MeshRefinementConfig(
            maximum_triangle_area=50.0,
            channel_exclusion_half_width=3.0,
            river_refinement_half_width=12.0,
            river_refinement_area=16.0,
            frontal_refinement_half_width=8.0,
            frontal_refinement_area=9.0,
            lateral_region_half_width=8.0,
            lateral_region_area=9.0,
        )
    )
    mesh = builder.build(
        floodplain_polygon=[[0.0, -40.0], [400.0, -40.0], [400.0, 40.0], [0.0, 40.0]],
        centerline=[[0.0, 0.0], [400.0, 0.0]],
        direct_connection_lines={'front': [[400.0, -10.0], [400.0, 10.0]]},
        lateral_links={'lateral_demo': [[150.0, 10.0], [250.0, 10.0]]},
    )
    boundary_tags = {'bottom': [0], 'front_tag': [1], 'top': [2], 'left': [3]}
    domain = anuga.create_domain_from_regions(
        mesh.bounding_polygon,
        boundary_tags=boundary_tags,
        maximum_triangle_area=50.0,
        mesh_filename=str(mesh_filename),
        interior_regions=mesh.interior_regions,
        interior_holes=mesh.interior_holes,
        breaklines=mesh.breaklines,
        minimum_triangle_angle=28.0,
        use_cache=False,
        verbose=False,
    )
    domain.set_name('islam_1d2d_coupled_demo')
    domain.set_minimum_storable_height(0.001)
    domain.set_minimum_allowed_height(0.001)
    domain.set_quantity('elevation', lambda x, y: 0.2 if y > 0.0 else 0.0)
    domain.set_quantity('friction', 0.03, location='centroids')
    domain.set_quantity('stage', 0.8, location='centroids')
    br = anuga.Reflective_boundary(domain)
    domain.set_boundary({'left': br, 'top': br, 'bottom': br, 'front_tag': anuga.Transmissive_boundary(domain)})
    return domain, mesh


def main() -> None:
    configure_runtime_environment()
    script_dir = Path(__file__).resolve().parent
    output_dir = script_dir.parent / 'artifacts' / 'examples' / 'islam_1d2d_coupled_demo'
    output_dir.mkdir(parents=True, exist_ok=True)

    topology, model_data = build_islam_like_topology(str(output_dir))
    network = Rivernet(topology, model_data, verbos=False)
    network.set_boundary('n1', 'flow', 2.5)
    network.set_boundary('n2', 'fix_level', 0.9)

    mesh_path = output_dir / 'islam_1d2d_mesh.msh'
    domain, mesh = build_two_d_domain(mesh_path)

    one_d = OneDNetworkAdapter(network)
    two_d = TwoDAnugaGpuAdapter(domain, multiprocessor_mode=1)
    two_d.initialize_gpu()
    two_d.register_exchange_region('lateral_demo', mesh.lateral_exchange_regions['lateral_demo'], mode='fast')

    lateral = LateralWeirLink.from_config(
        LateralLinkConfig(
            link_id='lateral_demo',
            river_name='mainstem',
            region_id='lateral_demo',
            river_cells=[3, 4, 5],
            segment_lengths=[30.0, 30.0, 30.0],
            crest_levels=[0.9, 0.9, 0.9],
            discharge_coefficient=0.7,
            two_d_sample=[mesh.lateral_exchange_regions['lateral_demo']] * 3,
        )
    )
    frontal = FrontalBoundaryLink.from_config(
        FrontalLinkConfig(
            link_id='front',
            river_name='mainstem',
            river_boundary_side='right',
            river_boundary_node='n2',
            two_d_boundary_tag='front_tag',
            boundary_length=20.0,
            outward_normal=(1.0, 0.0),
            max_iter=1,
        )
    )
    manager = CouplingManager(
        one_d=one_d,
        two_d=two_d,
        config=CouplingConfig(
            start_time=0.0,
            end_time=120.0,
            scheduler=SchedulerConfig(mode='fixed_interval', exchange_interval=20.0),
            diagnostics_dir=str(output_dir),
        ),
        lateral_links=[lateral],
        frontal_links=[frontal],
    )
    manager.run()
    print(f'Coupled demo finished. Diagnostics written to {output_dir}')


if __name__ == '__main__':
    main()
