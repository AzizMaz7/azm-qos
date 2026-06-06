from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    PauliTerm,
    PauliComponent,
    default_repetition_code,
    default_five_qubit_code,
    get_code_by_name,
    map_logical_pauli_string_to_physical,
    map_component_to_logical,
    make_syndrome_specs,
    syndrome_acceptance_probability,
    estimate_logical_component,
    run_qec_demo,
    init_production_project,
    load_production_spec,
    save_production_spec,
    run_production_qec_estimator,
)
from azmqos_research.cli import main

def test_default_codes():
    rep = default_repetition_code(3)
    assert rep.n_physical == 3
    assert len(rep.stabilizers) == 2
    five = default_five_qubit_code()
    assert five.n_physical == 5
    assert len(five.stabilizers) == 4
    assert get_code_by_name("repetition3").name == "repetition3"

def test_logical_mapping():
    code = default_repetition_code(3)
    physical = map_logical_pauli_string_to_physical("XZ", code)
    assert len(physical) == 6

def test_component_mapping_and_syndromes():
    code = default_repetition_code(3)
    component = PauliComponent(
        name="test_component",
        quantity="M",
        indices=[0, 0],
        terms=[PauliTerm(1.0, "ZI"), PauliTerm(0.5, "XX")],
        metadata={"component_family": "Mbb"},
    )
    logical = map_component_to_logical(component, code)
    assert len(logical.logical_terms) == 2
    syndromes = make_syndrome_specs(code)
    assert len(syndromes) == len(code.stabilizers)

def test_logical_estimate():
    code = default_repetition_code(3)
    component = PauliComponent(
        name="test_estimate_component",
        quantity="M",
        indices=[0, 0],
        terms=[PauliTerm(1.0, "Z"), PauliTerm(0.25, "X")],
        metadata={"component_family": "Mbb"},
    )
    logical = map_component_to_logical(component, code)
    estimate = estimate_logical_component(logical, shots=64)
    assert estimate.n_logical_terms == 2
    assert 0.0 <= estimate.syndrome_acceptance <= 1.0

def test_qec_demo():
    out_dir = ROOT / "outputs" / "test_v4_1_qec_demo"
    result = run_qec_demo(out_dir)
    assert len(result.estimates) == 1
    assert Path(result.artifacts["manifest"]).exists()

def _prepared_spec(tmp_name):
    out_dir = ROOT / "outputs" / tmp_name
    spec, artifacts = init_production_project(out_dir, project_name=tmp_name)
    spec = load_production_spec(artifacts["config_path"])
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    save_production_spec(spec, artifacts["config_path"])
    return spec, artifacts

def test_production_qec_estimator():
    spec, artifacts = _prepared_spec("test_v4_1_production_qec")
    result = run_production_qec_estimator(
        artifacts["config_path"],
        code_name="repetition3",
        max_components=2,
        shots=64,
    )
    assert len(result.estimates) == 2
    assert Path(result.artifacts["manifest"]).exists()
    assert Path(result.artifacts["M_logical_estimates_csv"]).exists()

def test_cli_qec_commands():
    out_dir = ROOT / "outputs" / "test_v4_1_cli_qec_demo"
    code = main(["qec-demo", "--output-dir", str(out_dir)])
    assert code == 0
    assert (out_dir / "qec_demo_manifest.json").exists()

    spec, artifacts = _prepared_spec("test_v4_1_cli_production_qec")
    code = main([
        "production-qec-estimate",
        "--config", artifacts["config_path"],
        "--code", "repetition3",
        "--max-components", "2",
        "--shots", "64",
    ])
    assert code == 0
    assert (Path(spec.output_dir) / "qec_logical_estimator" / "production_qec_estimator_manifest.json").exists()

if __name__ == "__main__":
    test_default_codes()
    test_logical_mapping()
    test_component_mapping_and_syndromes()
    test_logical_estimate()
    test_qec_demo()
    test_production_qec_estimator()
    test_cli_qec_commands()
    print("All v4.1 initial QEC/logical extension tests passed.")
