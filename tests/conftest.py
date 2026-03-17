from __future__ import annotations

from pathlib import Path

from coupling.runtime_env import configure_runtime_environment


configure_runtime_environment(Path('/tmp/1d_2d_coupling_tests'))
