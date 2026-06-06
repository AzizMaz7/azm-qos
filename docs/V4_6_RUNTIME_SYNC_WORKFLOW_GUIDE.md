# AZM-QOS v4.6 Runtime Sync Workflow Guide

The v4.6 workflow does:

1. Build or import job references.
2. Check whether Runtime fetching is enabled.
3. Load cached result if available.
4. Fetch status/counts through Runtime hooks when enabled.
5. Fall back to clearly labeled synthetic counts when Runtime is disabled or unavailable.
6. Cache the resulting record.
7. Compare dry-run expectations to synced results.
8. Export database/dashboard artifacts.

No hardware jobs are submitted.
