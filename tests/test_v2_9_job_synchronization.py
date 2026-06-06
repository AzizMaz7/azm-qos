from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    normalize_job_status,
    is_success_status,
    is_failure_status,
    mock_job_payload,
    sync_job_from_payload,
    run_mock_sync_workflow,
    run_mock_failure_sync_workflow,
)
from azmqos_research.cli import main

def test_status_helpers():
    assert normalize_job_status("JobStatus.DONE") == "DONE"
    assert is_success_status("DONE")
    assert is_failure_status("CANCELLED")

def test_sync_job_from_payload_done():
    out_dir = ROOT / "outputs" / "test_v2_9_payload_done"
    payload = mock_job_payload("job_done", status="DONE", counts={"00": 5, "11": 7})
    result = sync_job_from_payload(payload, out_dir, simulator_counts={"00": 6, "11": 6})
    assert result.action == "retrieved_counts"
    assert result.counts["11"] == 7
    assert Path(result.artifacts["hardware_counts_json"]).exists()

def test_sync_job_from_payload_pending():
    out_dir = ROOT / "outputs" / "test_v2_9_payload_pending"
    payload = mock_job_payload("job_pending", status="RUNNING", counts={})
    result = sync_job_from_payload(payload, out_dir)
    assert result.action == "still_pending"

def test_mock_sync_workflow():
    out_dir = ROOT / "outputs" / "test_v2_9_mock_sync"
    summary = run_mock_sync_workflow(out_dir)
    assert len(summary.results) == 1
    assert summary.results[0].action == "retrieved_counts"
    assert "manifest" in summary.dashboard_artifacts

def test_mock_failure_sync_workflow():
    out_dir = ROOT / "outputs" / "test_v2_9_failure_sync"
    summary = run_mock_failure_sync_workflow(out_dir)
    assert len(summary.results) == 1
    assert summary.results[0].action == "terminal_failure_detected"

def test_cli_sync_demo():
    out_dir = ROOT / "outputs" / "test_v2_9_cli_sync"
    code = main(["sync-demo", "--output-dir", str(out_dir)])
    assert code == 0
    assert (out_dir / "sync_manifest.json").exists()

if __name__ == "__main__":
    test_status_helpers()
    test_sync_job_from_payload_done()
    test_sync_job_from_payload_pending()
    test_mock_sync_workflow()
    test_mock_failure_sync_workflow()
    test_cli_sync_demo()
    print("All v2.9 job synchronization tests passed.")
