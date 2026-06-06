from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import create_demo_run_database, collect_metric_trend, export_metric_trend_csv, plot_metric_trend

print("AZM-QOS v2.8 Metric Trend Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "metric_trend_demo"
db, records, _ = create_demo_run_database(out_dir / "database")

trend = collect_metric_trend(records, "expectation")
csv_path = export_metric_trend_csv(trend, out_dir / "expectation_trend.csv")
fig_path = plot_metric_trend(trend, out_dir / "expectation_trend.png")

print(trend.summary())
print("CSV:", csv_path)
print("Figure:", fig_path)
