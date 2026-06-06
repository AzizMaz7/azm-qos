from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    retrieve_ibm_hardware_result,
    compare_counts,
    save_counts_json,
    save_counts_comparison_csv,
    plot_counts_comparison,
    make_hardware_comparison_markdown_report,
    HardwareComparisonReportData,
)

print("AZM-QOS v2.4 Updated: Latest Hardware Result + Simulator Comparison")
print("=" * 70)

# None means latest visible IBM Runtime job from any backend.
# Use backend_name="ibm_fez" or backend_name="ibm_brisbane" to restrict by backend.
hardware = retrieve_ibm_hardware_result(backend_name=None)

print(hardware.summary())
print()

if hardware.counts is None:
    raise RuntimeError("No hardware counts were extracted from the latest IBM Runtime job.")

# Replace this with your actual simulator result for the same circuit.
simulator_counts = {"00": 510, "11": 514}

comparison = compare_counts(simulator_counts, hardware.counts)
print(comparison.summary())

out_dir = ROOT / "outputs" / "retrieve_latest_hardware_and_compare_demo"
out_dir.mkdir(parents=True, exist_ok=True)

hardware_counts_path = save_counts_json(hardware.counts, out_dir / "hardware_counts_latest.json")
csv_path = save_counts_comparison_csv(comparison, out_dir / "counts_comparison.csv")
fig_path = plot_counts_comparison(comparison, out_dir / "counts_comparison.png")

report_data = HardwareComparisonReportData(
    counts_comparison=comparison,
    job_metadata={
        "job_id": hardware.job_id,
        "backend_name": hardware.backend_name,
        "status": hardware.status,
    },
    artifacts={
        "hardware_counts_json": str(hardware_counts_path),
        "counts_comparison_csv": str(csv_path),
        "counts_comparison_figure": str(fig_path),
    },
)

report_path = make_hardware_comparison_markdown_report(
    report_data,
    out_dir / "hardware_comparison_report.md",
)

print()
print("Saved:")
print(" ", hardware_counts_path)
print(" ", csv_path)
print(" ", fig_path)
print(" ", report_path)
