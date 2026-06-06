# AZM-QOS v3.2 Production Execution Adapters

v3.2 turns END/VQS production plan items into executable workload specs.

## New file

```text
azmqos_research/production_execution.py
```

## Main command

```bash
azmqos production-execute --config outputs/production_project/azmqos_production.json
```

Force simulator mode:

```bash
azmqos production-execute --config outputs/production_project/azmqos_production.json --mode simulator
```

Force hardware dry-run mode:

```bash
azmqos production-execute --config outputs/production_project/azmqos_production.json --mode hardware_dry_run
```

## Main outputs

- `workloads.csv`
- `job_manifest.json`
- `execution_results.json`
- `execution_results.csv`
- production execution database
- dashboard
- execution report
