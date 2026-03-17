from __future__ import annotations

import logging
import os
from pathlib import Path


_CONFIGURED = False


def configure_runtime_environment(base_dir: str | os.PathLike[str] | None = None) -> Path:
    global _CONFIGURED
    if _CONFIGURED:
        return Path(os.environ['MPLCONFIGDIR'])

    root = Path(base_dir) if base_dir is not None else Path('/tmp/1d_2d_coupling_runtime')
    mpl_dir = root / 'mplconfig'
    cache_dir = root / 'cache'
    fontconfig_dir = root / 'fontconfig'
    xdg_config_dir = root / 'xdg_config'
    pycache_dir = root / 'pycache'
    for path in (mpl_dir, cache_dir, fontconfig_dir, xdg_config_dir, pycache_dir):
        path.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault('MPLCONFIGDIR', str(mpl_dir))
    os.environ.setdefault('XDG_CACHE_HOME', str(cache_dir))
    os.environ.setdefault('XDG_CONFIG_HOME', str(xdg_config_dir))
    os.environ.setdefault('FONTCONFIG_PATH', '/etc/fonts')
    os.environ.setdefault('FONTCONFIG_FILE', '/etc/fonts/fonts.conf')
    os.environ.setdefault('FONTCONFIG_CACHE', str(fontconfig_dir))
    os.environ.setdefault('PYTHONPYCACHEPREFIX', str(pycache_dir))

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
