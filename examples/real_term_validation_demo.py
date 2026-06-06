from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import load_registry_for_research, export_term_audit_csv, make_real_term_validation_report

print("AZM-QOS v2.1 Real-Term Validation Demo")
print("=" * 70)

template = ROOT / "templates" / "endvqs_real_terms_template.json"
load_result = load_registry_for_research(component_registry_json=template)

out_dir = ROOT / "outputs" / "real_term_validation_demo"
out_dir.mkdir(parents=True, exist_ok=True)

audit_path = export_term_audit_csv(load_result.registry, out_dir / "term_audit.csv")
report_path = make_real_term_validation_report(load_result, out_dir / "real_term_validation_report.md")

print(load_result.summary())
print(load_result.validation.summary())
print()
print("Saved audit:", audit_path)
print("Saved report:", report_path)
