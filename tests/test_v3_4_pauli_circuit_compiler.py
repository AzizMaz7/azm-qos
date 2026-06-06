from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    PauliTerm,
    PauliComponent,
    pauli_commutes,
    can_share_single_qubit_measurement_basis,
    merge_measurement_basis,
    group_commuting_terms_greedy,
    basis_rotations_for_pauli_basis,
    expectation_from_counts_for_pauli,
    ancilla_expectation_from_counts,
    compile_pauli_component,
    make_pauli_compile_demo,
)
from azmqos_research.cli import main

def test_pauli_commutation():
    assert pauli_commutes("ZZ", "ZI")
    # XZ and ZX commute: two local anticommutes give an even parity.
    assert pauli_commutes("XZ", "ZX")
    # XI and ZI anticommute: one local anticommute gives odd parity.
    assert not pauli_commutes("XI", "ZI")

def test_product_basis_sharing():
    assert can_share_single_qubit_measurement_basis("ZI", "ZZ")
    assert not can_share_single_qubit_measurement_basis("XI", "ZI")

def test_merge_basis_and_rotations():
    basis = merge_measurement_basis(["ZI", "IZ", "ZZ"])
    assert basis == "ZZ"
    assert basis_rotations_for_pauli_basis("XYZ") == [(0, "H"), (1, "SdgH")]

def test_expectation_from_counts():
    counts = {"0": 75, "1": 25}
    exp = expectation_from_counts_for_pauli(counts, "Z")
    assert abs(exp - 0.5) < 1e-12

def test_ancilla_expectation():
    counts = {"0": 80, "1": 20}
    assert abs(ancilla_expectation_from_counts(counts) - 0.6) < 1e-12

def test_compile_component():
    component = PauliComponent(
        name="test_component",
        quantity="M",
        indices=[0, 0],
        terms=[PauliTerm(1.0, "ZI"), PauliTerm(1.0, "IZ"), PauliTerm(1.0, "XX")],
    )
    result = compile_pauli_component(component)
    assert len(result.groups) >= 2
    assert len(result.measurement_circuits) == len(result.groups)
    assert len(result.hadamard_tests) == len(component.terms)

def test_demo_and_cli():
    out_dir = ROOT / "outputs" / "test_v3_4_pauli_demo"
    result = make_pauli_compile_demo(out_dir)
    assert Path(result.artifacts["manifest"]).exists()

    cli_out = ROOT / "outputs" / "test_v3_4_cli"
    code = main(["pauli-compile", "--output-dir", str(cli_out)])
    assert code == 0
    assert (cli_out / "pauli_compile_demo_manifest.json").exists()

if __name__ == "__main__":
    test_pauli_commutation()
    test_product_basis_sharing()
    test_merge_basis_and_rotations()
    test_expectation_from_counts()
    test_ancilla_expectation()
    test_compile_component()
    test_demo_and_cli()
    print("All v3.4 Pauli circuit compiler tests passed.")
