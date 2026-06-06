# AZM-QOS v3.1 END/VQS Production Configuration

v3.1 adds production-run configuration for real END/VQS workflows.

## New file

```text
azmqos_research/production.py
```

## Main commands

```bash
azmqos production-init --output-dir outputs/production_project
azmqos production-plan --config outputs/production_project/azmqos_production.json
azmqos production-run --config outputs/production_project/azmqos_production.json
```

## Main features

- component registry selection
- observable family filtering
- simulator/hardware-safe policies
- queue/resume policy scaffold
- production plan exports
- production database/dashboard
- manuscript scaffold
- final production archive
