from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    IBMRuntimeConfig,
    diagnose_ibm_runtime,
    run_sampler_v2_job,
    make_ibm_runtime_report,
    hardware_vs_simulator_comparison_scaffold,
)
from azmqos_research.cli import main

def test_ibm_config_summary():
    config = IBMRuntimeConfig(backend_name="demo_backend", shots=128, dry_run=True)
    assert "demo_backend" in config.summary()

def test_diagnostics_safe():
    diagnostics = diagnose_ibm_runtime(IBMRuntimeConfig())
    assert hasattr(diagnostics, "qiskit_installed")
    assert hasattr(diagnostics, "message")

def test_sampler_dry_run():
    result = run_sampler_v2_job(config=IBMRuntimeConfig(backend_name="demo_backend", shots=128, dry_run=True))
    assert result.dry_run is True
    assert result.status == "dry_run"

def test_report_generation():
    out_dir = ROOT / "outputs" / "test_v2_3_ibm_report"
    out_dir.mkdir(parents=True, exist_ok=True)
    diagnostics = diagnose_ibm_runtime(IBMRuntimeConfig())
    submission = run_sampler_v2_job(config=IBMRuntimeConfig(dry_run=True))
    report = make_ibm_runtime_report(diagnostics, out_dir / "ibm_report.md", submission_result=submission)
    assert Path(report).exists()

def test_cli_ibm_dry_run():
    out_dir = ROOT / "outputs" / "test_v2_3_cli_ibm"
    code = main(["ibm-dry-run", "--output-dir", str(out_dir), "--shots", "128"])
    assert code == 0
    assert (out_dir / "ibm_runtime_dry_run_report.md").exists()

def test_comparison_scaffold():
    comparison = hardware_vs_simulator_comparison_scaffold(simulator_result={"counts": {"0": 10}}, hardware_result=None)
    assert comparison["status"] == "pending_hardware_result"

if __name__ == "__main__":
    test_ibm_config_summary()
    test_diagnostics_safe()
    test_sampler_dry_run()
    test_report_generation()
    test_cli_ibm_dry_run()
    test_comparison_scaffold()
    print("All v2.3 IBM Runtime path tests passed.")
