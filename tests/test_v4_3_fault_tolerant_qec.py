from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    get_code_by_name,
    CircuitNoiseModel,
    make_syndrome_extraction_circuit_spec,
    make_repeated_syndrome_schedule,
    effective_round_error_probability,
    simulate_repeated_syndrome_rounds,
    estimate_logical_failure_rate,
    run_ft_qec_demo,
    init_production_project,
    load_production_spec,
    save_production_spec,
    run_production_ft_qec,
)
from azmqos_research.cli import main

def test_syndrome_specs():
    code = get_code_by_name("repetition3")
    spec = make_syndrome_extraction_circuit_spec(code, stabilizer_index=0, round_index=0)
    assert spec.code_name == code.name
    assert len(spec.operations) >= 2

def test_repeated_schedule():
    code = get_code_by_name("repetition3")
    schedule = make_repeated_syndrome_schedule(code, rounds=3)
    assert len(schedule) == 3 * len(code.stabilizers)

def test_noise_and_rounds():
    code = get_code_by_name("repetition3")
    noise = CircuitNoiseModel(data_error_rate=0.02, measurement_error_rate=0.03)
    p = effective_round_error_probability(noise, code)
    assert 0.0 <= p <= 1.0
    rounds = simulate_repeated_syndrome_rounds("test_component", code, rounds=3, noise=noise)
    assert len(rounds) == 3
    failure = estimate_logical_failure_rate("test_component", code, rounds=3, noise=noise, shots=16)
    assert 0.0 <= failure <= 1.0

def test_ft_qec_demo():
    out_dir = ROOT / "outputs" / "test_v4_3_ft_demo"
    result = run_ft_qec_demo(out_dir)
    assert len(result.component_results) == 1
    assert Path(result.artifacts["manifest"]).exists()

def _prepared_spec(tmp_name):
    out_dir = ROOT / "outputs" / tmp_name
    spec, artifacts = init_production_project(out_dir, project_name=tmp_name)
    spec = load_production_spec(artifacts["config_path"])
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    save_production_spec(spec, artifacts["config_path"])
    return spec, artifacts

def test_production_ft_qec():
    spec, artifacts = _prepared_spec("test_v4_3_production_ft_qec")
    result = run_production_ft_qec(
        artifacts["config_path"],
        code_name="repetition3",
        max_components=2,
        shots=64,
        rounds=3,
        physical_error_rate=0.02,
        measurement_error_rate=0.03,
    )
    assert len(result.component_results) == 2
    assert Path(result.artifacts["manifest"]).exists()
    assert Path(result.artifacts["M_ft_qec_estimates_csv"]).exists()

def test_cli_ft_qec_commands():
    out_dir = ROOT / "outputs" / "test_v4_3_cli_ft_demo"
    code = main(["ft-qec-demo", "--output-dir", str(out_dir)])
    assert code == 0
    assert (out_dir / "ft_qec_demo_manifest.json").exists()

    spec, artifacts = _prepared_spec("test_v4_3_cli_production_ft_qec")
    code = main([
        "production-ft-qec",
        "--config", artifacts["config_path"],
        "--code", "repetition3",
        "--max-components", "2",
        "--shots", "64",
        "--rounds", "3",
        "--physical-error-rate", "0.02",
        "--measurement-error-rate", "0.03",
    ])
    assert code == 0
    assert (Path(spec.output_dir) / "ft_qec" / "production_ft_qec_manifest.json").exists()

if __name__ == "__main__":
    test_syndrome_specs()
    test_repeated_schedule()
    test_noise_and_rounds()
    test_ft_qec_demo()
    test_production_ft_qec()
    test_cli_ft_qec_commands()
    print("All v4.3 fault-tolerant QEC tests passed.")
