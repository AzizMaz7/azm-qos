# AZM-QOS v4.6 IBM Runtime Fetch Adapters and Hardware Result Caching

v4.6 adds optional IBM Runtime fetch hooks and persistent result caching.

## Required first production command

```powershell
azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project
```

## New file

```text
azmqos_research/qec_runtime_fetch.py
```

## Main commands

Standalone demo:

```powershell
azmqos runtime-fetch-demo --output-dir outputs\runtime_fetch_demo --backend-name ibm_fez
```

Production Runtime-sync workflow:

```powershell
azmqos production-runtime-sync --config outputs\production_project\azmqos_production.json --backend-name ibm_fez --code repetition3 --max-components 2 --shots 64 --rounds 3
```

Enable real Runtime fetching:

```powershell
azmqos production-runtime-sync --config outputs\production_project\azmqos_production.json --job-ids-file job_ids.json --enable-runtime-fetch
```

## Main outputs

- `runtime_fetch_records.csv`
- `runtime_fetch_records.json`
- `job_references.csv`
- `counts_records.csv`
- `sync_comparisons.csv`
- `runtime_sync_report.md`
- `production_runtime_sync_manifest.json`
- `runtime_cache/*.json`
