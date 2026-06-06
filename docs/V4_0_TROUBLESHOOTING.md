# AZM-QOS v4.0 Troubleshooting

## Error: `azmqos_production.json` not found

Run this first from inside the package folder:

```powershell
azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project
```

Then run:

```powershell
azmqos production-plan --config outputs\production_project\azmqos_production.json
```

Then run:

```powershell
azmqos stable-run --config outputs\production_project\azmqos_production.json --backend fallback
```

## After installing a new version

Run:

```powershell
python -m pip install -e .
```

from inside the new version folder.
