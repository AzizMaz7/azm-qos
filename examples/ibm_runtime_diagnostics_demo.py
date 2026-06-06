from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import IBMRuntimeConfig, diagnose_ibm_runtime, make_ibm_runtime_report

print("AZM-QOS v2.3 IBM Runtime Diagnostics Demo")
print("=" * 70)

config = IBMRuntimeConfig()
diagnostics = diagnose_ibm_runtime(config)

out_dir = ROOT / "outputs" / "ibm_runtime_diagnostics_demo"
out_dir.mkdir(parents=True, exist_ok=True)
report_path = make_ibm_runtime_report(diagnostics, out_dir / "ibm_runtime_report.md")

print(diagnostics.summary())
print()
print("Saved report:", report_path)
