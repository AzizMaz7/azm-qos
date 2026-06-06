from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    HardwareJobReference,
    RuntimeFetchConfig,
    runtime_package_available,
    cache_key_for_job,
    fetch_job_with_retry,
    fetch_jobs_with_runtime_adapter,
    run_runtime_fetch_demo,
    init_production_project,
    load_production_spec,
    save_production_spec,
    run_production_runtime_sync,
)
from azmqos_research.cli import main

def test_runtime_availability_bool():
    assert isinstance(runtime_package_available(), bool)

def test_cache_key_and_fetch():
    job = HardwareJobReference(job_id="job_cache_test", backend_name="ibm_fez", circuit_id="c0", shots=64)
    key = cache_key_for_job(job)
    assert len(key) == 24
    config = RuntimeFetchConfig(enable_runtime_fetch=False, use_cache=True)
    cache_dir = ROOT / "outputs" / "test_v4_6_cache" / "cache"
    first = fetch_job_with_retry(job, config, cache_dir=cache_dir)
    second = fetch_job_with_retry(job, config, cache_dir=cache_dir)
    assert first.counts_record.shots == 64
    assert second.cached is True

def test_fetch_jobs_adapter_synthetic():
    jobs = [
        HardwareJobReference(job_id="job1", backend_name="ibm_fez", circuit_id="c0", shots=64),
        HardwareJobReference(job_id="job2", backend_name="ibm_fez", circuit_id="c1", shots=64),
    ]
    config = RuntimeFetchConfig(enable_runtime_fetch=False)
    records = fetch_jobs_with_runtime_adapter(jobs, config)
    assert len(records) == 2
    assert all("synthetic" in r.source for r in records)

def test_runtime_fetch_demo():
    out_dir = ROOT / "outputs" / "test_v4_6_runtime_demo"
    result = run_runtime_fetch_demo(out_dir, backend_name="ibm_fez", rounds=2, shots=64)
    assert len(result.fetch_records) >= 1
    assert Path(result.artifacts["manifest"]).exists()

def _prepared_spec(tmp_name):
    out_dir = ROOT / "outputs" / tmp_name
    spec, artifacts = init_production_project(out_dir, project_name=tmp_name)
    spec = load_production_spec(artifacts["config_path"])
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    save_production_spec(spec, artifacts["config_path"])
    return spec, artifacts

def test_production_runtime_sync():
    spec, artifacts = _prepared_spec("test_v4_6_production_runtime")
    result = run_production_runtime_sync(
        artifacts["config_path"],
        backend_name="ibm_fez",
        code_name="repetition3",
        max_components=2,
        shots=64,
        rounds=2,
    )
    assert len(result.fetch_records) >= 1
    assert Path(result.artifacts["manifest"]).exists()
    assert Path(result.artifacts["runtime_fetch_records_csv"]).exists()

def test_cli_runtime_commands():
    out_dir = ROOT / "outputs" / "test_v4_6_cli_runtime_demo"
    code = main([
        "runtime-fetch-demo",
        "--output-dir", str(out_dir),
        "--backend-name", "ibm_fez",
        "--rounds", "2",
        "--shots", "64",
    ])
    assert code == 0
    assert (out_dir / "runtime_fetch_demo_manifest.json").exists()

    spec, artifacts = _prepared_spec("test_v4_6_cli_production_runtime")
    code = main([
        "production-runtime-sync",
        "--config", artifacts["config_path"],
        "--backend-name", "ibm_fez",
        "--code", "repetition3",
        "--max-components", "2",
        "--shots", "64",
        "--rounds", "2",
    ])
    assert code == 0
    assert (Path(spec.output_dir) / "runtime_sync" / "production_runtime_sync_manifest.json").exists()

if __name__ == "__main__":
    test_runtime_availability_bool()
    test_cache_key_and_fetch()
    test_fetch_jobs_adapter_synthetic()
    test_runtime_fetch_demo()
    test_production_runtime_sync()
    test_cli_runtime_commands()
    print("All v4.6 IBM Runtime fetch tests passed.")
