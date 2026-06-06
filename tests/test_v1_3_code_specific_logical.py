from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import RuntimeManager, RuntimeConfig
from azmqos.states import zero_state
from azmqos_endvqs import default_endvqs_registry, build_all_endvqs_workloads, assemble_m_matrix, assemble_v_vector
from azmqos_logical import (
    repetition_code_3_logical_operator_map,
    encode_registry_with_code_map,
    compare_registry_sizes,
)
from azmqos_qec import repetition_code_3, build_syndrome_extraction_specs_for_code

def test_code_specific_map():
    code_map = repetition_code_3_logical_operator_map()
    assert code_map.encode_string("XZ") == "XXXZII"

def test_registry_encoding():
    physical = default_endvqs_registry()
    code_map = repetition_code_3_logical_operator_map()
    logical = encode_registry_with_code_map(physical, code_map)
    comparison = compare_registry_sizes(physical, logical)
    assert comparison["logical_max_pauli_length"] == 6

def test_syndrome_specs():
    code = repetition_code_3()
    specs = build_syndrome_extraction_specs_for_code(code)
    assert len(specs) == 2
    assert specs[0].ancilla_qubit == 3
    assert any(step.gate == "MEASURE" for step in specs[0].steps)

def test_encoded_workloads_run():
    physical = default_endvqs_registry()
    code_map = repetition_code_3_logical_operator_map()
    logical = encode_registry_with_code_map(physical, code_map)
    workloads = build_all_endvqs_workloads(registry=logical)

    for workload in workloads:
        n = workload.n_qubits
        workload.state_preparation = lambda params, n=n: zero_state(n)
        workload.parameters = {"n_physical_qubits": n}

    manager = RuntimeManager()
    results = [manager.run(w, "shot_simulator", RuntimeConfig(shots=64, repeats=1, seed=1)) for w in workloads]
    M = assemble_m_matrix(results, dimension=2)
    V = assemble_v_vector(results, dimension=2)
    assert M.shape == (2, 2)
    assert V.shape == (2,)

if __name__ == "__main__":
    test_code_specific_map()
    test_registry_encoding()
    test_syndrome_specs()
    test_encoded_workloads_run()
    print("All v1.3 code-specific logical/syndrome tests passed.")
