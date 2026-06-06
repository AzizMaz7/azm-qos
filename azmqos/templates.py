from .pauli import PauliTerm
from .workload import QuantumWorkload
from .states import product_ry_state

def make_generic_two_qubit_workload():
    def prepare(params):
        return product_ry_state([params.get("theta0", 0.4), params.get("theta1", 0.7)])
    return QuantumWorkload(
        n_qubits=2,
        observables=[
            PauliTerm(1.0, "ZI", label="observable_ZI"),
            PauliTerm(0.5, "IZ", label="observable_IZ"),
            PauliTerm(-0.25, "XX", label="correlation_XX"),
            PauliTerm(0.125, "ZZ", label="correlation_ZZ"),
        ],
        state_preparation=prepare,
        parameters={"theta0": 0.4, "theta1": 0.7},
        name="generic_two_qubit_observable_problem",
        domain="general",
        description="A domain-neutral two-qubit observable estimation example.",
        tags=["general", "observable-estimation", "pauli"],
    )

def make_qaoa_maxcut_2node_workload(gamma=0.5, beta=0.3):
    def prepare(params):
        return product_ry_state([2 * params.get("beta", beta), 2 * params.get("gamma", gamma)])
    return QuantumWorkload(
        n_qubits=2,
        observables=[PauliTerm(0.5, "II", "constant"), PauliTerm(-0.5, "ZZ", "edge_ZZ")],
        state_preparation=prepare,
        parameters={"gamma": gamma, "beta": beta},
        name="qaoa_maxcut_2node_proxy",
        domain="optimization",
        description="A small MaxCut/QAOA-style cost-estimation workload.",
        tags=["qaoa", "maxcut", "optimization"],
    )

def make_chemistry_style_h2_proxy_workload(theta=0.6):
    def prepare(params):
        t = params.get("theta", theta)
        return product_ry_state([t, -t])
    return QuantumWorkload(
        n_qubits=2,
        observables=[
            PauliTerm(-1.052373245772859, "II", "h0"),
            PauliTerm(0.39793742484318045, "ZI", "h1_ZI"),
            PauliTerm(-0.39793742484318045, "IZ", "h2_IZ"),
            PauliTerm(-0.01128010425623538, "ZZ", "h3_ZZ"),
            PauliTerm(0.18093119978423156, "XX", "h4_XX"),
        ],
        state_preparation=prepare,
        parameters={"theta": theta},
        name="chemistry_style_h2_proxy",
        domain="quantum_chemistry",
        description="Compact Pauli-sum Hamiltonian workload inspired by quantum chemistry.",
        tags=["chemistry", "vqe", "hamiltonian", "pauli"],
    )
