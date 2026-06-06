# AZM-QOS v3.2 Execution Adapter Guide

The v3.2 adapter has two safe execution modes:

## Simulator

Generates deterministic placeholder estimates and counts for every production plan item.

## Hardware dry-run

Generates pseudo job IDs and job manifests, but does not submit IBM jobs.

The real hardware submission path remains intentionally separate.
