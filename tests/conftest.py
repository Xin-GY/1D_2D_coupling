from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from coupling.runtime_env import configure_runtime_environment


configure_runtime_environment(Path('/tmp/1d_2d_coupling_tests'))


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='session')
def coupling_sweep_artifacts(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output_root = tmp_path_factory.mktemp('coupling_sweep') / 'coupling_sweep'
    subprocess.run(
        [
            sys.executable,
            '-u',
            '-m',
            'experiments.run_coupling_sweep',
            '--output-root',
            str(output_root),
        ],
        check=True,
        cwd=REPO_ROOT,
    )
    return output_root
