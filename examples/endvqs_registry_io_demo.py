from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_endvqs import (
    default_endvqs_registry,
    save_term_registry_json,
    load_term_registry_json,
    save_term_registry_csv,
    load_term_registry_csv,
    validate_term_registry,
    m_symmetry_diagnostics,
)

print("AZM-QOS v1.1 END/VQS Registry I/O Demo")
print("=" * 70)

registry = default_endvqs_registry()
out_dir = ROOT / "outputs"
out_dir.mkdir(exist_ok=True)

json_path = out_dir / "endvqs_registry.json"
csv_path = out_dir / "endvqs_registry.csv"

save_term_registry_json(registry, json_path)
save_term_registry_csv(registry, csv_path)

loaded_json = load_term_registry_json(json_path)
loaded_csv = load_term_registry_csv(csv_path)

print("Saved JSON:", json_path)
print("Saved CSV: ", csv_path)
print()
print(validate_term_registry(loaded_json).summary())
print()
print(validate_term_registry(loaded_csv).summary())
print()
print("M symmetry diagnostics:")
print(m_symmetry_diagnostics(loaded_json))
