# AZM-QOS v5.0

**AZM-QOS v5.0** is the **stable public research release** of the AZM-QOS END/VQS + QEC platform.

It keeps the v4.9 one-command workflow and adds public-release quality artifacts: semantic versioning metadata, a public API reference scaffold, a documentation-site scaffold, paper-reproduction examples, a scaffold-label cleanup report, and public-release validation.

````markdown
# AZM-QOS

**AZM-QOS** is a research software platform for generalized quantum observable simulation workflows, END/VQS-style estimator construction, QEC-aware logical estimators, hardware-result synchronization, hardware-analysis reports, and reproducible manuscript/thesis export.

[![DOI](https://zenodo.org/badge/1261397835.svg)](https://doi.org/10.5281/zenodo.20572832)

## Citation

If you use AZM-QOS in academic work, please cite the archived software release:

```bibtex
@software{maaz_azmqos_2026,
  author  = {Momin, Abdul Aziz},
  title   = {{AZM-QOS: A Quantum Observable Simulation and QEC-Aware Research Workflow Platform}},
  version = {5.0.0},
  year    = {2026},
  doi     = {10.5281/zenodo.20572833},
  url     = {https://github.com/YOUR_USERNAME/azm-qos}
}
````

## Install

```bash
python -m pip install -e .
```

## Required first command

Always initialize the production project first:

```bash
azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project
```

This creates:

```text
outputs\production_project\azmqos_production.json
```

## Recommended public-release workflow

| Step | Command |
|---|---|
| Install | `python -m pip install -e .` |
| Initialize | `azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project` |
| Plan | `azmqos production-plan --config outputs\production_project\azmqos_production.json` |
| Public release info | `azmqos public-release-info --output-dir outputs\public_release_info` |
| Public release validation | `azmqos public-release-validate --output-dir outputs\public_release_validate` |
| Full production release | `azmqos production-release-run --config outputs\production_project\azmqos_production.json --backend-name ibm_fez --code repetition3 --max-components 2 --shots 64 --rounds 3` |

## New in v5.0

- Semantic versioning metadata
- Stable public-release manifest
- Public API reference scaffold
- Documentation-site scaffold
- Paper-reproduction example index
- Scaffold-label cleanup report
- Public-release validation checklist
- Public citation metadata scaffold
- Lightweight public-release CLI commands

## New research file

```text
azmqos_research/
   └── qec_public_release.py
```

## Main v5.0 CLI commands

```bash
azmqos public-release-info --output-dir outputs\public_release_info
```

```bash
azmqos public-release-validate --output-dir outputs\public_release_validate
```

## Run examples

```bash
python examples\public_release_info_demo.py
python examples\paper_reproduction_index_demo.py
python examples\api_reference_demo.py
```

## Run tests

```bash
python tests\test_v5_0_public_release.py
```

## Scientific note

Synthetic fallback workflows validate software behavior and reproducibility, but real hardware claims require real Runtime records, calibration metadata, and hardware-count imports.
