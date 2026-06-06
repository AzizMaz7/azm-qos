# AZM-QOS v4.5 Hardware Result Ingestion and Synchronization

v4.5 adds hardware-style result synchronization for QEC dry-run workflows.

## Required first production command

```powershell
azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project
```

## New file

```text
azmqos_research/qec_hardware_sync.py
```

## Main commands

Standalone demo:

```powershell
azmqos qec-hardware-sync-demo --output-dir outputs\qec_hardware_sync_demo --backend-name ibm_fez
```

Production sync workflow:

```powershell
azmqos production-qec-hardware-sync --config outputs\production_project\azmqos_production.json --backend-name ibm_fez --code repetition3 --max-components 2 --shots 64 --rounds 3
```

With imported job IDs:

```powershell
azmqos production-qec-hardware-sync --config outputs\production_project\azmqos_production.json --job-ids-file job_ids.json
```

## Main outputs

- `job_references.csv`
- `job_references.json`
- `counts_records.csv`
- `counts_records.json`
- `sync_comparisons.csv`
- `sync_comparisons.json`
- `sync_comparisons.png`
- `hardware_sync_report.md`
- `production_qec_hardware_sync_manifest.json`
