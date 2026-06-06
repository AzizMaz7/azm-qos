# AZM-QOS v2.7 Experiment Database

v2.7 adds persistent JSONL run tracking.

## New file

```text
azmqos_research/experiment_db.py
```

## Main objects

```text
ArtifactRecord
BackendMetadataRecord
ExperimentRunRecord
ExperimentDatabase
```

## Main command

```bash
azmqos runs-demo --output-dir outputs/run_database_demo
```

## Main examples

```bash
python examples\experiment_database_demo.py
python examples\run_tracking_demo.py
python examples\dashboard_export_demo.py
```

## What it tracks

- run ID
- run name
- run type
- status
- tags
- parameters
- metrics
- backend metadata
- IBM job IDs
- artifacts
- notes
