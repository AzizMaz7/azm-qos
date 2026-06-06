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
)

print("AZM-QOS v2.7 Run Tracking Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "run_tracking_demo"
out_dir.mkdir(parents=True, exist_ok=True)

db = ExperimentDatabase(out_dir / "runs.jsonl")

artifact_path = out_dir / "example_result.json"
artifact_path.write_text('{"result": "demo"}', encoding="utf-8")

record = new_run_record(
    name="manual_tracked_run",
    run_type="hardware",
    status="completed",
    tags=["manual", "demo"],
    parameters={"shots": 1024},
    metrics={"tvd": 0.05},
    backend=BackendMetadataRecord(
        backend_name="ibm_demo",
        job_id="demo_job",
        job_status="DONE",
        num_qubits=127,
    ),
    artifacts=[artifact_from_path(artifact_path)],
)

run_id = db.append(record)

print("Saved run ID:", run_id)
print(db.summary())
print()
print("Hardware query:")
for item in db.query(run_type="hardware"):
    print(item.summary())
