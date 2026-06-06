# AZM-QOS v4.4 Hardware-Ready QEC Transpilation

v4.4 adds hardware-ready dry-run transpilation scaffolds for QEC syndrome circuits.

## Required first production command

```powershell
azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project
```

## New file

```text
azmqos_research/qec_hardware.py
```

## Main commands

Standalone demo:

```powershell
azmqos qec-hardware-demo --output-dir outputs\qec_hardware_demo --backend-name ibm_fez
```

Production hardware dry-run workflow:

```powershell
azmqos production-qec-hardware-dry-run --config outputs\production_project\azmqos_production.json --backend-name ibm_fez --code repetition3 --max-components 2 --shots 64 --rounds 3
```

## Main outputs

- `syndrome_circuit_specs.json`
- `resource_summaries.csv`
- `resource_summaries.json`
- `isa_checks.csv`
- `isa_checks.json`
- `job_manifests.csv`
- `job_manifests.json`
- `layout_recommendation.json`
- `qec_hardware_report.md`
- `production_qec_hardware_dry_run_manifest.json`
