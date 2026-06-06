from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import make_generic_two_qubit_workload, RuntimeManager, RuntimeConfig, export_result_json, export_result_csv, make_text_report

workload = make_generic_two_qubit_workload()
manager = RuntimeManager()
print("Available backends:")
for name, info in manager.list_backends().items():
    print(f"  {name}: {info.description}")

result = manager.run(workload, "shot_simulator", RuntimeConfig(shots=4096, repeats=50, seed=123))
print()
print(result.summary())

out_dir = ROOT / "outputs"
out_dir.mkdir(exist_ok=True)
export_result_json(result, out_dir / "backend_runtime_result.json")
export_result_csv(result, out_dir / "backend_runtime_result.csv")
make_text_report(workload, result, out_dir / "backend_runtime_report.txt")
print(f"Saved outputs to: {out_dir}")
