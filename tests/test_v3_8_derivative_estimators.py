from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    DerivativeParameter,
    DerivativeEstimatorConfig,
    ENDVQSStatePreparationConfig,
    get_parameter_value,
    shifted_stateprep_config,
    PauliComponent,
    PauliTerm,
    estimate_component_derivative,
    estimate_component_derivatives,
    run_derivative_demo,
    init_production_project,
    load_production_spec,
    save_production_spec,
    run_production_derivative_estimators,
)
from azmqos_research.cli import main

def test_parameter_get_shift():
    cfg = ENDVQSStatePreparationConfig()
    p = DerivativeParameter("p", 0)
    old = get_parameter_value(cfg, p)
    shifted = shifted_stateprep_config(cfg, p, 0.5)
    assert abs(get_parameter_value(shifted, p) - (old + 0.5)) < 1e-12

def test_component_derivative_single():
    component = PauliComponent(
        name="test_derivative_component",
        quantity="M",
        indices=[0, 0],
        terms=[PauliTerm(0.5, "ZI"), PauliTerm(0.1, "XX")],
        metadata={"component_family": "Mbb"},
    )
    config = DerivativeEstimatorConfig(parameters=[DerivativeParameter("p", 0)], shots=64, backend="fallback")
    estimate = estimate_component_derivative(component, ENDVQSStatePreparationConfig(), DerivativeParameter("p", 0), config)
    assert estimate.parameter.name == "p"
    assert estimate.shots == 64

def test_component_derivatives_multiple():
    component = PauliComponent(
        name="test_derivative_component_multi",
        quantity="V",
        indices=[0],
        terms=[PauliTerm(0.5, "Z"), PauliTerm(0.1, "X")],
        metadata={"component_family": "Va"},
    )
    config = DerivativeEstimatorConfig(parameters=[DerivativeParameter("p", 0), DerivativeParameter("q", 0)], shots=64, backend="fallback")
    estimates = estimate_component_derivatives(component, ENDVQSStatePreparationConfig(), config)
    assert len(estimates) == 2

def test_derivative_demo():
    out_dir = ROOT / "outputs" / "test_v3_8_derivative_demo"
    result = run_derivative_demo(out_dir)
    assert len(result.component_derivatives) == 2
    assert Path(result.artifacts["manifest"]).exists()

def _prepared_spec(tmp_name):
    out_dir = ROOT / "outputs" / tmp_name
    spec, artifacts = init_production_project(out_dir, project_name=tmp_name)
    spec = load_production_spec(artifacts["config_path"])
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    save_production_spec(spec, artifacts["config_path"])
    return spec, artifacts

def test_production_derivatives():
    spec, artifacts = _prepared_spec("test_v3_8_production_derivatives")
    result = run_production_derivative_estimators(
        artifacts["config_path"],
        backend="fallback",
        max_components=2,
        shots=64,
    )
    assert len(result.component_derivatives) == 8
    assert Path(result.artifacts["manifest"]).exists()
    assert Path(result.artifacts["M_derivatives_csv"]).exists()

def test_cli_derivative_commands():
    out_dir = ROOT / "outputs" / "test_v3_8_cli_derivative_demo"
    code = main(["derivative-demo", "--output-dir", str(out_dir)])
    assert code == 0
    assert (out_dir / "derivative_demo_manifest.json").exists()

    spec, artifacts = _prepared_spec("test_v3_8_cli_production_derivatives")
    code = main([
        "production-derivatives",
        "--config", artifacts["config_path"],
        "--backend", "fallback",
        "--max-components", "2",
        "--shots", "64",
    ])
    assert code == 0
    assert (Path(spec.output_dir) / "derivative_estimators" / "production_derivatives_manifest.json").exists()

if __name__ == "__main__":
    test_parameter_get_shift()
    test_component_derivative_single()
    test_component_derivatives_multiple()
    test_derivative_demo()
    test_production_derivatives()
    test_cli_derivative_commands()
    print("All v3.8 derivative estimator tests passed.")
