from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import make_windows_troubleshooting_guide, make_clean_command_table

print("AZM-QOS v4.9 Windows Troubleshooting Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "windows_troubleshooting_demo"
guide = make_windows_troubleshooting_guide(out_dir / "windows_troubleshooting.md")
table = make_clean_command_table(out_dir / "clean_command_table.md")

print("Guide:", guide)
print("Command table:", table)
