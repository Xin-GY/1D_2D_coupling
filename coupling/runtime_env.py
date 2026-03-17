from __future__ import annotations

import logging
import os
from pathlib import Path
import re
import site
import sys


_CONFIGURED = False
_ANUGA_EDITABLE_REPAIRED = False


def _site_packages_root() -> Path | None:
    for candidate in site.getsitepackages():
        path = Path(candidate)
        if path.exists():
            return path
    return None


def repair_anuga_editable_build_env() -> None:
    global _ANUGA_EDITABLE_REPAIRED
    if _ANUGA_EDITABLE_REPAIRED:
        return

    site_root = _site_packages_root()
    if site_root is None:
        return
    loader_path = site_root / '_anuga_editable_loader.py'
    if not loader_path.exists():
        _ANUGA_EDITABLE_REPAIRED = True
        return

    text = loader_path.read_text(encoding='utf-8')
    match = re.search(r"\[\s*'([^']+/overlay/bin/ninja)'\s*\]", text)
    if not match:
        _ANUGA_EDITABLE_REPAIRED = True
        return

    overlay_bin = Path(match.group(1)).parent
    overlay_root = overlay_bin.parent.parent
    env_bin = Path(sys.executable).resolve().parent

    overlay_bin.mkdir(parents=True, exist_ok=True)
    for tool in ('ninja', 'meson', 'cython'):
        source = env_bin / tool
        if not source.exists():
            continue
        target = overlay_bin / tool
        if target.exists() or target.is_symlink():
            target.unlink()
        target.symlink_to(source)

    numpy_include = site_root / 'numpy' / '_core' / 'include'
    if numpy_include.exists():
        pyver = f'python{sys.version_info.major}.{sys.version_info.minor}'
        target = overlay_root / 'lib' / pyver / 'site-packages' / 'numpy' / '_core' / 'include'
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            target.unlink()
        target.symlink_to(numpy_include)

    _ANUGA_EDITABLE_REPAIRED = True


def configure_runtime_environment(base_dir: str | os.PathLike[str] | None = None) -> Path:
    global _CONFIGURED
    if _CONFIGURED:
        return Path(os.environ['MPLCONFIGDIR'])

    repair_anuga_editable_build_env()

    root = Path(base_dir) if base_dir is not None else Path('/tmp/1d_2d_coupling_runtime')
    mpl_dir = root / 'mplconfig'
    cache_dir = root / 'cache'
    fontconfig_dir = root / 'fontconfig'
    xdg_config_dir = root / 'xdg_config'
    pycache_dir = root / 'pycache'
    anuga_data_dir = root / 'anuga_data'
    for path in (mpl_dir, cache_dir, fontconfig_dir, xdg_config_dir, pycache_dir, anuga_data_dir):
        path.mkdir(parents=True, exist_ok=True)

    # Reuse the stable user-level CuPy cache so real-GPU entrypoints do not
    # force an NVRTC cold compile on every subprocess launch.
    cupy_cache_dir = Path(os.environ.get('CUPY_CACHE_DIR', Path.home() / '.cupy' / 'kernel_cache'))
    cupy_cache_dir.mkdir(parents=True, exist_ok=True)

    os.environ['MPLCONFIGDIR'] = str(mpl_dir)
    os.environ['XDG_CACHE_HOME'] = str(cache_dir)
    os.environ['XDG_CONFIG_HOME'] = str(xdg_config_dir)
    os.environ['FONTCONFIG_PATH'] = '/etc/fonts'
    os.environ['FONTCONFIG_FILE'] = '/etc/fonts/fonts.conf'
    os.environ['FONTCONFIG_CACHE'] = str(fontconfig_dir)
    os.environ['CUPY_CACHE_DIR'] = str(cupy_cache_dir)
    os.environ['PYTHONPYCACHEPREFIX'] = str(pycache_dir)
    os.environ['ANUGADATA'] = str(anuga_data_dir)
    os.environ['INUNDATIONHOME'] = str(anuga_data_dir)

    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        if not hasattr(record, 'mname'):
            record.mname = record.module
        return record

    logging.setLogRecordFactory(record_factory)
    _CONFIGURED = True
    return mpl_dir


def require_fast_mode(mode: str | None) -> str:
    normalized = 'fast' if mode is None else str(mode).strip()
    if normalized != 'fast':
        raise ValueError(f'Only GPUInlet fast mode is supported, got mode={mode!r}')
    return normalized
