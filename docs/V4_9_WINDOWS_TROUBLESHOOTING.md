# AZM-QOS v4.9 Windows Troubleshooting

## Missing production config

```powershell
azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project
```

## Reinstall after downloading a new version

```powershell
python -m pip install -e .
```

## Recommended final command

```powershell
azmqos production-release-run --config outputs\production_project\azmqos_production.json --backend-name ibm_fez --code repetition3 --max-components 2 --shots 64 --rounds 3
```
