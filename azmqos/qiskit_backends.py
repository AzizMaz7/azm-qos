from __future__ import annotations
import numpy as np
from .backends import BackendAdapter, BackendInfo
from .config import RuntimeConfig
from .job import JobResult
from .qiskit_adapter import require_qiskit, require_qiskit_aer, add_pauli_measurement_basis, expectation_from_counts

class QiskitAerBackend(BackendAdapter):
    """Optional Qiskit Aer backend.

    This backend measures each Pauli term separately by adding basis rotations and
    all-qubit measurement to a Qiskit circuit workload.
    """

    def __init__(self, name="qiskit_aer", simulator_options=None):
        super().__init__(name)
        self.simulator_options = simulator_options or {}

    def info(self):
        return BackendInfo(
            name=self.name,
            backend_type="qiskit_aer",
            description="Qiskit Aer finite-shot circuit backend.",
            supports_shots=True,
            supports_exact=False,
            metadata={"optional_dependency": "qiskit-aer"},
        )

    def run(self, workload, config: RuntimeConfig):
        config.validate()
        require_qiskit()
        AerSimulator = require_qiskit_aer()

        if workload.circuit is None:
            raise ValueError("QiskitAerBackend requires workload.circuit.")

        simulator = AerSimulator(**self.simulator_options)
        totals = []
        last_terms = {}

        for _ in range(config.repeats):
            total = 0.0 + 0.0j
            term_estimates = {}
            for term in workload.observables:
                measurement_circuit = add_pauli_measurement_basis(workload.circuit, term.pauli)
                compiled = measurement_circuit
                try:
                    from qiskit import transpile
                    compiled = transpile(measurement_circuit, simulator, optimization_level=config.optimization_level)
                except Exception:
                    pass

                job = simulator.run(compiled, shots=config.shots, seed_simulator=config.seed)
                result = job.result()
                counts = result.get_counts()
                raw = expectation_from_counts(counts, term.pauli)
                term_est = term.coeff * raw
                total += term_est
                term_estimates[term.name] = float(np.real_if_close(term_est))
            totals.append(total)
            last_terms = term_estimates

        totals = np.asarray(totals, dtype=complex)
        return JobResult(
            workload_name=workload.name,
            domain=workload.domain,
            backend_name=self.name,
            backend_type="qiskit_aer",
            shots=config.shots,
            repeats=config.repeats,
            exact_total=None,
            estimate_mean=np.mean(totals),
            estimate_std=float(np.std(np.real(totals), ddof=1)) if config.repeats > 1 else 0.0,
            mean_absolute_error=None,
            term_estimates=last_terms,
            metadata={
                "backend_info": self.info().__dict__,
                "qiskit_note": "Each Pauli term measured in a separate basis-rotated circuit.",
                "optimization_level": config.optimization_level,
            },
        )
