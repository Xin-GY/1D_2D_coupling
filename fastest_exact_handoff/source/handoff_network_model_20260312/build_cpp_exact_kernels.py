import os
from pathlib import Path

from setuptools import Extension, setup

import numpy as np
from Cython.Build import cythonize


root = Path(__file__).resolve().parent
repo_root = root.parent.parent.parent
os.chdir(repo_root)

extensions = [
    Extension(
        name="fastest_exact_handoff.source.handoff_network_model_20260312.cython_cpp_bridge",
        sources=[
            str(root / "cython_cpp_bridge.pyx"),
            str(root / "cpp/output_buffer.cpp"),
            str(root / "cpp/evolve_core.cpp"),
        ],
        include_dirs=[np.get_include(), str(root)],
        language="c++",
        extra_compile_args=["-O3", "-std=c++17"],
    )
]

setup(
    name="cpp_exact_kernels",
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
