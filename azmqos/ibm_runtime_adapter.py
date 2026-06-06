from __future__ import annotations
from dataclasses import dataclass
from typing import Any

def ibm_runtime_available() -> bool:
    try:
        import qiskit_ibm_runtime  # noqa: F401
        return True
    except Exception:
        return False

def require_ibm_runtime():
    try:
        import qiskit_ibm_runtime
        return qiskit_ibm_runtime
    except Exception as exc:
        raise ImportError(
            "qiskit-ibm-runtime is required for IBM Runtime execution. Install it with:\n"
            "python -m pip install qiskit-ibm-runtime"
        ) from exc

@dataclass
class IBMRuntimeDiagnostics:
    runtime_package_available: bool
    service_constructed: bool
    message: str
    available_backends: list[str]

    def summary(self):
        return (
            f"IBMRuntimeDiagnostics(package_available={self.runtime_package_available}, "
            f"service_constructed={self.service_constructed}, "
            f"available_backends={self.available_backends}, message={self.message})"
        )

def diagnose_ibm_runtime(channel: str | None = None, instance: str | None = None) -> IBMRuntimeDiagnostics:
    """Try to inspect IBM Runtime availability without submitting any jobs."""
    if not ibm_runtime_available():
        return IBMRuntimeDiagnostics(
            runtime_package_available=False,
            service_constructed=False,
            message="qiskit-ibm-runtime is not installed.",
            available_backends=[],
        )

    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
        kwargs: dict[str, Any] = {}
        if channel is not None:
            kwargs["channel"] = channel
        if instance is not None:
            kwargs["instance"] = instance
        service = QiskitRuntimeService(**kwargs)
        names = []
        try:
            backends = service.backends()
            names = [b.name for b in backends[:10]]
        except Exception:
            names = []
        return IBMRuntimeDiagnostics(
            runtime_package_available=True,
            service_constructed=True,
            message="QiskitRuntimeService was constructed. Backend list may depend on credentials/access.",
            available_backends=names,
        )
    except Exception as exc:
        return IBMRuntimeDiagnostics(
            runtime_package_available=True,
            service_constructed=False,
            message=f"Could not construct QiskitRuntimeService: {exc}",
            available_backends=[],
        )
