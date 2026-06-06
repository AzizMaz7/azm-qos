# AZM-QOS v3.0 Integrated Research Application

v3.0 adds project-level orchestration.

## New files

```text
azmqos_research/project_config.py
azmqos_research/plugin_registry.py
azmqos_research/app.py
```

## Main commands

```bash
azmqos app-init --output-dir outputs/my_project
azmqos app-run --config outputs/my_project/azmqos_project.json
azmqos app-report --config outputs/my_project/azmqos_project.json
```

## Main examples

```bash
python examples\project_config_demo.py
python examples\plugin_registry_demo.py
python examples\integrated_app_demo.py
```

## Workflow

The integrated app can create:

- project config
- plugin registry
- run database
- sync report
- mitigation report
- uncertainty report
- dashboard
- manuscript scaffold
- final reproducibility archive
