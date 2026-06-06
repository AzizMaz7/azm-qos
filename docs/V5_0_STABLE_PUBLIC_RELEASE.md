# AZM-QOS v5.0 Stable Public Research Release

v5.0 is the stable public research release.

## Required first production command

```powershell
azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project
```

## New file

```text
azmqos_research/qec_public_release.py
```

## Main commands

```powershell
azmqos public-release-info --output-dir outputs\public_release_info
```

```powershell
azmqos public-release-validate --output-dir outputs\public_release_validate
```

## Main outputs

- `public_release_manifest.json`
- `api_reference.md`
- `docs_site/`
- `paper_reproduction_index.md`
- `scaffold_label_cleanup_report.md`
- `CITATION.cff.json`
- `public_release_validation.md`
