from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    PauliTerm,
    PauliComponent,
    QiskitExecutionConfig,
    compile_pauli_component,
    build_circuit_or_fallback_spec,
    normalize_qiskit_counts,
    execute_component_with_qiskit_or_fallback,
    init_production_project,
    load_production_spec,
    save_production_spec,
    run_production_qiskit_execution,
)
from azmqos_research.cli import main

def test_normalize_qiskit_counts():
    counts = normalize_qiskit_counts({"01": 3, "10": 5}, n_qubits=2, reverse_bitstrings=True)
    assert counts == {"10": 3, "01": 5}

def test_build_circuit_or_fallback():
    component = PauliComponent(
        name="test_component",
        quantity="M",
        indices=[0, 0],
        terms=[PauliTerm(1.0, "ZI"), PauliTerm(0.5, "IZ")],
    )
    compiled = compile_pauli_component(component)
    spec, build, qc = build_circuit_or_fallback_spec(component, compiled.groups[0])
    assert build.n_qubits == len(compiled.groups[0].measurement_basis)
    assert build.measurement_basis == compiled.groups[0].measurement_basis

def test_execute_component_fallback():
    component = PauliComponent(
        name="test_component_fallback",
        quantity="M",
        indices=[0, 0],
        terms=[PauliTerm(1.0, "ZI"), PauliTerm(0.5, "IZ"), PauliTerm(0.25, "XX")],
        metadata={"component_family": "Mbb"},
    )
    config = QiskitExecutionConfig(backend="fallback", shots=256)
    result = execute_component_with_qiskit_or_fallback(component, config)
    assert len(result.group_results) >= 2
    assert result.component_estimate.n_terms == 3

def test_execute_component_hardware_dry_run():
    component = PauliComponent(
        name="test_component_hw_dry",
        quantity="M",
        indices=[0, 0],
        terms=[PauliTerm(1.0, "ZI"), PauliTerm(0.25, "XX")],
        metadata={"component_family": "Mbb"},
    )
    config = QiskitExecutionConfig(backend="hardware_dry_run", shots=128, hardware_backend_name="ibm_fez")
    result = execute_component_with_qiskit_or_fallback(component, config)
    assert all(group.status == "dry_run_prepared" for group in result.group_results)
    assert all(group.job_id is not None for group in result.group_results)

def _prepared_spec(tmp_name):
    out_dir = ROOT / "outputs" / tmp_name
    spec, artifacts = init_production_project(out_dir, project_name=tmp_name)
    spec = load_production_spec(artifacts["config_path"])
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    save_production_spec(spec, artifacts["config_path"])
    return spec, artifacts

def test_run_production_qiskit_execution():
    spec, artifacts = _prepared_spec("test_v3_6_qiskit_execution")
    result = run_production_qiskit_execution(
        artifacts["config_path"],
        backend="fallback",
        max_components=2,
        shots=128,
    )
    assert len(result.component_estimates) == 2
    assert Path(result.artifacts["production_qiskit_execution_manifest"]).exists()
    assert Path(result.artifacts["dashboard_html"]).exists()

def test_cli_production_qiskit_execute():
    spec, artifacts = _prepared_spec("test_v3_6_cli_qiskit")
    code = main([
        "production-qiskit-execute",
        "--config", artifacts["config_path"],
        "--backend", "fallback",
        "--shots", "128",
        "--max-components", "2",
    ])
    assert code == 0
    assert (Path(spec.output_dir) / "qiskit_pauli_execution" / "production_qiskit_execution_manifest.json").exists()

if __name__ == "__main__":
    test_normalize_qiskit_counts()
    test_build_circuit_or_fallback()
    test_execute_component_fallback()
    test_execute_component_hardware_dry_run()
    test_run_production_qiskit_execution()
    test_cli_production_qiskit_execute()
    print("All v3.6 Qiskit Pauli execution tests passed.")
