from __future__ import annotations

import argparse
from pathlib import Path

from experiments.cases import generate_case_matrix, prepare_case
from experiments.io import ensure_dir
from experiments.runner import run_case


def _find_case(case_name: str):
    for case in generate_case_matrix():
        if case.case_name == case_name:
            return case
    raise KeyError(f'Unknown experiment case: {case_name}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Run one coupling sweep case in an isolated process.')
    parser.add_argument('case_name')
    parser.add_argument('--output-root', default='artifacts/coupling_sweep')
    args = parser.parse_args()

    case = _find_case(args.case_name)
    output_root = ensure_dir(Path(args.output_root))
    run_case(case, output_root, prepare_case, reference=None)


if __name__ == '__main__':
    main()
