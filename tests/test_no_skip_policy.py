from __future__ import annotations

import ast
from pathlib import Path


FORBIDDEN_ATTRS = {'skip', 'skipif', 'xfail', 'importorskip'}


def _forbidden_calls(tree: ast.AST) -> list[str]:
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in FORBIDDEN_ATTRS:
                hits.append(func.attr)
            elif isinstance(func, ast.Name) and func.id in FORBIDDEN_ATTRS:
                hits.append(func.id)
    return hits


def test_target_test_modules_do_not_use_skip_or_xfail():
    for path in Path('tests').glob('test_*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        hits = _forbidden_calls(tree)
        assert not hits, f'{path} contains forbidden skip/xfail usage: {hits}'
