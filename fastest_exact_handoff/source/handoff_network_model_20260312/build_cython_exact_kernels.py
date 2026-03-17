import os
from pathlib import Path

from setuptools import Extension, setup

import numpy as np
from Cython.Build import cythonize

root = Path(__file__).resolve().parent
repo_root = root.parent.parent.parent
os.chdir(repo_root)


def existing_extensions():
    specs = []
    if (root / "cython_node_iteration.pyx").exists():
        specs.append(
            Extension(
                name="fastest_exact_handoff.source.handoff_network_model_20260312.cython_node_iteration",
                sources=[str(root / "cython_node_iteration.pyx")],
                include_dirs=[np.get_include(), str(root)],
                extra_compile_args=["-O3"],
            )
        )
    if (root / "cython_river_kernels.pyx").exists():
        specs.append(
            Extension(
                name="fastest_exact_handoff.source.handoff_network_model_20260312.cython_river_kernels",
                sources=[str(root / "cython_river_kernels.pyx"), str(root / "cpp/river_kernels.cpp")],
                include_dirs=[np.get_include(), str(root)],
                language="c++",
                extra_compile_args=["-O3", "-std=c++17"],
            )
        )
    return specs


extensions = existing_extensions()

setup(
    name="cython_exact_kernels",
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            "language_level": 3,
            "boundscheck": False,
            "wraparound": False,
            "initializedcheck": False,
            "cdivision": True,
        },
    ),
)
