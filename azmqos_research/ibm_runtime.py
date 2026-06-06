from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import json
import time

@dataclass
class IBMRuntimeConfig:
    """Configuration for optional IBM Runtime execution."""

    channel: str | None = None
    instance: str | None = None
    backend_name: str | None = None
    shots: int = 1024
    optimization_level: int = 1
    resilience_level: int | None = None
    dry_run: bool = True
    use_session: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        return (
            f"IBMRuntimeConfig(backend={self.backend_name}, shots={self.shots}, "
            f"optimization_level={self.optimization_level}, dry_run={self.dry_run}, "
            f"use_session={self.use_session})"
        )

@dataclass
class IBMRuntimeDiagnosticsResult:
    qiskit_installed: bool
    qiskit_ibm_runtime_installed: bool
    service_constructed: bool
    qiskit_version: str | None
    runtime_version: str | None
    message: str
    available_backends: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        return (
            "IBMRuntimeDiagnosticsResult\n"
            f"  qiskit_installed: {self.qiskit_installed}\n"
            f"  qiskit_ibm_runtime_installed: {self.qiskit_ibm_runtime_installed}\n"
            f"  service_constructed: {self.service_constructed}\n"
            f"  qiskit_version: {self.qiskit_version}\n"
            f"  runtime_version: {self.runtime_version}\n"
            f"  available_backends: {self.available_backends}\n"
            f"  message: {self.message}"
        )

@dataclass
class IBMBackendSummary:
    name: str
    num_qubits: int | None = None
    operational: bool | None = None
    simulator: bool | None = None
    pending_jobs: int | None = None
    basis_gates: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        return (
            f"IBMBackendSummary(name={self.name}, qubits={self.num_qubits}, "
            f"operational={self.operational}, simulator={self.simulator}, pending_jobs={self.pending_jobs})"
        )

@dataclass
class IBMRuntimeSubmissionResult:
    dry_run: bool
    backend_name: str | None
    primitive: str
    job_id: str | None
    status: str
    message: str
    result_preview: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        return (
            "IBMRuntimeSubmissionResult\n"
            f"  dry_run: {self.dry_run}\n"
            f"  backend: {self.backend_name}\n"
            f"  primitive: {self.primitive}\n"
            f"  job_id: {self.job_id}\n"
            f"  status: {self.status}\n"
            f"  message: {self.message}"
        )

def _import_qiskit_version():
    try:
        import qiskit
        return True, getattr(qiskit, "__version__", "unknown")
    except Exception:
        return False, None

def _import_runtime_version():
    try:
        import qiskit_ibm_runtime
        return True, getattr(qiskit_ibm_runtime, "__version__", "unknown")
    except Exception:
        return False, None

def ibm_runtime_packages_available() -> bool:
    qiskit_ok, _ = _import_qiskit_version()
    runtime_ok, _ = _import_runtime_version()
    return bool(qiskit_ok and runtime_ok)

def construct_qiskit_runtime_service(config: IBMRuntimeConfig | None = None):
    """Construct QiskitRuntimeService if qiskit-ibm-runtime and credentials are available."""
    config = config or IBMRuntimeConfig()
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
    except Exception as exc:
        raise ImportError(
            "qiskit-ibm-runtime is not installed. Install with: "
            "python -m pip install qiskit-ibm-runtime"
        ) from exc

    kwargs = {}
    if config.channel is not None:
        kwargs["channel"] = config.channel
    if config.instance is not None:
        kwargs["instance"] = config.instance
    return QiskitRuntimeService(**kwargs)

def diagnose_ibm_runtime(config: IBMRuntimeConfig | None = None, max_backends: int = 10) -> IBMRuntimeDiagnosticsResult:
    """Inspect local IBM Runtime readiness without submitting jobs."""
    config = config or IBMRuntimeConfig()
    qiskit_ok, qiskit_version = _import_qiskit_version()
    runtime_ok, runtime_version = _import_runtime_version()

    if not qiskit_ok:
        return IBMRuntimeDiagnosticsResult(
            qiskit_installed=False,
            qiskit_ibm_runtime_installed=runtime_ok,
            service_constructed=False,
            qiskit_version=None,
            runtime_version=runtime_version,
            message="Qiskit is not installed.",
        )

    if not runtime_ok:
        return IBMRuntimeDiagnosticsResult(
            qiskit_installed=True,
            qiskit_ibm_runtime_installed=False,
            service_constructed=False,
            qiskit_version=qiskit_version,
            runtime_version=None,
            message="qiskit-ibm-runtime is not installed.",
        )

    try:
        service = construct_qiskit_runtime_service(config)
        names = []
        try:
            backends = service.backends()
            for backend in backends[:max_backends]:
                names.append(getattr(backend, "name", str(backend)))
        except Exception:
            names = []
        return IBMRuntimeDiagnosticsResult(
            qiskit_installed=True,
            qiskit_ibm_runtime_installed=True,
            service_constructed=True,
            qiskit_version=qiskit_version,
            runtime_version=runtime_version,
            message="QiskitRuntimeService was constructed. Backend visibility depends on account access.",
            available_backends=names,
        )
    except Exception as exc:
        return IBMRuntimeDiagnosticsResult(
            qiskit_installed=True,
            qiskit_ibm_runtime_installed=True,
            service_constructed=False,
            qiskit_version=qiskit_version,
            runtime_version=runtime_version,
            message=f"Could not construct QiskitRuntimeService: {exc}",
        )

