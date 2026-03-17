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
        name="fastest_exact_handoff.source.handoff_network_model_20260312.cython_cross_section",
        sources=[str(root / "cython_cross_section.pyx")],
        include_dirs=[np.get_include(), str(root)],
        extra_compile_args=["-O3"],
    )
]


setup(
    name="cython_cross_section",
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
