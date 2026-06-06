# AZM-QOS v2.9 Hardware Job Synchronization

v2.9 adds job status/result synchronization for existing IBM hardware jobs and database records.

## New file

```text
azmqos_research/job_sync.py
```

## Main features

- refresh job status
- retrieve completed counts
- detect failed/cancelled jobs
- update JSONL experiment database records
- export sync CSV and Markdown reports
- rebuild dashboards after sync

## Main command

```bash
azmqos sync-demo --output-dir outputs/sync_demo
```

## Main examples

```bash
python examples\job_sync_demo.py
python examples\mock_job_status_demo.py
python examples\sync_dashboard_demo.py
```
