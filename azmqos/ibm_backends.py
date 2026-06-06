from __future__ import annotations
from .backends import BackendAdapter, BackendInfo
from .config import RuntimeConfig
from .job import JobResult
from .cloud import make_local_cloud_status
from .ibm_runtime_adapter import ibm_runtime_available, diagnose_ibm_runtime

class IBMRuntimeBackend(BackendAdapter):
    """IBM Runtime backend scaffold.

    v0.7 intentionally avoids silent hardware submission. It provides a safe
    adapter and diagnostics. Full Sampler/Estimator execution should be added
    in a later version after credentials, runtime version, and primitive API
    are known.
    """

    def __init__(self, name="ibm_runtime", backend_name: str | None = None, channel: str | None = None, instance: str | None = None):
        super().__init__(name)
        self.target_backend_name = backend_name
        self.channel = channel
        self.instance = instance

    def info(self):
        return BackendInfo(
            name=self.name,
            backend_type="ibm_runtime_scaffold",
            description="IBM Quantum Runtime adapter scaffold with safe diagnostics.",
            supports_shots=True,
            supports_exact=False,
            metadata={
                "optional_dependency": "qiskit-ibm-runtime",
                "runtime_package_available": ibm_runtime_available(),
                "target_backend_name": self.target_backend_name,
                "channel": self.channel,
                "instance": self.instance,
            },
        )

    def diagnostics(self):
        return diagnose_ibm_runtime(channel=self.channel, instance=self.instance)

    def run(self, workload, config: RuntimeConfig):
        diag = self.diagnostics()
        status = make_local_cloud_status(
            backend_name=self.name,
            status="not_submitted",
            message="IBM Runtime scaffold did not submit a hardware job in v0.7.",
        )

        raise RuntimeError(
            "IBMRuntimeBackend in AZM-QOS v0.7 is a safe scaffold and does not submit jobs yet.\n"
            f"Diagnostics: {diag.summary()}\n"
            "Next step: implement Sampler/Estimator execution once your IBM credentials, backend, "
            "and installed qiskit-ibm-runtime API version are confirmed."
        )
