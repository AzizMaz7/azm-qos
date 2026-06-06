from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import PauliTerm, PauliComponent, deterministic_counts_for_basis, execute_component_pauli_measurements, init_production_project, load_production_spec, save_production_spec, run_production_pauli_execution
from azmqos_research.cli import main

def test_deterministic_counts_for_basis():
    counts = deterministic_counts_for_basis("test_component", "ZZ", shots=128)
    assert sum(counts.values()) == 128
    assert set(counts).issubset({"00", "01", "10", "11"})

def test_execute_component_pauli_measurements():
    component = PauliComponent(name="test_component", quantity="M", indices=[0, 0], terms=[PauliTerm(1.0, "ZI"), PauliTerm(0.5, "IZ"), PauliTerm(0.25, "XX")], metadata={"component_family": "Mbb"})
    compilation, estimate = execute_component_pauli_measurements(component, shots_per_group=256)
    assert len(compilation.groups) >= 2
    assert estimate.n_terms == 3
    assert estimate.n_groups == len(compilation.groups)

def _prepared_spec(tmp_name):
    out_dir = ROOT / "outputs" / tmp_name
    spec, artifacts = init_production_project(out_dir, project_name=tmp_name)
    spec = load_production_spec(artifacts["config_path"])
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    save_production_spec(spec, artifacts["config_path"])
    return spec, artifacts

def test_run_production_pauli_execution():
    spec, artifacts = _prepared_spec("test_v3_5_pauli_execution")
    result = run_production_pauli_execution(artifacts["config_path"], shots_per_group=256)
    assert len(result.component_estimates) >= 1
    assert Path(result.artifacts["production_pauli_execution_manifest"]).exists()
    assert Path(result.artifacts["M_estimates_csv"]).exists()
    assert Path(result.artifacts["V_estimates_csv"]).exists()
    assert Path(result.artifacts["dashboard_html"]).exists()

def test_run_production_pauli_execution_max_components():
    spec, artifacts = _prepared_spec("test_v3_5_pauli_execution_max")
    result = run_production_pauli_execution(artifacts["config_path"], max_components=2, shots_per_group=128)
    assert len(result.component_estimates) == 2

def test_cli_production_pauli_execute():
    spec, artifacts = _prepared_spec("test_v3_5_cli_pauli")
    code = main(["production-pauli-execute", "--config", artifacts["config_path"], "--shots", "128", "--max-components", "2"])
    assert code == 0
    assert (Path(spec.output_dir) / "pauli_execution" / "production_pauli_execution_manifest.json").exists()

if __name__ == "__main__":
    test_deterministic_counts_for_basis()
    test_execute_component_pauli_measurements()
    test_run_production_pauli_execution()
    test_run_production_pauli_execution_max_components()
    test_cli_production_pauli_execute()
    print("All v3.5 production Pauli execution tests passed.")
