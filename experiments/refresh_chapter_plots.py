from __future__ import annotations

import argparse
from pathlib import Path

from coupling.runtime_env import configure_runtime_environment


configure_runtime_environment(Path('/tmp/1d_2d_coupling_refresh_chapter_plots'))

from experiments.chapter_plotting import refresh_chapter_plot_outputs
from experiments.io import read_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Refresh chapter plots and plot QA artifacts without rerunning simulations.')
    parser.add_argument('--output-root', default=str(Path('artifacts') / 'chapter_coupling_analysis'))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)
    figure_manifest = read_csv(output_root / 'summaries' / 'figure_manifest.csv')
    plot_specs = [
        {
            'figure_id': row['figure_id'],
            'module_name': row['script_path'].replace('/', '.').removesuffix('.py'),
            'output_png_path': row['output_png_path'],
            'input_data_paths': row['input_data_paths'],
            'caption_draft_cn': row['caption_draft_cn'],
            'caption_draft_en': row['caption_draft_en'],
            'chapter_section': row['chapter_section'],
        }
        for row in figure_manifest
    ]
    refresh_chapter_plot_outputs(output_root, plot_specs)


if __name__ == '__main__':
    main()
