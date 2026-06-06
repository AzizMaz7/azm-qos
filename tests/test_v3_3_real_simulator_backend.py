from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import init_production_project, load_production_spec, save_production_spec, make_production_plan, production_plan_to_workloads, workload_to_circuit_spec, exact_expectation_from_circuit_spec, run_fallback_simulator, expectation_from_binary_counts, run_production_simulator_batch, run_production_shot_scaling
from azmqos_research.cli import main

def _prepared_spec(tmp_name):
    out_dir = ROOT / "outputs" / tmp_name
    spec, artifacts = init_production_project(out_dir, project_name=tmp_name)
    spec = load_production_spec(artifacts["config_path"])
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    save_production_spec(spec, artifacts["config_path"])
    return spec, artifacts

def test_workload_to_circuit():
    spec, artifacts = _prepared_spec("test_v3_3_workload_to_circuit")
    plan = make_production_plan(spec)
    workloads = production_plan_to_workloads(plan, spec)
    circuit = workload_to_circuit_spec(workloads[0])
    exact = exact_expectation_from_circuit_spec(circuit)
    assert circuit.n_qubits == 1
    assert -1.0 <= exact <= 1.0

def test_fallback_simulator_counts():
    spec, artifacts = _prepared_spec("test_v3_3_fallback_counts")
    plan = make_production_plan(spec)
    workload = production_plan_to_workloads(plan, spec)[0]
    circuit = workload_to_circuit_spec(workload)
    counts = run_fallback_simulator(circuit, shots=128)
    assert sum(counts.values()) == 128
    exp = expectation_from_binary_counts(counts)
    assert -1.0 <= exp <= 1.0

def test_production_simulator_batch():
    spec, artifacts = _prepared_spec("test_v3_3_batch")
    result = run_production_simulator_batch(artifacts["config_path"], backend="fallback", shots=256)
    assert len(result.comparisons) == len(result.workloads)
    assert Path(result.artifacts["production_simulator_manifest"]).exists()
    assert Path(result.artifacts["dashboard_html"]).exists()

def test_production_shot_scaling():
    spec, artifacts = _prepared_spec("test_v3_3_scaling")
    result = run_production_shot_scaling(artifacts["config_path"], shot_powers=(6, 8), backend="fallback")
    assert len(result["points"]) >= 2
    assert Path(result["manifest"]).exists()
    assert Path(result["csv"]).exists()

def test_cli_production_simulate():
    spec, artifacts = _prepared_spec("test_v3_3_cli_sim")
    code = main(["production-simulate", "--config", artifacts["config_path"], "--backend", "fallback", "--shots", "128"])
    assert code == 0
    assert (Path(spec.output_dir) / "simulator" / "production_simulator_manifest.json").exists()

def test_cli_production_shot_scaling():
    spec, artifacts = _prepared_spec("test_v3_3_cli_scaling")
    code = main(["production-shot-scaling", "--config", artifacts["config_path"], "--backend", "fallback"])
    assert code == 0
    assert (Path(spec.output_dir) / "simulator" / "shot_scaling" / "production_shot_scaling_manifest.json").exists()

if __name__ == "__main__":
    test_workload_to_circuit()
    test_fallback_simulator_counts()
    test_production_simulator_batch()
    test_production_shot_scaling()
    test_cli_production_simulate()
    test_cli_production_shot_scaling()
    print("All v3.3 real simulator backend tests passed.")
