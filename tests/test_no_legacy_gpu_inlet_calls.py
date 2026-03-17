from __future__ import annotations

import ast
from pathlib import Path


PRODUCTION_DIRS = ['coupling', 'experiments', 'scripts', 'examples', 'demo']


def _python_files() -> list[Path]:
    files: list[Path] = []
    for dirname in PRODUCTION_DIRS:
        files.extend(Path(dirname).rglob('*.py'))
    return files


def test_production_code_does_not_call_legacy_gpu_inlet_api_or_nonfast_modes():
    for path in _python_files():
        text = path.read_text(encoding='utf-8')
        assert 'cpu_compatible' not in text, f'{path} references cpu_compatible'
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr != 'apply_inlets_gpu', f'{path} calls legacy apply_inlets_gpu()'
