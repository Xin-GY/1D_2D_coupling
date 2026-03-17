from __future__ import annotations

from typing import Any

from demo.Rivernet import Rivernet as LegacyRivernet
from fastest_exact_handoff.source.handoff_network_model_20260312.coupling_factory import (
    build_fastest_exact_network,
)


SUPPORTED_ONE_D_BACKENDS = {"legacy", "fastest_exact"}
DEFAULT_ONE_D_BACKEND = "fastest_exact"


def create_oned_network(
    backend: str,
    topology: dict[tuple[str, str], dict[str, Any]],
    model_data: dict[str, Any],
    *,
    initial_stage: float,
    verbos: bool = False,
):
    backend_name = str(backend).strip().lower()
    if backend_name == "legacy":
        network = LegacyRivernet(topology, model_data, verbos=verbos)
        for _, _, data in network.G.edges(data=True):
            data["river"].Set_init_water_level(float(initial_stage))
        return network
    if backend_name == "fastest_exact":
        return build_fastest_exact_network(
            topology,
            model_data,
            initial_stage=float(initial_stage),
            verbos=verbos,
        )
    raise ValueError(
        f"Unsupported 1D backend {backend!r}; expected one of {sorted(SUPPORTED_ONE_D_BACKENDS)}"
    )
