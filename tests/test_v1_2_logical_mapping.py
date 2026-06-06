from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import RuntimeManager, RuntimeConfig
from azmqos_endvqs import default_endvqs_registry, assemble_m_matrix, assemble_v_vector
from azmqos_logical import (
    repetition_code_block_encoding,
    identity_encoding,
    encode_pauli_string,
    encode_term_registry,
    compare_registry_sizes,
    build_logical_endvqs_workloads,
    estimate_logical_mapping_resources,
)

def test_encode_pauli_string():
    enc = repetition_code_block_encoding(3)
    assert encode_pauli_string("XZ", enc) == "XXXZZZ"

def test_identity_encoding():
    enc = identity_encoding()
    assert encode_pauli_string("XYZ", enc) == "XYZ"

def test_encode_registry():
    reg = default_endvqs_registry()
    enc = repetition_code_block_encoding(3)
    logical = encode_term_registry(reg, enc)
    comparison = compare_registry_sizes(reg, logical)
    assert comparison["logical_max_pauli_length"] == 3 * comparison["physical_max_pauli_length"]

def test_logical_workloads_run():
    reg = default_endvqs_registry()
    enc = repetition_code_block_encoding(3)
    workloads = build_logical_endvqs_workloads(reg, enc)
    assert len(workloads) == 6
    manager = RuntimeManager()
    results = [manager.run(w, "shot_simulator", RuntimeConfig(shots=64, repeats=1, seed=1)) for w in workloads]
    M = assemble_m_matrix(results, dimension=2)
    V = assemble_v_vector(results, dimension=2)
    assert M.shape == (2, 2)
    assert V.shape == (2,)

def test_resource_estimate():
    reg = default_endvqs_registry()
    enc = repetition_code_block_encoding(3)
    est = estimate_logical_mapping_resources(reg, enc, shots_per_term=100, rounds=2)
    assert est.physical_qubits == est.logical_qubits * 3
    assert est.estimated_total_shots > 0

if __name__ == "__main__":
    test_encode_pauli_string()
    test_identity_encoding()
    test_encode_registry()
    test_logical_workloads_run()
    test_resource_estimate()
    print("All v1.2 logical mapping tests passed.")
