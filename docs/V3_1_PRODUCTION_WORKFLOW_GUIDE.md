# AZM-QOS v3.1 Production Workflow Guide

Initialize:

```bash
azmqos production-init --output-dir outputs/my_endvqs_project
```

Edit:

```text
outputs/my_endvqs_project/azmqos_production.json
```

Set:

```json
"component_registry_path": "templates/endvqs_real_terms_template.json"
```

Then plan:

```bash
azmqos production-plan --config outputs/my_endvqs_project/azmqos_production.json
```

Dry-run-safe production workflow:

```bash
azmqos production-run --config outputs/my_endvqs_project/azmqos_production.json
```

The v3.1 production workflow does not submit hardware jobs by default.
