from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research.cli import main

print("AZM-QOS v2.0 CLI Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "cli_demo"
exit_code = main([
    "run",
    "--output-dir", str(out_dir),
    "--shots", "64",
    "--repeats", "1",
    "--rounds", "3",
    "--trials", "5",
    "--measurement-error", "0.05",
    "--seed", "123",
])

print("CLI exit code:", exit_code)
