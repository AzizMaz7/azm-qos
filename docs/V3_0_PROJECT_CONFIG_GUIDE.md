# AZM-QOS v3.0 Project Config Guide

Initialize a project:

```bash
azmqos app-init --output-dir outputs/my_project --project-name my_project
```

Edit:

```text
outputs/my_project/azmqos_project.json
```

Then run:

```bash
azmqos app-run --config outputs/my_project/azmqos_project.json
```

The default configuration is safe and uses mock/local workflows only.
