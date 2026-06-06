from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    ExperimentDatabase,
    new_run_record,
    BackendMetadataRecord,
    artifact_from_path,
    export_run_table_csv,
    export_dashboard_json,
    summarize_records,
    create_demo_run_database,
)
from azmqos_research.cli import main

def test_database_append_read_query():
    out_dir = ROOT / "outputs" / "test_v2_7_database"
    out_dir.mkdir(parents=True, exist_ok=True)
    db = ExperimentDatabase(out_dir / "runs.jsonl")

    record = new_run_record(
        name="test_run",
        run_type="hardware",
        status="completed",
        tags=["ibm"],
        metrics={"tvd": 0.05},
        backend=BackendMetadataRecord(backend_name="ibm_demo", job_id="job123", job_status="DONE"),
    )
    db.append(record)

    records = db.read_all()
    assert len(records) == 1
    assert records[0].name == "test_run"
    assert len(db.query(run_type="hardware")) == 1
    assert len(db.query(metric_max={"tvd": 0.1})) == 1

def test_artifact_record():
    out_dir = ROOT / "outputs" / "test_v2_7_artifact"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "artifact.txt"
    path.write_text("demo", encoding="utf-8")
    artifact = artifact_from_path(path)
    assert artifact.metadata["exists"] is True

def test_exports():
    out_dir = ROOT / "outputs" / "test_v2_7_exports"
    db, records, artifacts = create_demo_run_database(out_dir)
    assert len(records) == 2
    assert Path(artifacts["run_table_csv"]).exists()
    assert Path(artifacts["dashboard_json"]).exists()
    assert Path(artifacts["markdown_report"]).exists()
    summary = summarize_records(records)
    assert summary["by_type"]["simulator"] == 1
    assert summary["by_type"]["hardware"] == 1

def test_cli_runs_demo():
    out_dir = ROOT / "outputs" / "test_v2_7_cli_runs"
    code = main(["runs-demo", "--output-dir", str(out_dir)])
    assert code == 0
    assert (out_dir / "azmqos_runs.jsonl").exists()
    assert (out_dir / "dashboard.json").exists()

if __name__ == "__main__":
    test_database_append_read_query()
    test_artifact_record()
    test_exports()
    test_cli_runs_demo()
    print("All v2.7 experiment database tests passed.")
