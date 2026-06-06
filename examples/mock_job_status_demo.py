from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    mock_job_payload,
    sync_job_from_payload,
    run_mock_failure_sync_workflow,
)

print("AZM-QOS v2.9 Mock Job Status Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "mock_job_status_demo"

payload = mock_job_payload(job_id="demo_pending_job", status="RUNNING", backend_name="mock_backend", counts={})
result = sync_job_from_payload(payload, output_dir=out_dir / "single")
print(result.summary())
print()

failure_summary = run_mock_failure_sync_workflow(out_dir / "failure")
print(failure_summary.summary())
for item in failure_summary.results:
    print(item.summary())
