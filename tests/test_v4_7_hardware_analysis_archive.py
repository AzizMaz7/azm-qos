from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
import json
from azmqos_research import (
    wilson_interval,
    default_calibration_metadata,
    load_backend_calibration,
    run_hardware_analysis_demo,
    init_production_project,
    load_production_spec,
    save_production_spec,
    run_production_hardware_analysis,
)
from azmqos_research.cli import main

def test_wilson_interval():
    p, lo, hi = wilson_interval(50, 100)
    assert 0.0 <= lo <= p <= hi <= 1.0

def test_calibration_load_default():
    default = default_calibration_metadata("ibm_fez")
    assert default.backend_name == "ibm_fez"
    out_dir = ROOT / "outputs" / "test_v4_7_calibration"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "cal.json"
    path.write_text(json.dumps({"backend_name": "ibm_fez", "median_readout_error": 0.01}), encoding="utf-8")
    loaded = load_backend_calibration(path)
    assert loaded.median_readout_error == 0.01

def test_hardware_analysis_demo():
    out_dir = ROOT / "outputs" / "test_v4_7_analysis_demo"
    result = run_hardware_analysis_demo(out_dir, backend_name="ibm_fez", rounds=2, shots=64)
    assert result.run_summary.total_records >= 1
    assert len(result.count_intervals) >= 1
    assert Path(result.artifacts["final_qec_experiment_archive"]).exists()

def _prepared_spec(tmp_name):
    out_dir = ROOT / "outputs" / tmp_name
    spec, artifacts = init_production_project(out_dir, project_name=tmp_name)
    spec = load_production_spec(artifacts["config_path"])
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    save_production_spec(spec, artifacts["config_path"])
    return spec, artifacts

def test_production_hardware_analysis():
    spec, artifacts = _prepared_spec("test_v4_7_production_analysis")
    result = run_production_hardware_analysis(
        artifacts["config_path"],
        backend_name="ibm_fez",
        code_name="repetition3",
        max_components=2,
        shots=64,
        rounds=2,
    )
    assert result.run_summary.total_records >= 1
    assert Path(result.artifacts["manifest"]).exists()
    assert Path(result.artifacts["production_final_qec_experiment_archive"]).exists()

def test_cli_hardware_analysis_commands():
    out_dir = ROOT / "outputs" / "test_v4_7_cli_analysis_demo"
    code = main([
        "hardware-analysis-demo",
        "--output-dir", str(out_dir),
        "--backend-name", "ibm_fez",
        "--rounds", "2",
        "--shots", "64",
    ])
    assert code == 0
    assert (out_dir / "hardware_analysis" / "hardware_analysis_manifest.json").exists()

    spec, artifacts = _prepared_spec("test_v4_7_cli_production_analysis")
    code = main([
        "production-hardware-analysis",
        "--config", artifacts["config_path"],
        "--backend-name", "ibm_fez",
        "--code", "repetition3",
        "--max-components", "2",
        "--shots", "64",
        "--rounds", "2",
    ])
    assert code == 0
    assert (Path(spec.output_dir) / "hardware_analysis" / "production_hardware_analysis_manifest.json").exists()

if __name__ == "__main__":
    test_wilson_interval()
    test_calibration_load_default()
    test_hardware_analysis_demo()
    test_production_hardware_analysis()
    test_cli_hardware_analysis_commands()
    print("All v4.7 hardware-analysis/archive tests passed.")
