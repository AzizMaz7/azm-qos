from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass
class BackendSelectionRequest:
    prefer_hardware: bool = False
    require_exact: bool = False
    require_shots: bool = True
    allow_cloud: bool = False
    max_qubits: int | None = None
    preferred_provider: str | None = None
    tags: list[str] | None = None

@dataclass
class BackendSelection:
    backend_name: str
    reason: str
    metadata: dict[str, Any]

class BackendSelector:
    """Simple policy engine for choosing a backend from RuntimeManager."""

    def select(self, manager, workload, request: BackendSelectionRequest | None = None) -> BackendSelection:
        request = request or BackendSelectionRequest()
        backends = manager.list_backends()

        if request.require_exact and "local_statevector" in backends and workload.state_preparation is not None:
            return BackendSelection(
                backend_name="local_statevector",
                reason="Exact expectation values requested and state-preparation workload is available.",
                metadata={},
            )

        if request.prefer_hardware or request.allow_cloud:
            if "ibm_runtime" in backends and request.allow_cloud:
                return BackendSelection(
                    backend_name="ibm_runtime",
                    reason="Cloud/hardware execution allowed and IBM Runtime adapter is registered.",
                    metadata={"warning": "IBM credentials and runtime availability still required."},
                )

        if "qiskit_aer" in backends and workload.circuit is not None:
            return BackendSelection(
                backend_name="qiskit_aer",
                reason="Circuit workload detected and Qiskit Aer backend is available.",
                metadata={},
            )

        if "shot_simulator" in backends:
            return BackendSelection(
                backend_name="shot_simulator",
                reason="Default finite-shot simulator selected.",
                metadata={},
            )

        if "local_statevector" in backends:
            return BackendSelection(
                backend_name="local_statevector",
                reason="Fallback exact local statevector backend selected.",
                metadata={},
            )

        raise RuntimeError("No compatible backend found.")