def _backend_summary(backend) -> IBMBackendSummary:
    name = getattr(backend, "name", str(backend))
    num_qubits = None
    basis_gates = []
    operational = None
    simulator = None
    pending_jobs = None

    try:
        num_qubits = getattr(backend, "num_qubits", None)
    except Exception:
        pass

    try:
        status = backend.status()
        operational = getattr(status, "operational", None)
        pending_jobs = getattr(status, "pending_jobs", None)
    except Exception:
        pass

    try:
        configuration = backend.configuration()
        simulator = getattr(configuration, "simulator", None)
        basis_gates = list(getattr(configuration, "basis_gates", []) or [])
        if num_qubits is None:
            num_qubits = getattr(configuration, "n_qubits", None)
    except Exception:
        pass

    return IBMBackendSummary(
        name=name,
        num_qubits=num_qubits,
        operational=operational,
        simulator=simulator,
        pending_jobs=pending_jobs,
        basis_gates=basis_gates,
    )

def list_ibm_backends(config: IBMRuntimeConfig | None = None, min_qubits: int | None = None, include_simulators: bool = False):
    """List backend summaries. Requires IBM Runtime service and account access."""
    service = construct_qiskit_runtime_service(config)
    summaries = []
    for backend in service.backends():
        summary = _backend_summary(backend)
        if min_qubits is not None and summary.num_qubits is not None and summary.num_qubits < min_qubits:
            continue
        if not include_simulators and summary.simulator is True:
            continue
        summaries.append(summary)
    return summaries

def select_least_busy_backend(config: IBMRuntimeConfig | None = None, min_qubits: int | None = None, include_simulators: bool = False):
    """Select a backend by lowest pending job count from visible backends."""
    summaries = list_ibm_backends(config, min_qubits=min_qubits, include_simulators=include_simulators)
    if not summaries:
        raise RuntimeError("No IBM backends available with the requested filters.")
    return sorted(summaries, key=lambda b: (b.pending_jobs if b.pending_jobs is not None else 10**9, b.name))[0]

def get_backend(config: IBMRuntimeConfig):
    service = construct_qiskit_runtime_service(config)
    if not config.backend_name:
        selected = select_least_busy_backend(config)
        config.backend_name = selected.name
    return service.backend(config.backend_name)

def prepare_isa_circuit(circuit, backend, optimization_level: int = 1):
    """Transpile a circuit to an IBM backend ISA when Qiskit is installed."""
    try:
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    except Exception as exc:
        raise ImportError("Qiskit is required for ISA-circuit preparation.") from exc
    pm = generate_preset_pass_manager(backend=backend, optimization_level=optimization_level)
    return pm.run(circuit)

def _simple_ghz_circuit(n_qubits: int = 2):
    try:
        from qiskit import QuantumCircuit
    except Exception as exc:
        raise ImportError("Qiskit is required to build demo circuits.") from exc
    qc = QuantumCircuit(n_qubits, n_qubits)
    qc.h(0)
    for i in range(n_qubits - 1):
        qc.cx(i, i + 1)
    qc.measure(range(n_qubits), range(n_qubits))
    return qc

def build_ibm_demo_circuit(n_qubits: int = 2):
    return _simple_ghz_circuit(n_qubits)

