# AZM-QOS v4.8 Final Manuscript/Thesis Export

v4.8 adds final paper/thesis export and reproducibility packaging.

## Required first production command

```powershell
azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project
```

## New file

```text
azmqos_research/qec_final_export.py
```

## Main commands

Standalone demo:

```powershell
azmqos final-export-demo --output-dir outputs\final_export_demo
```

Production final export:

```powershell
azmqos production-final-export --config outputs\production_project\azmqos_production.json --backend-name ibm_fez --code repetition3 --max-components 2 --shots 64 --rounds 3
```

## Main outputs

- `manuscript/azmqos_manuscript_scaffold.tex`
- `thesis/azmqos_thesis_appendix.md`
- `figures/figures_manifest.json`
- `reproducibility_checklist.md`
- `version_lockfile.json`
- `final_command_summary.md`
- `final_export_report.md`
- `final_export_manifest.json`
- final export archive ZIP
