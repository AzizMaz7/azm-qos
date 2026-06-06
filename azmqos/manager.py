from __future__ import annotations
from .config import RuntimeConfig
from .backends import BackendAdapter, LocalStatevectorBackend, ShotSimulatorBackend

class RuntimeManager:
    def __init__(self, include_qiskit: bool = True, include_ibm: bool = True):
        self.backends: dict[str, BackendAdapter] = {}
        self.register_backend(LocalStatevectorBackend())
        self.register_backend(ShotSimulatorBackend())
        if include_qiskit:
            try:
                from .qiskit_backends import QiskitAerBackend
                self.register_backend(QiskitAerBackend())
            except Exception:
                pass
        if include_ibm:
            try:
                from .ibm_backends import IBMRuntimeBackend
                self.register_backend(IBMRuntimeBackend())
            except Exception:
                pass

    def register_backend(self, backend: BackendAdapter):
        self.backends[backend.name] = backend

    def list_backends(self):
        return {name: backend.info() for name, backend in self.backends.items()}

    def get_backend(self, name):
        if name not in self.backends:
            available = ", ".join(self.backends)
            raise KeyError(f"Unknown backend {name!r}. Available backends: {available}")
        return self.backends[name]

    def run(self, workload, backend_name="shot_simulator", config: RuntimeConfig | None = None):
        if config is None:
            config = RuntimeConfig()
        if config.seed is not None and backend_name == "shot_simulator":
            self.register_backend(ShotSimulatorBackend(seed=config.seed))
        backend = self.get_backend(backend_name)
        return backend.run(workload, config)
