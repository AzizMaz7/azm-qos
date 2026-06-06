from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import IBMRuntimeConfig, run_sampler_v2_job, diagnose_ibm_runtime, make_ibm_runtime_report

print("AZM-QOS v2.3 IBM Dry-Run Submission Demo")
print("=" * 70)

config = IBMRuntimeConfig(backend_name=None, shots=1024, dry_run=True)
submission = run_sampler_v2_job(config=config)
diagnostics = diagnose_ibm_runtime(config)

out_dir = ROOT / "outputs" / "ibm_dry_run_submission_demo"
out_dir.mkdir(parents=True, exist_ok=True)
report_path = make_ibm_runtime_report(diagnostics, out_dir / "ibm_dry_run_report.md", submission_result=submission)

print(submission.summary())
print()
print("Saved report:", report_path)
