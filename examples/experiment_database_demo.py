from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import create_demo_run_database

print("AZM-QOS v2.7 Experiment Database Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "experiment_database_demo"
db, records, artifacts = create_demo_run_database(out_dir)

print(db.summary())
print()
for record in records:
    print(record.summary())
    print()

print("Artifacts:")
for key, value in artifacts.items():
    print(f"  {key}: {value}")