def run_sampler_v2_job(
    circuit=None,
    config: IBMRuntimeConfig | None = None,
    dry_run: bool | None = None,
):
    """Submit or dry-run an IBM Runtime SamplerV2 job.

    This function only submits when dry_run is explicitly False.
    """
    config = config or IBMRuntimeConfig()
    if dry_run is not None:
        config.dry_run = bool(dry_run)

    if config.dry_run:
        return IBMRuntimeSubmissionResult(
            dry_run=True,
            backend_name=config.backend_name,
            primitive="SamplerV2",
            job_id=None,
            status="dry_run",
            message="Dry run only. No IBM Runtime job was submitted.",
            metadata={"config": asdict(config)},
        )

    backend = get_backend(config)
    circuit = circuit or build_ibm_demo_circuit(min(2, getattr(backend, "num_qubits", 2) or 2))
    isa_circuit = prepare_isa_circuit(circuit, backend, config.optimization_level)

    try:
        from qiskit_ibm_runtime import SamplerV2 as Sampler
    except Exception:
        try:
            from qiskit_ibm_runtime import Sampler
        except Exception as exc:
            raise ImportError("Could not import SamplerV2/Sampler from qiskit_ibm_runtime.") from exc

    sampler = Sampler(mode=backend)
    job = sampler.run([isa_circuit], shots=config.shots)

    return IBMRuntimeSubmissionResult(
        dry_run=False,
        backend_name=getattr(backend, "name", config.backend_name),
        primitive="SamplerV2",
        job_id=job.job_id() if hasattr(job, "job_id") else None,
        status=str(job.status()) if hasattr(job, "status") else "submitted",
        message="IBM Runtime Sampler job submitted.",
        metadata={"config": asdict(config)},
    )

def run_estimator_v2_job(
    circuit,
    observable,
    config: IBMRuntimeConfig | None = None,
    dry_run: bool | None = None,
):
    """Submit or dry-run an IBM Runtime EstimatorV2 job."""
    config = config or IBMRuntimeConfig()
    if dry_run is not None:
        config.dry_run = bool(dry_run)

    if config.dry_run:
        return IBMRuntimeSubmissionResult(
            dry_run=True,
            backend_name=config.backend_name,
            primitive="EstimatorV2",
            job_id=None,
            status="dry_run",
            message="Dry run only. No IBM Runtime job was submitted.",
            metadata={"config": asdict(config)},
        )

    backend = get_backend(config)
    isa_circuit = prepare_isa_circuit(circuit, backend, config.optimization_level)

    try:
        from qiskit_ibm_runtime import EstimatorV2 as Estimator
    except Exception:
        try:
            from qiskit_ibm_runtime import Estimator
        except Exception as exc:
            raise ImportError("Could not import EstimatorV2/Estimator from qiskit_ibm_runtime.") from exc

    estimator = Estimator(mode=backend)
    job = estimator.run([(isa_circuit, observable)])

    return IBMRuntimeSubmissionResult(
        dry_run=False,
        backend_name=getattr(backend, "name", config.backend_name),
        primitive="EstimatorV2",
        job_id=job.job_id() if hasattr(job, "job_id") else None,
        status=str(job.status()) if hasattr(job, "status") else "submitted",
        message="IBM Runtime Estimator job submitted.",
        metadata={"config": asdict(config)},
    )

def make_ibm_runtime_report(diagnostics: IBMRuntimeDiagnosticsResult, output_path, backend_summaries=None, submission_result=None):
    output_path = Path(output_path)
    backend_summaries = backend_summaries or []

    lines = [
        "# AZM-QOS v2.3 IBM Runtime Report",
        "",
        "## Diagnostics",
        "",
        "```text",
        diagnostics.summary(),
        "```",
        "",
        "## Visible backend summaries",
        "",
    ]
    if backend_summaries:
        for backend in backend_summaries:
            lines.extend(["```text", backend.summary(), "```", ""])
    else:
        lines.append("No backend summaries were provided or visible.")

    if submission_result is not None:
        lines.extend([
            "",
            "## Submission result",
            "",
            "```text",
            submission_result.summary(),
            "```",
        ])

    lines.extend([
        "",
        "## Safety note",
        "",
        "AZM-QOS v2.3 uses dry-run mode by default. Real hardware jobs are only submitted when dry_run=False or the CLI is called with --submit.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path

def save_ibm_runtime_json(payload, output_path):
    output_path = Path(output_path)
    def default(o):
        if hasattr(o, "__dict__"):
            return o.__dict__
        return str(o)
    output_path.write_text(json.dumps(payload, indent=2, default=default), encoding="utf-8")
    return output_path

def hardware_vs_simulator_comparison_scaffold(simulator_result=None, hardware_result=None):
    """Return a comparison dictionary. Hardware result can be filled after job completion."""
    return {
        "simulator_result": simulator_result,
        "hardware_result": hardware_result,
        "status": "pending_hardware_result" if hardware_result is None else "comparison_ready",
        "note": "Populate hardware_result after retrieving IBM Runtime job output.",
    }
