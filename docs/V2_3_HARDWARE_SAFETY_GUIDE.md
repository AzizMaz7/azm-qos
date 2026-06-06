# AZM-QOS v2.3 Hardware Safety Guide

AZM-QOS v2.3 defaults to dry-run mode.

Real hardware jobs are submitted only when:

```python
IBMRuntimeConfig(dry_run=False)
```

or:

```bash
azmqos ibm-dry-run --submit
```

Before submitting:

1. Confirm your IBM Quantum account.
2. Confirm backend access.
3. Confirm shot count.
4. Confirm circuit size and depth.
5. Start with a small smoke test.
6. Save the generated IBM Runtime report.
