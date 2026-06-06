from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import create_demo_run_database, make_artifact_browser_html, export_artifact_index_csv

print("AZM-QOS v2.8 Artifact Browser Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "artifact_browser_demo"
db, records, _ = create_demo_run_database(out_dir / "database")

csv_path = export_artifact_index_csv(records, out_dir / "artifact_index.csv")
html_path = make_artifact_browser_html(records, out_dir / "artifact_browser.html")

print("CSV:", csv_path)
print("HTML:", html_path)
