from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    default_single_qubit_calibration,
    invert_2x2,
    apply_readout_mitigation_to_binary_probs,
    mitigate_expectation_value,
    synthetic_noise_scaled_derivatives,
    linear_zne_extrapolate,
    allocate_derivative_shots,
    run_derivative_mitigation_demo,
    init_production_project,
    load_production_spec,
    save_production_spec,
    run_production_mitigated_derivatives,
)
from azmqos_research.cli import main

def test_matrix_inverse():
    inv = invert_2x2([[1.0, 0.0], [0.0, 1.0]])
    assert inv == [[1.0, -0.0], [-0.0, 1.0]]

def test_readout_mitigation_probs():
    cal = default_single_qubit_calibration()
    probs = apply_readout_mitigation_to_binary_probs([0.8, 0.2], cal)
    assert abs(sum(probs) - 1.0) < 1e-12
    assert all(0.0 <= x <= 1.0 for x in probs)

def test_mitigate_expectation_value():
    value = mitigate_expectation_value(0.5)
    assert -1.0 <= value <= 1.0

def test_zne_extrapolation():
    points = synthetic_noise_scaled_derivatives(0.2, [1.0, 3.0, 5.0])
    zne = linear_zne_extrapolate(points)
    assert isinstance(zne, float)

def test_derivative_mitigation_demo():
    out_dir = ROOT / "outputs" / "test_v3_9_mitigation_demo"
    result = run_derivative_mitigation_demo(out_dir)
    assert len(result.mitigated_derivatives) == 2
    assert Path(result.artifacts["manifest"]).exists()

def _prepared_spec(tmp_name):
    out_dir = ROOT / "outputs" / tmp_name
    spec, artifacts = init_production_project(out_dir, project_name=tmp_name)
    spec = load_production_spec(artifacts["config_path"])
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    save_production_spec(spec, artifacts["config_path"])
    return spec, artifacts

def test_production_mitigated_derivatives():
    spec, artifacts = _prepared_spec("test_v3_9_production_mitigated")
    result = run_production_mitigated_derivatives(
        artifacts["config_path"],
        backend="fallback",
        max_components=2,
        shots=64,
    )
    assert len(result.mitigated_derivatives) == 8
    assert Path(result.artifacts["manifest"]).exists()
    assert Path(result.artifacts["M_mitigated_derivatives_csv"]).exists()

def test_cli_mitigation_commands():
    out_dir = ROOT / "outputs" / "test_v3_9_cli_mitigation_demo"
    code = main(["derivative-mitigation-demo", "--output-dir", str(out_dir)])
    assert code == 0
    assert (out_dir / "derivative_mitigation_demo_manifest.json").exists()

    spec, artifacts = _prepared_spec("test_v3_9_cli_production_mitigated")
    code = main([
        "production-mitigated-derivatives",
        "--config", artifacts["config_path"],
        "--backend", "fallback",
        "--max-components", "2",
        "--shots", "64",
    ])
    assert code == 0
    assert (Path(spec.output_dir) / "derivative_mitigation" / "production_mitigated_derivatives_manifest.json").exists()

if __name__ == "__main__":
    test_matrix_inverse()
    test_readout_mitigation_probs()
    test_mitigate_expectation_value()
    test_zne_extrapolation()
    test_derivative_mitigation_demo()
    test_production_mitigated_derivatives()
    test_cli_mitigation_commands()
    print("All v3.9 derivative error mitigation tests passed.")
