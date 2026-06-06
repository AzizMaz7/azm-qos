# AZM-QOS v4.5 Hardware Sync Workflow Guide

The v4.5 workflow does:

1. Create or load hardware dry-run manifests.
2. Import job IDs or derive sync references from dry-run manifests.
3. Import hardware counts or generate deterministic synthetic hardware-style counts.
4. Normalize syndrome-count records.
5. Compare dry-run expected counts to hardware-style counts.
6. Compute total variation distance.
7. Store sync results in database/dashboard artifacts.

Default behavior is local and synthetic. To use real hardware data, export IBM job IDs/counts into JSON or CSV and pass them with `--job-ids-file` and `--counts-file`.
