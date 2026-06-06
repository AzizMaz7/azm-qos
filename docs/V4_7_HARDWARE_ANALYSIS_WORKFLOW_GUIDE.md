# AZM-QOS v4.7 Hardware Analysis Workflow Guide

The v4.7 workflow does:

1. Run or load Runtime-sync results.
2. Separate real Runtime records from synthetic fallback records.
3. Load or create backend calibration metadata.
4. Compute hardware-count confidence intervals.
5. Compute logical failure-rate confidence bands.
6. Export analysis reports and figures.
7. Build a final QEC experiment archive.

Synthetic-only analyses are workflow validation, not hardware evidence.
