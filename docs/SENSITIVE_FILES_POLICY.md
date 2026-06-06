# Sensitive Files Policy

The following files should remain local/private and are ignored by Git:

```text
.env
job_ids.json
backend_calibration.json
counts_records.json
runtime_cache/
outputs/
```

Use a shared private folder on your machine instead:

```text
C:\Users\mazab\AZM_QOS_SHARED\
    job_ids.json
    backend_calibration.json
    counts_records.json
```

Then pass full paths to the CLI:

```powershell
azmqos production-runtime-sync --config outputs\production_project\azmqos_production.json --job-ids-file "C:\Users\mazab\AZM_QOS_SHARED\job_ids.json"
```
