from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from coupling.runtime_env import configure_runtime_environment


configure_runtime_environment(Path('/tmp/1d_2d_coupling_tests'))


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_python_module(*args: str) -> None:
    subprocess.run(
        [
            sys.executable,
            '-u',
            '-m',
            *args,
        ],
        check=True,
        cwd=REPO_ROOT,
    )


@pytest.fixture(scope='session')
def coupling_sweep_artifacts(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output_root = tmp_path_factory.mktemp('coupling_sweep') / 'coupling_sweep'
    _run_python_module('experiments.run_coupling_sweep', '--suite', 'legacy', '--output-root', str(output_root))
    return output_root


@pytest.fixture(scope='session')
def chapter_analysis_artifacts(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output_root = tmp_path_factory.mktemp('chapter_analysis') / 'chapter_coupling_analysis'
    _run_python_module(
        'experiments.run_coupling_sweep',
        '--suite',
        'chapter',
        '--profile',
        'test',
        '--disable-download',
        '--output-root',
        str(output_root),
    )
    return output_root
