from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    HardwareJobReference,
    normalize_counts,
    total_variation_distance,
    synthetic_hardware_counts_for_job,
    compare_dry_run_to_hardware,
    sync_hardware_results,
    run_qec_hardware_sync_demo,
    init_production_project,
    load_production_spec,
    save_production_spec,
    run_production_qec_hardware_sync,
)
from azmqos_research.cli import main

def test_counts_normalization_and_tvd():
    counts = normalize_counts({"0": 10, " 1": 5}, n_bits=1)
    assert counts == {"0": 10, "1": 5}
    assert abs(total_variation_distance({"0": 10}, {"0": 10})) < 1e-12

def test_synthetic_counts_and_compare():
    job = HardwareJobReference(job_id="job1", backend_name="ibm_fez", circuit_id="c0", shots=100)
    record = synthetic_hardware_counts_for_job(job)
    assert sum(record.counts.values()) == 100
    comp = compare_dry_run_to_hardware(job, record)
    assert comp.job_id == "job1"
    assert 0.0 <= comp.total_variation_distance <= 1.0

def test_sync_hardware_results():
    jobs = [
        HardwareJobReference(job_id="job1", backend_name="ibm_fez", circuit_id="c0", shots=64),
        HardwareJobReference(job_id="job2", backend_name="ibm_fez", circuit_id="c1", shots=64),
    ]
    records, comparisons = sync_hardware_results(jobs)
    assert len(records) == 2
    assert len(comparisons) == 2

def test_hardware_sync_demo():
    out_dir = ROOT / "outputs" / "test_v4_5_sync_demo"
    result = run_qec_hardware_sync_demo(out_dir, backend_name="ibm_fez", rounds=2, shots=64)
    assert len(result.comparisons) >= 1
    assert Path(result.artifacts["manifest"]).exists()

def _prepared_spec(tmp_name):
    out_dir = ROOT / "outputs" / tmp_name
    spec, artifacts = init_production_project(out_dir, project_name=tmp_name)
    spec = load_production_spec(artifacts["config_path"])
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    save_production_spec(spec, artifacts["config_path"])
    return spec, artifacts

def test_production_hardware_sync():
    spec, artifacts = _prepared_spec("test_v4_5_production_sync")
    result = run_production_qec_hardware_sync(
        artifacts["config_path"],
        backend_name="ibm_fez",
        code_name="repetition3",
        max_components=2,
        shots=64,
        rounds=2,
    )
    assert len(result.comparisons) >= 1
    assert Path(result.artifacts["manifest"]).exists()
    assert Path(result.artifacts["sync_comparisons_csv"]).exists()

def test_cli_sync_commands():
    out_dir = ROOT / "outputs" / "test_v4_5_cli_sync_demo"
    code = main([
        "qec-hardware-sync-demo",
        "--output-dir", str(out_dir),
        "--backend-name", "ibm_fez",
        "--rounds", "2",
        "--shots", "64",
    ])
    assert code == 0
    assert (out_dir / "qec_hardware_sync_demo_manifest.json").exists()

    spec, artifacts = _prepared_spec("test_v4_5_cli_production_sync")
    code = main([
        "production-qec-hardware-sync",
        "--config", artifacts["config_path"],
        "--backend-name", "ibm_fez",
        "--code", "repetition3",
        "--max-components", "2",
        "--shots", "64",
        "--rounds", "2",
    ])
    assert code == 0
    assert (Path(spec.output_dir) / "qec_hardware_sync" / "production_qec_hardware_sync_manifest.json").exists()

if __name__ == "__main__":
    test_counts_normalization_and_tvd()
    test_synthetic_counts_and_compare()
    test_sync_hardware_results()
    test_hardware_sync_demo()
    test_production_hardware_sync()
    test_cli_sync_commands()
    print("All v4.5 hardware result sync tests passed.")
