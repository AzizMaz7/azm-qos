from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    ENDVQSStatePreparationConfig,
    ElectronicStateParameters,
    NuclearCoherentParameters,
    ENDVQSLayout,
    make_fukutome_electronic_operations,
    make_nuclear_coherent_operations,
    make_derivative_stateprep_config,
    make_endvqs_stateprep_plan,
    make_component_specific_stateprep_plan,
    PauliComponent,
    PauliTerm,
    make_stateprep_demo,
    run_endvqs_qiskit_component_execution,
    init_production_project,
    load_production_spec,
    save_production_spec,
    run_production_endvqs_execution,
)
from azmqos_research.cli import main

def test_operation_generation():
    layout = ENDVQSLayout(n_electronic_qubits=2, n_nuclear_qubits=2)
    eops = make_fukutome_electronic_operations(ElectronicStateParameters(), layout)
    nops = make_nuclear_coherent_operations(NuclearCoherentParameters(), layout)
    assert len(eops) >= 4
    assert len(nops) == 4

def test_derivative_plan():
    base = ENDVQSStatePreparationConfig()
    cfg = make_derivative_stateprep_config(base, derivative="p", derivative_index=0)
    plan = make_endvqs_stateprep_plan(cfg)
    assert plan.config.derivative == "p"
    assert plan.operations[-1].label.startswith("derivative_p")

def test_component_specific_plan():
    component = PauliComponent(
        name="test_Mbb",
        quantity="M",
        indices=[0, 1],
        terms=[PauliTerm(1.0, "ZI")],
        metadata={"component_family": "Mbb"},
    )
    plan = make_component_specific_stateprep_plan(ENDVQSStatePreparationConfig(), component)
    assert plan.component_name == "test_Mbb"
    assert plan.config.derivative in {"q", "alpha", "p", "beta"}

def test_stateprep_demo():
    out_dir = ROOT / "outputs" / "test_v3_7_stateprep_demo"
    plan, artifacts = make_stateprep_demo(out_dir)
    assert Path(artifacts["manifest"]).exists()
    assert len(plan.operations) >= 1

def test_component_execution_fallback():
    component = PauliComponent(
        name="test_exec_component",
        quantity="M",
        indices=[0, 0],
        terms=[PauliTerm(1.0, "ZI"), PauliTerm(0.5, "XX")],
        metadata={"component_family": "Mbb"},
    )
    result, execution = run_endvqs_qiskit_component_execution(
        component,
        stateprep_config=ENDVQSStatePreparationConfig(),
        backend="fallback",
        shots=128,
    )
    assert result.component_name == "test_exec_component"
    assert result.backend_used == "fallback"

def _prepared_spec(tmp_name):
    out_dir = ROOT / "outputs" / tmp_name
    spec, artifacts = init_production_project(out_dir, project_name=tmp_name)
    spec = load_production_spec(artifacts["config_path"])
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    save_production_spec(spec, artifacts["config_path"])
    return spec, artifacts

def test_production_endvqs_execution():
    spec, artifacts = _prepared_spec("test_v3_7_production_endvqs")
    result = run_production_endvqs_execution(
        artifacts["config_path"],
        backend="fallback",
        max_components=2,
        shots=128,
    )
    assert len(result["results"]) == 2
    assert Path(result["artifacts"]["manifest"]).exists()

def test_cli_stateprep_and_execution():
    out_dir = ROOT / "outputs" / "test_v3_7_cli_stateprep"
    code = main(["endvqs-stateprep-demo", "--output-dir", str(out_dir)])
    assert code == 0
    assert (out_dir / "stateprep_demo_manifest.json").exists()

    spec, artifacts = _prepared_spec("test_v3_7_cli_endvqs_exec")
    code = main([
        "production-endvqs-execute",
        "--config", artifacts["config_path"],
        "--backend", "fallback",
        "--max-components", "2",
        "--shots", "128",
    ])
    assert code == 0
    assert (Path(spec.output_dir) / "endvqs_stateprep_execution" / "endvqs_stateprep_execution_manifest.json").exists()

if __name__ == "__main__":
    test_operation_generation()
    test_derivative_plan()
    test_component_specific_plan()
    test_stateprep_demo()
    test_component_execution_fallback()
    test_production_endvqs_execution()
    test_cli_stateprep_and_execution()
    print("All v3.7 END/VQS state-preparation tests passed.")
