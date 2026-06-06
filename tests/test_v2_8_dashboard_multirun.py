from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    create_demo_run_database,
    collect_metric_trend,
    backend_performance_history,
    export_artifact_index_csv,
    make_artifact_browser_html,
    build_dashboard_package,
)
from azmqos_research.cli import main

def test_metric_trend():
    out_dir = ROOT / "outputs" / "test_v2_8_metric_trend"
    db, records, _ = create_demo_run_database(out_dir / "database")
    trend = collect_metric_trend(records, "expectation")
    assert len(trend.points) == 2
    assert trend.metric_name == "expectation"

def test_backend_history():
    out_dir = ROOT / "outputs" / "test_v2_8_backend_history"
    db, records, _ = create_demo_run_database(out_dir / "database")
    history = backend_performance_history(records)
    assert len(history) == 1
    assert history[0].backend_name == "mock_ibm_backend"

def test_artifact_browser():
    out_dir = ROOT / "outputs" / "test_v2_8_artifact_browser"
    db, records, _ = create_demo_run_database(out_dir / "database")
    csv_path = export_artifact_index_csv(records, out_dir / "artifact_index.csv")
    html_path = make_artifact_browser_html(records, out_dir / "artifact_browser.html")
    assert Path(csv_path).exists()
    assert Path(html_path).exists()

def test_dashboard_package():
    out_dir = ROOT / "outputs" / "test_v2_8_dashboard_package"
    package = build_dashboard_package(out_dir)
    assert package.records_count == 2
    assert Path(package.artifacts["dashboard_html"]).exists()
    assert Path(package.artifacts["artifact_browser_html"]).exists()
    assert Path(package.artifacts["manifest"]).exists()

def test_cli_dashboard_demo():
    out_dir = ROOT / "outputs" / "test_v2_8_cli_dashboard"
    code = main(["dashboard-demo", "--output-dir", str(out_dir)])
    assert code == 0
    assert (out_dir / "dashboard.html").exists()
    assert (out_dir / "dashboard_manifest.json").exists()

if __name__ == "__main__":
    test_metric_trend()
    test_backend_history()
    test_artifact_browser()
    test_dashboard_package()
    test_cli_dashboard_demo()
    print("All v2.8 dashboard/multi-run tests passed.")
