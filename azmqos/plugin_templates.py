from __future__ import annotations
from .plugins import AZMQOSPlugin, PluginInfo
from .pauli import PauliTerm
from .workload import QuantumWorkload
from .states import product_ry_state, bell_state, ghz_state

class VQSPlugin(AZMQOSPlugin):
    """Template plugin for variational quantum simulation workloads.

    This is intentionally generic. Real VQS plugins should provide physical
    metric/gradient terms from the user's chosen ansatz and Hamiltonian.
    """

    def info(self):
        return PluginInfo(
            name="azmqos-vqs-template",
            version="0.1.0",
            domain="vqs",
            description="Template VQS plugin that creates metric/gradient-style Pauli workloads.",
            author="Abdul Aziz Maaz",
            tags=["vqs", "variational", "simulation", "template"],
        )

    def create_workloads(self, n_qubits: int = 2, theta0: float = 0.4, theta1: float = 0.7, **kwargs):
        if n_qubits != 2:
            raise ValueError("Template VQSPlugin currently supports n_qubits=2 for demonstration.")

        def prepare(params):
            return product_ry_state([params.get("theta0", theta0), params.get("theta1", theta1)])

        metric_workload = QuantumWorkload(
            n_qubits=2,
            observables=[
                PauliTerm(1.0, "ZI", label="metric_proxy_00"),
                PauliTerm(0.5, "IZ", label="metric_proxy_11"),
                PauliTerm(-0.25, "XX", label="metric_proxy_01"),
            ],
            state_preparation=prepare,
            parameters={"theta0": theta0, "theta1": theta1},
            name="vqs_metric_proxy_workload",
            domain="vqs",
            description="Template VQS metric-style observable workload.",
            tags=["vqs", "metric", "template"],
            metadata={"plugin": self.info().name},
        )

        gradient_workload = QuantumWorkload(
            n_qubits=2,
            observables=[
                PauliTerm(0.75, "YY", label="gradient_proxy_0"),
                PauliTerm(0.125, "ZZ", label="gradient_proxy_1"),
            ],
            state_preparation=prepare,
            parameters={"theta0": theta0, "theta1": theta1},
            name="vqs_gradient_proxy_workload",
            domain="vqs",
            description="Template VQS gradient/force-style observable workload.",
            tags=["vqs", "gradient", "force", "template"],
            metadata={"plugin": self.info().name},
        )

        return [metric_workload, gradient_workload]

class ENDVQSPlugin(AZMQOSPlugin):
    """Template plugin for END/VQS-style workloads.

    This is a placeholder structure for the user's PhD project. It does not
    hard-code a full END derivation. It shows where M-matrix and V-vector
    workloads belong.
    """

    def info(self):
        return PluginInfo(
            name="azmqos-endvqs-template",
            version="0.1.0",
            domain="endvqs",
            description="Template END/VQS plugin for M-matrix and V-vector observable workloads.",
            author="Abdul Aziz Maaz",
            tags=["end", "vqs", "m-matrix", "v-vector", "template"],
        )

    def create_workloads(self, theta0: float = 0.4, theta1: float = 0.7, **kwargs):
        def prepare(params):
            return product_ry_state([params.get("theta0", theta0), params.get("theta1", theta1)])

        m_matrix_proxy = QuantumWorkload(
            n_qubits=2,
            observables=[
                PauliTerm(1.0, "ZI", label="M_00_proxy"),
                PauliTerm(1.0, "IZ", label="M_11_proxy"),
                PauliTerm(-0.5, "XX", label="M_01_proxy"),
                PauliTerm(0.25, "ZZ", label="M_correlation_proxy"),
            ],
            state_preparation=prepare,
            parameters={"theta0": theta0, "theta1": theta1},
            name="endvqs_m_matrix_proxy_workload",
            domain="endvqs",
            description="Template END/VQS M-matrix-style workload. Replace proxy terms with derived Pauli decompositions.",
            tags=["endvqs", "M-matrix", "template"],
            metadata={
                "plugin": self.info().name,
                "replace_with": "real Mbb, Mab, Maa, etc. Pauli decompositions",
            },
        )

        v_vector_proxy = QuantumWorkload(
            n_qubits=2,
            observables=[
                PauliTerm(0.75, "XX", label="V_0_proxy"),
                PauliTerm(-0.25, "YY", label="V_1_proxy"),
                PauliTerm(0.125, "ZZ", label="V_correlation_proxy"),
            ],
            state_preparation=prepare,
            parameters={"theta0": theta0, "theta1": theta1},
            name="endvqs_v_vector_proxy_workload",
            domain="endvqs",
            description="Template END/VQS V-vector-style workload. Replace proxy terms with derived Pauli decompositions.",
            tags=["endvqs", "V-vector", "template"],
            metadata={
                "plugin": self.info().name,
                "replace_with": "real Va, Vb, and force-vector Pauli decompositions",
            },
        )

        return [m_matrix_proxy, v_vector_proxy]

class QECPlugin(AZMQOSPlugin):
    """Template plugin for QEC-style stabilizer/logical observable workloads."""

    def info(self):
        return PluginInfo(
            name="azmqos-qec-template",
            version="0.1.0",
            domain="qec",
            description="Template QEC plugin for stabilizer and logical Pauli workloads.",
            author="Abdul Aziz Maaz",
            tags=["qec", "stabilizer", "logical", "template"],
        )

    def create_workloads(self, state: str = "bell", **kwargs):
        if state == "ghz":
            n_qubits = 3
            def prepare(params):
                return ghz_state(3)
            observables = [
                PauliTerm(1.0, "ZZI", label="stabilizer_ZZI"),
                PauliTerm(1.0, "IZZ", label="stabilizer_IZZ"),
                PauliTerm(1.0, "XXX", label="logical_X_proxy"),
            ]
        else:
            n_qubits = 2
            def prepare(params):
                return bell_state()
            observables = [
                PauliTerm(1.0, "ZZ", label="stabilizer_ZZ"),
                PauliTerm(1.0, "XX", label="logical_X_proxy"),
            ]

        return QuantumWorkload(
            n_qubits=n_qubits,
            observables=observables,
            state_preparation=prepare,
            parameters={},
            name=f"qec_{state}_stabilizer_proxy_workload",
            domain="qec",
            description="Template QEC stabilizer/logical observable workload.",
            tags=["qec", "stabilizer", "logical", "template"],
            metadata={"plugin": self.info().name, "state": state},
        )
