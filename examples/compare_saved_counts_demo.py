from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    compare_counts,
    save_counts_comparison_csv,
    plot_counts_comparison,
    make_hardware_comparison_markdown_report,
    HardwareComparisonReportData,
)

print("AZM-QOS v2.4 Updated: Saved Counts Comparison Demo")
print("=" * 70)

# Replace these dictionaries with your real simulator and hardware counts.
simulator_counts = {"00": 510, "11": 514}
hardware_counts = {"00": 470, "01": 30, "10": 34, "11": 490}

comparison = compare_counts(simulator_counts, hardware_counts)
print(comparison.summary())

out_dir = ROOT / "outputs" / "compare_saved_counts_demo"
out_dir.mkdir(parents=True, exist_ok=True)

csv_path = save_counts_comparison_csv(comparison, out_dir / "counts_comparison.csv")
fig_path = plot_counts_comparison(comparison, out_dir / "counts_comparison.png")

report_data = HardwareComparisonReportData(
    counts_comparison=comparison,
    job_metadata={"source": "saved_counts_demo"},
    artifacts={
        "counts_comparison_csv": str(csv_path),
        "counts_comparison_figure": str(fig_path),
    },
)

report_path = make_hardware_comparison_markdown_report(
    report_data,
    out_dir / "hardware_comparison_report.md",
)

print("Saved report:", report_path)
