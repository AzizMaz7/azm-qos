# AZM-QOS v4.9 Release Polish

v4.9 adds final user-facing release quality features.

## Required first production command

```powershell
azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project
```

## New file

```text
azmqos_research/qec_release.py
```

## Main commands

Demo:

```powershell
azmqos release-demo --output-dir outputs\release_demo
```

All-in-one production release:

```powershell
azmqos production-release-run --config outputs\production_project\azmqos_production.json --backend-name ibm_fez --code repetition3 --max-components 2 --shots 64 --rounds 3
```

Minimal clean package:

```powershell
azmqos release-minimal-package --output-dir outputs\minimal_package
```

## Main outputs

- `release_validation_report.md`
- `clean_command_table.md`
- `windows_troubleshooting.md`
- `release_report.html`
- `release_manifest.json`
- minimal clean package ZIP
