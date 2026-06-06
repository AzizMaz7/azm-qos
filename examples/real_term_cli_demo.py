from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research.cli import main

print("AZM-QOS v2.1 Real-Term CLI Demo")
print("=" * 70)

template = ROOT / "templates" / "endvqs_real_terms_template.json"
out_dir = ROOT / "outputs" / "real_term_cli_demo"

exit_code = main([
    "real-terms",
    "--component-registry", str(template),
    "--output-dir", str(out_dir),
    "--shots", "128",
    "--repeats", "2",
    "--rounds", "3",
    "--trials", "5",
    "--measurement-error", "0.05",
    "--seed", "123",
])

print("CLI exit code:", exit_code)
