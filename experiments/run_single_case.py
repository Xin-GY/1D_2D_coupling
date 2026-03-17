from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from coupling.runtime_env import repair_anuga_editable_build_env

repair_anuga_editable_build_env()

from experiments.chapter_cases import generate_all_chapter_cases
from experiments.io import read_json
from experiments.cases import generate_all_cases, prepare_case
from experiments.chapter_cases import prepare_chapter_case
from experiments.io import ensure_dir
from experiments.runner import run_case
from experiments.chapter_runner import run_chapter_case
from experiments.test7_data import Test7DataProvenance, resolve_test7_data


def _find_case(case_name: str):
    for case in generate_all_cases():
        if case.case_name == case_name:
            return case
    raise KeyError(f'Unknown experiment case: {case_name}')


def _chapter_provenance(path: str | None, output_root: Path) -> Test7DataProvenance:
    if path is not None:
        payload = read_json(Path(path))
        return Test7DataProvenance(**payload)
    return resolve_test7_data(output_root / 'logs' / 'test7_cache', allow_download=False)


def _find_chapter_case(case_name: str, profile: str, provenance: Test7DataProvenance):
    for case in generate_all_chapter_cases(provenance, profile=profile):
        if case.case_name == case_name:
            return case
    raise KeyError(f'Unknown chapter experiment case: {case_name}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Run one coupling sweep case in an isolated process.')
    parser.add_argument('case_name')
    parser.add_argument('--output-root', default='artifacts/coupling_sweep')
    parser.add_argument('--registry', default='legacy', choices=['legacy', 'chapter'])
    parser.add_argument('--profile', default='paper', choices=['paper', 'test'])
    parser.add_argument('--chapter-provenance')
    parser.add_argument('--one-d-backend')
    parser.add_argument('--mesh-variant')
    args = parser.parse_args()

    output_root = ensure_dir(Path(args.output_root))
    if args.registry == 'legacy':
        case = _find_case(args.case_name)
        if args.one_d_backend is not None:
            case = replace(case, one_d_backend=args.one_d_backend)
        run_case(case, output_root, prepare_case, reference=None)
        return
    provenance = _chapter_provenance(args.chapter_provenance, output_root)
    case = _find_chapter_case(args.case_name, args.profile, provenance)
    overrides = {}
    if args.one_d_backend is not None:
        overrides['one_d_backend'] = args.one_d_backend
    if args.mesh_variant is not None:
        overrides['mesh_variant'] = args.mesh_variant
    if overrides:
        case = replace(case, **overrides)
    run_chapter_case(case, output_root, prepare_chapter_case, reference=None)


if __name__ == '__main__':
    main()
