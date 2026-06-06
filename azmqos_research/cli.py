from __future__ import annotations
import argparse
from pathlib import Path
from .runner import run_research_platform_pipeline
from .qec_public_release import run_public_release_info, run_public_release_validate
from .qec_release import run_release_demo, run_production_release, run_minimal_package_demo
from .qec_final_export import run_final_export_demo, run_production_final_export
from .qec_hardware_analysis import run_hardware_analysis_demo, run_production_hardware_analysis
from .qec_runtime_fetch import run_runtime_fetch_demo, run_production_runtime_sync
from .qec_hardware_sync import run_qec_hardware_sync_demo, run_production_qec_hardware_sync
from .qec_hardware import run_qec_hardware_demo, run_production_qec_hardware_dry_run
from .qec_fault_tolerant import run_ft_qec_demo, run_production_ft_qec
from .qec_decoder import run_qec_decoder_demo, run_production_qec_decoder
from .qec_logical import run_qec_demo, run_production_qec_estimator
from .stable_platform import run_stable_workflow, run_stable_smoke_test
from .derivative_mitigation import run_derivative_mitigation_demo, run_production_mitigated_derivatives
from .derivative_estimators import run_derivative_demo, run_production_derivative_estimators
from .endvqs_stateprep import make_stateprep_demo, run_production_endvqs_execution
from .qiskit_pauli_execution import run_production_qiskit_execution
from .production_pauli_execution import run_production_pauli_execution
from .pauli_compiler import make_pauli_compile_demo, compile_registry_components
from .production_simulator import run_production_simulator_batch, run_production_shot_scaling
from .production_execution import run_production_execution_adapter
from .production import init_production_project, load_production_spec, make_production_plan, export_production_plan_json, export_production_plan_csv, make_production_plan_report, run_production_dry_run, validate_production_spec
from .project_config import init_project, load_project_config, validate_project_config
from .app import run_integrated_workflow, make_project_summary_report
from .job_sync import run_mock_sync_workflow
from .dashboard import build_dashboard_package
from .experiment_db import create_demo_run_database
from .uncertainty import run_mock_uncertainty_workflow
from .real_terms import run_real_term_research_pipeline
from .ibm_runtime import IBMRuntimeConfig, diagnose_ibm_runtime, run_sampler_v2_job, make_ibm_runtime_report
from .hardware_compare import run_mock_hardware_comparison
from .calibration_mitigation import run_mock_mitigation_workflow

def build_parser():
    parser = argparse.ArgumentParser(description="AZM-QOS v2.1 research platform CLI")
    sub = parser.add_subparsers(dest="command")

    run = sub.add_parser("run", help="Run the integrated research platform pipeline.")
    run.add_argument("--output-dir", default="azmqos_research_output")
    run.add_argument("--shots", type=int, default=64)
    run.add_argument("--repeats", type=int, default=1)
    run.add_argument("--rounds", type=int, default=3)
    run.add_argument("--trials", type=int, default=5)
    run.add_argument("--measurement-error", type=float, default=0.05)
    run.add_argument("--seed", type=int, default=123)

    real = sub.add_parser("real-terms", help="Run with a custom END/VQS term registry.")
    real.add_argument("--output-dir", default="azmqos_real_terms_output")
    real.add_argument("--term-registry", default=None, help="Path to END/VQS term-registry JSON.")
    real.add_argument("--component-registry", default=None, help="Path to END/VQS component-registry JSON.")
    real.add_argument("--shots", type=int, default=256)
    real.add_argument("--repeats", type=int, default=5)
    real.add_argument("--rounds", type=int, default=5)
    real.add_argument("--trials", type=int, default=20)
    real.add_argument("--measurement-error", type=float, default=0.05)
    real.add_argument("--seed", type=int, default=123)
    real.add_argument("--no-default", action="store_true", help="Fail if no registry path is provided.")

    ibm_diag = sub.add_parser("ibm-diagnose", help="Diagnose IBM Runtime environment without submitting jobs.")
    ibm_diag.add_argument("--output-dir", default="azmqos_ibm_diagnostics")
    ibm_diag.add_argument("--channel", default=None)
    ibm_diag.add_argument("--instance", default=None)

    ibm_dry = sub.add_parser("ibm-dry-run", help="Prepare an IBM Runtime Sampler dry run. Use --submit to submit.")
    ibm_dry.add_argument("--output-dir", default="azmqos_ibm_dry_run")
    ibm_dry.add_argument("--backend", default=None)
    ibm_dry.add_argument("--shots", type=int, default=1024)
    ibm_dry.add_argument("--channel", default=None)
    ibm_dry.add_argument("--instance", default=None)
    ibm_dry.add_argument("--submit", action="store_true", help="Actually submit a Runtime job. Default is dry-run.")

    hw = sub.add_parser("hardware-compare", help="Create a hardware-vs-simulator comparison report from mock/saved results.")
    hw.add_argument("--output-dir", default="azmqos_hardware_compare_output")

    mit = sub.add_parser("mitigate", help="Create a calibration-aware mitigation report from mock/saved results.")
    mit.add_argument("--output-dir", default="azmqos_mitigation_output")

    unc = sub.add_parser("uncertainty", help="Create a finite-shot uncertainty report from mock/saved results.")
    unc.add_argument("--output-dir", default="azmqos_uncertainty_output")
    unc.add_argument("--bootstrap", type=int, default=500)
    unc.add_argument("--confidence", type=float, default=0.95)

    runs = sub.add_parser("runs-demo", help="Create a demo AZM-QOS run database.")
    runs.add_argument("--output-dir", default="azmqos_run_database_output")

    dash = sub.add_parser("dashboard-demo", help="Create a demo multi-run dashboard package.")
    dash.add_argument("--output-dir", default="azmqos_dashboard_output")

    sync = sub.add_parser("sync-demo", help="Run a mock hardware job synchronization workflow.")
    sync.add_argument("--output-dir", default="azmqos_sync_output")

    app_init = sub.add_parser("app-init", help="Initialize an AZM-QOS v3.0 project folder.")
    app_init.add_argument("--output-dir", default="azmqos_project")
    app_init.add_argument("--project-name", default="azmqos_research_project")

    app_run = sub.add_parser("app-run", help="Run the integrated AZM-QOS v3.0 workflow.")
    app_run.add_argument("--config", required=True)

    app_report = sub.add_parser("app-report", help="Print project configuration summary.")
    app_report.add_argument("--config", required=True)

    prod_init = sub.add_parser("production-init", help="Initialize an END/VQS production project.")
    prod_init.add_argument("--output-dir", default="azmqos_production_project")
    prod_init.add_argument("--project-name", default="endvqs_production_project")

    prod_plan = sub.add_parser("production-plan", help="Create an END/VQS production plan.")
    prod_plan.add_argument("--config", required=True)

    prod_run = sub.add_parser("production-run", help="Run the dry-run-safe END/VQS production workflow.")
    prod_run.add_argument("--config", required=True)

    prod_exec = sub.add_parser("production-execute", help="Run the v3.2 production execution adapter.")
    prod_exec.add_argument("--config", required=True)
    prod_exec.add_argument("--mode", default=None, choices=["simulator", "hardware_dry_run", "hardware_submit_disabled"])

    prod_sim = sub.add_parser("production-simulate", help="Run the v3.3 production simulator backend.")
    prod_sim.add_argument("--config", required=True)
    prod_sim.add_argument("--backend", default="auto", choices=["auto", "aer", "fallback"])
    prod_sim.add_argument("--shots", type=int, default=None)

    prod_scale = sub.add_parser("production-shot-scaling", help="Run v3.3 production simulator shot scaling.")
    prod_scale.add_argument("--config", required=True)
    prod_scale.add_argument("--backend", default="fallback", choices=["auto", "aer", "fallback"])

    pauli = sub.add_parser("pauli-compile", help="Run Pauli-term circuit compiler demo or compile a registry.")
    pauli.add_argument("--output-dir", default="azmqos_pauli_compile_output")
    pauli.add_argument("--registry", default=None)
    pauli.add_argument("--max-components", type=int, default=None)

    prod_pauli = sub.add_parser("production-pauli-execute", help="Run grouped Pauli execution for selected END/VQS production components.")
    prod_pauli.add_argument("--config", required=True)
    prod_pauli.add_argument("--max-components", type=int, default=None)
    prod_pauli.add_argument("--shots", type=int, default=None)

    prod_qiskit = sub.add_parser("production-qiskit-execute", help="Run Qiskit/fallback execution for compiled Pauli production components.")
    prod_qiskit.add_argument("--config", required=True)
    prod_qiskit.add_argument("--backend", default="auto", choices=["auto", "aer", "basic", "fallback", "hardware_dry_run"])
    prod_qiskit.add_argument("--max-components", type=int, default=None)
    prod_qiskit.add_argument("--shots", type=int, default=None)
    prod_qiskit.add_argument("--hardware-backend-name", default=None)

    stateprep = sub.add_parser("endvqs-stateprep-demo", help="Create an END/VQS state-preparation demo.")
    stateprep.add_argument("--output-dir", default="azmqos_endvqs_stateprep_output")

    endvqs_exec = sub.add_parser("production-endvqs-execute", help="Run production END/VQS state-prep execution hooks.")
    endvqs_exec.add_argument("--config", required=True)
    endvqs_exec.add_argument("--stateprep-config", default=None)
    endvqs_exec.add_argument("--backend", default="fallback", choices=["auto", "aer", "basic", "fallback", "hardware_dry_run"])
    endvqs_exec.add_argument("--max-components", type=int, default=None)
    endvqs_exec.add_argument("--shots", type=int, default=None)

    deriv_demo = sub.add_parser("derivative-demo", help="Run a v3.8 parameter-shift derivative demo.")
    deriv_demo.add_argument("--output-dir", default="azmqos_derivative_demo_output")

    prod_deriv = sub.add_parser("production-derivatives", help="Run production derivative estimators.")
    prod_deriv.add_argument("--config", required=True)
    prod_deriv.add_argument("--stateprep-config", default=None)
    prod_deriv.add_argument("--backend", default="fallback", choices=["auto", "aer", "basic", "fallback", "hardware_dry_run"])
    prod_deriv.add_argument("--max-components", type=int, default=None)
    prod_deriv.add_argument("--shots", type=int, default=None)

    mitig_demo = sub.add_parser("derivative-mitigation-demo", help="Run a v3.9 derivative error-mitigation demo.")
    mitig_demo.add_argument("--output-dir", default="azmqos_derivative_mitigation_output")

    prod_mitig = sub.add_parser("production-mitigated-derivatives", help="Run production mitigated derivative estimators.")
    prod_mitig.add_argument("--config", required=True)
    prod_mitig.add_argument("--stateprep-config", default=None)
    prod_mitig.add_argument("--backend", default="fallback", choices=["auto", "aer", "basic", "fallback", "hardware_dry_run"])
    prod_mitig.add_argument("--max-components", type=int, default=None)
    prod_mitig.add_argument("--shots", type=int, default=None)
    prod_mitig.add_argument("--total-allocation-shots", type=int, default=None)

    stable = sub.add_parser("stable-run", help="Run the v4.0 stable integrated END/VQS workflow.")
    stable.add_argument("--config", required=True)
    stable.add_argument("--backend", default="fallback", choices=["auto", "aer", "basic", "fallback", "hardware_dry_run"])
    stable.add_argument("--max-components", type=int, default=2)
    stable.add_argument("--shots", type=int, default=64)

    smoke = sub.add_parser("stable-smoke-test", help="Run a v4.0 stable workflow smoke test.")
    smoke.add_argument("--output-dir", default="azmqos_stable_smoke_test")

    qec_demo = sub.add_parser("qec-demo", help="Run a v4.1 QEC/logical-qubit demo.")
    qec_demo.add_argument("--output-dir", default="azmqos_qec_demo_output")

    prod_qec = sub.add_parser("production-qec-estimate", help="Run QEC-aware logical observable estimates for selected production components.")
    prod_qec.add_argument("--config", required=True)
    prod_qec.add_argument("--code", default="repetition3", choices=["repetition3", "repetition5", "five_qubit_perfect_scaffold"])
    prod_qec.add_argument("--max-components", type=int, default=None)
    prod_qec.add_argument("--shots", type=int, default=1024)
    prod_qec.add_argument("--physical-error-rate", type=float, default=0.01)

    qec_decoder_demo = sub.add_parser("qec-decoder-demo", help="Run a v4.2 QEC decoder demo.")
    qec_decoder_demo.add_argument("--output-dir", default="azmqos_qec_decoder_demo_output")

    prod_qec_decoder = sub.add_parser("production-qec-decode", help="Run QEC decoder and syndrome post-processing for production components.")
    prod_qec_decoder.add_argument("--config", required=True)
    prod_qec_decoder.add_argument("--code", default="repetition3", choices=["repetition3", "repetition5", "five_qubit_perfect_scaffold"])
    prod_qec_decoder.add_argument("--max-components", type=int, default=None)
    prod_qec_decoder.add_argument("--shots", type=int, default=1024)
    prod_qec_decoder.add_argument("--physical-error-rate", type=float, default=0.01)

    ft_qec_demo = sub.add_parser("ft-qec-demo", help="Run a v4.3 fault-tolerant QEC demo.")
    ft_qec_demo.add_argument("--output-dir", default="azmqos_ft_qec_demo_output")

    prod_ft_qec = sub.add_parser("production-ft-qec", help="Run FT-QEC repeated syndrome workflow for production components.")
    prod_ft_qec.add_argument("--config", required=True)
    prod_ft_qec.add_argument("--code", default="repetition3", choices=["repetition3", "repetition5", "five_qubit_perfect_scaffold"])
    prod_ft_qec.add_argument("--max-components", type=int, default=None)
    prod_ft_qec.add_argument("--shots", type=int, default=1024)
    prod_ft_qec.add_argument("--rounds", type=int, default=3)
    prod_ft_qec.add_argument("--physical-error-rate", type=float, default=0.01)
    prod_ft_qec.add_argument("--measurement-error-rate", type=float, default=0.02)

    qec_hw_demo = sub.add_parser("qec-hardware-demo", help="Run a v4.4 QEC hardware dry-run demo.")
    qec_hw_demo.add_argument("--output-dir", default="azmqos_qec_hardware_demo_output")
    qec_hw_demo.add_argument("--backend-name", default="ibm_fez")
    qec_hw_demo.add_argument("--code", default="repetition3", choices=["repetition3", "repetition5", "five_qubit_perfect_scaffold"])
    qec_hw_demo.add_argument("--rounds", type=int, default=3)
    qec_hw_demo.add_argument("--shots", type=int, default=64)

    prod_qec_hw = sub.add_parser("production-qec-hardware-dry-run", help="Run hardware dry-run transpilation for QEC syndrome circuits.")
    prod_qec_hw.add_argument("--config", required=True)
    prod_qec_hw.add_argument("--backend-name", default="ibm_fez")
    prod_qec_hw.add_argument("--code", default="repetition3", choices=["repetition3", "repetition5", "five_qubit_perfect_scaffold"])
    prod_qec_hw.add_argument("--max-components", type=int, default=None)
    prod_qec_hw.add_argument("--shots", type=int, default=1024)
    prod_qec_hw.add_argument("--rounds", type=int, default=3)
    prod_qec_hw.add_argument("--physical-error-rate", type=float, default=0.01)
    prod_qec_hw.add_argument("--measurement-error-rate", type=float, default=0.02)

    qec_sync_demo = sub.add_parser("qec-hardware-sync-demo", help="Run a v4.5 QEC hardware result sync demo.")
    qec_sync_demo.add_argument("--output-dir", default="azmqos_qec_hardware_sync_demo_output")
    qec_sync_demo.add_argument("--backend-name", default="ibm_fez")
    qec_sync_demo.add_argument("--rounds", type=int, default=2)
    qec_sync_demo.add_argument("--shots", type=int, default=64)

    prod_qec_sync = sub.add_parser("production-qec-hardware-sync", help="Sync hardware-style QEC results with dry-run manifests.")
    prod_qec_sync.add_argument("--config", required=True)
    prod_qec_sync.add_argument("--backend-name", default="ibm_fez")
    prod_qec_sync.add_argument("--code", default="repetition3", choices=["repetition3", "repetition5", "five_qubit_perfect_scaffold"])
    prod_qec_sync.add_argument("--max-components", type=int, default=None)
    prod_qec_sync.add_argument("--shots", type=int, default=1024)
    prod_qec_sync.add_argument("--rounds", type=int, default=3)
    prod_qec_sync.add_argument("--job-ids-file", default=None)
    prod_qec_sync.add_argument("--counts-file", default=None)
    prod_qec_sync.add_argument("--physical-error-rate", type=float, default=0.01)
    prod_qec_sync.add_argument("--measurement-error-rate", type=float, default=0.02)

    runtime_demo = sub.add_parser("runtime-fetch-demo", help="Run a v4.6 Runtime fetch/cache demo.")
    runtime_demo.add_argument("--output-dir", default="azmqos_runtime_fetch_demo_output")
    runtime_demo.add_argument("--backend-name", default="ibm_fez")
    runtime_demo.add_argument("--rounds", type=int, default=2)
    runtime_demo.add_argument("--shots", type=int, default=64)

    prod_runtime = sub.add_parser("production-runtime-sync", help="Run Runtime fetch/cache synchronization for QEC hardware results.")
    prod_runtime.add_argument("--config", required=True)
    prod_runtime.add_argument("--backend-name", default="ibm_fez")
    prod_runtime.add_argument("--code", default="repetition3", choices=["repetition3", "repetition5", "five_qubit_perfect_scaffold"])
    prod_runtime.add_argument("--max-components", type=int, default=None)
    prod_runtime.add_argument("--shots", type=int, default=1024)
    prod_runtime.add_argument("--rounds", type=int, default=3)
    prod_runtime.add_argument("--job-ids-file", default=None)
    prod_runtime.add_argument("--enable-runtime-fetch", action="store_true")
    prod_runtime.add_argument("--force-refresh", action="store_true")
    prod_runtime.add_argument("--physical-error-rate", type=float, default=0.01)
    prod_runtime.add_argument("--measurement-error-rate", type=float, default=0.02)

    hw_analysis_demo = sub.add_parser("hardware-analysis-demo", help="Run a v4.7 hardware-analysis demo.")
    hw_analysis_demo.add_argument("--output-dir", default="azmqos_hardware_analysis_demo_output")
    hw_analysis_demo.add_argument("--backend-name", default="ibm_fez")
    hw_analysis_demo.add_argument("--rounds", type=int, default=2)
    hw_analysis_demo.add_argument("--shots", type=int, default=64)

    prod_hw_analysis = sub.add_parser("production-hardware-analysis", help="Run production hardware analysis and final QEC archive generation.")
    prod_hw_analysis.add_argument("--config", required=True)
    prod_hw_analysis.add_argument("--backend-name", default="ibm_fez")
    prod_hw_analysis.add_argument("--code", default="repetition3", choices=["repetition3", "repetition5", "five_qubit_perfect_scaffold"])
    prod_hw_analysis.add_argument("--max-components", type=int, default=None)
    prod_hw_analysis.add_argument("--shots", type=int, default=1024)
    prod_hw_analysis.add_argument("--rounds", type=int, default=3)
    prod_hw_analysis.add_argument("--job-ids-file", default=None)
    prod_hw_analysis.add_argument("--enable-runtime-fetch", action="store_true")
    prod_hw_analysis.add_argument("--force-refresh", action="store_true")
    prod_hw_analysis.add_argument("--calibration-file", default=None)
    prod_hw_analysis.add_argument("--physical-error-rate", type=float, default=0.01)
    prod_hw_analysis.add_argument("--measurement-error-rate", type=float, default=0.02)

    final_demo = sub.add_parser("final-export-demo", help="Run a v4.8 final manuscript/thesis export demo.")
    final_demo.add_argument("--output-dir", default="azmqos_final_export_demo_output")

    prod_final = sub.add_parser("production-final-export", help="Run final manuscript/thesis export and archive generation.")
    prod_final.add_argument("--config", required=True)
    prod_final.add_argument("--backend-name", default="ibm_fez")
    prod_final.add_argument("--code", default="repetition3", choices=["repetition3", "repetition5", "five_qubit_perfect_scaffold"])
    prod_final.add_argument("--max-components", type=int, default=None)
    prod_final.add_argument("--shots", type=int, default=1024)
    prod_final.add_argument("--rounds", type=int, default=3)
    prod_final.add_argument("--job-ids-file", default=None)
    prod_final.add_argument("--enable-runtime-fetch", action="store_true")
    prod_final.add_argument("--force-refresh", action="store_true")
    prod_final.add_argument("--calibration-file", default=None)
    prod_final.add_argument("--physical-error-rate", type=float, default=0.01)
    prod_final.add_argument("--measurement-error-rate", type=float, default=0.02)

    release_demo = sub.add_parser("release-demo", help="Run a v4.9 release-quality demo.")
    release_demo.add_argument("--output-dir", default="azmqos_release_demo_output")

    prod_release = sub.add_parser("production-release-run", help="Run all-in-one production final export + release packaging.")
    prod_release.add_argument("--config", required=True)
    prod_release.add_argument("--backend-name", default="ibm_fez")
    prod_release.add_argument("--code", default="repetition3", choices=["repetition3", "repetition5", "five_qubit_perfect_scaffold"])
    prod_release.add_argument("--max-components", type=int, default=None)
    prod_release.add_argument("--shots", type=int, default=1024)
    prod_release.add_argument("--rounds", type=int, default=3)
    prod_release.add_argument("--job-ids-file", default=None)
    prod_release.add_argument("--enable-runtime-fetch", action="store_true")
    prod_release.add_argument("--force-refresh", action="store_true")
    prod_release.add_argument("--calibration-file", default=None)
    prod_release.add_argument("--physical-error-rate", type=float, default=0.01)
    prod_release.add_argument("--measurement-error-rate", type=float, default=0.02)

    min_pkg = sub.add_parser("release-minimal-package", help="Create a minimal clean ZIP without generated outputs.")
    min_pkg.add_argument("--output-dir", default="azmqos_minimal_package_output")

    pub_info = sub.add_parser("public-release-info", help="Export v5.0 public-release metadata, API docs, and paper-reproduction index.")
    pub_info.add_argument("--output-dir", default="azmqos_public_release_info")

    pub_validate = sub.add_parser("public-release-validate", help="Validate v5.0 public-release files.")
    pub_validate.add_argument("--output-dir", default="azmqos_public_release_validate")

    return parser

def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        result = run_research_platform_pipeline(
            output_dir=args.output_dir,
            shots=args.shots,
            repeats=args.repeats,
            n_rounds=args.rounds,
            n_trials=args.trials,
            measurement_error_probability=args.measurement_error,
            seed=args.seed,
        )
        print(result.summary())
        print("Output directory:", Path(args.output_dir).resolve())
        return 0

    if args.command == "real-terms":
        result = run_real_term_research_pipeline(
            output_dir=args.output_dir,
            term_registry_json=args.term_registry,
            component_registry_json=args.component_registry,
            shots=args.shots,
            repeats=args.repeats,
            n_rounds=args.rounds,
            n_trials=args.trials,
            measurement_error_probability=args.measurement_error,
            seed=args.seed,
            allow_default=not args.no_default,
        )
        print(result.summary())
        print("Output directory:", Path(args.output_dir).resolve())
        return 0

    if args.command == "ibm-diagnose":
        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        config = IBMRuntimeConfig(channel=args.channel, instance=args.instance)
        diagnostics = diagnose_ibm_runtime(config)
        report = make_ibm_runtime_report(diagnostics, out / "ibm_runtime_report.md")
        print(diagnostics.summary())
        print("Report:", report)
        return 0

    if args.command == "ibm-dry-run":
        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        config = IBMRuntimeConfig(
            channel=args.channel,
            instance=args.instance,
            backend_name=args.backend,
            shots=args.shots,
            dry_run=not args.submit,
        )
        result = run_sampler_v2_job(config=config)
        diagnostics = diagnose_ibm_runtime(config)
        report = make_ibm_runtime_report(diagnostics, out / "ibm_runtime_dry_run_report.md", submission_result=result)
        print(result.summary())
        print("Report:", report)
        return 0

    if args.command == "hardware-compare":
        result = run_mock_hardware_comparison(args.output_dir)
        print(result.summary())
        print("Output directory:", Path(args.output_dir).resolve())
        return 0

    if args.command == "mitigate":
        result = run_mock_mitigation_workflow(args.output_dir)
        print(result.summary())
        print("Output directory:", Path(args.output_dir).resolve())
        return 0

    if args.command == "uncertainty":
        from pathlib import Path
        result = run_mock_uncertainty_workflow(
            args.output_dir,
            n_bootstrap=args.bootstrap,
            confidence_level=args.confidence,
        )
        print(result.summary())
        print("Output directory:", Path(args.output_dir).resolve())
        return 0

    if args.command == "runs-demo":
        from pathlib import Path
        db, records, artifacts = create_demo_run_database(args.output_dir)
        print(db.summary())
        print("Records:", len(records))
        print("Output directory:", Path(args.output_dir).resolve())
        for key, value in artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "dashboard-demo":
        from pathlib import Path
        package = build_dashboard_package(args.output_dir)
        print(package.summary_text())
        print("Output directory:", Path(args.output_dir).resolve())
        for key, value in package.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "sync-demo":
        from pathlib import Path
        summary = run_mock_sync_workflow(args.output_dir)
        print(summary.summary())
        print("Output directory:", Path(args.output_dir).resolve())
        for key, value in summary.dashboard_artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "app-init":
        config, artifacts = init_project(args.output_dir, project_name=args.project_name)
        print(config.summary())
        for key, value in artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "app-run":
        result = run_integrated_workflow(args.config)
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "app-report":
        config = load_project_config(args.config)
        print(config.summary())
        issues = validate_project_config(config)
        if issues:
            print("Validation issues:")
            for issue in issues:
                print(f"- {issue}")
        return 0

    if args.command == "production-init":
        spec, artifacts = init_production_project(args.output_dir, project_name=args.project_name)
        print(spec.summary())
        for key, value in artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "production-plan":
        from pathlib import Path
        spec = load_production_spec(args.config)
        issues = validate_production_spec(spec)
        plan = make_production_plan(spec)
        out_dir = Path(spec.output_dir) / "plans"
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = export_production_plan_json(plan, out_dir / "production_plan.json")
        csv_path = export_production_plan_csv(plan, out_dir / "production_plan.csv")
        report_path = make_production_plan_report(plan, out_dir / "production_plan_report.md")
        print(plan.summary())
        if issues:
            print("Validation issues:")
            for issue in issues:
                print(f"- {issue}")
        print("json:", json_path)
        print("csv:", csv_path)
        print("report:", report_path)
        return 0

    if args.command == "production-run":
        result = run_production_dry_run(args.config)
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "production-execute":
        result = run_production_execution_adapter(args.config, force_mode=args.mode)
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "production-simulate":
        result = run_production_simulator_batch(args.config, backend=args.backend, shots=args.shots)
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "production-shot-scaling":
        result = run_production_shot_scaling(args.config, backend=args.backend)
        print("Shot-scaling points:", len(result["points"]))
        print("csv:", result["csv"])
        print("figure:", result["figure"])
        print("manifest:", result["manifest"])
        return 0

    if args.command == "pauli-compile":
        if args.registry:
            results = compile_registry_components(args.registry, args.output_dir, max_components=args.max_components)
            print("Compiled components:", len(results))
            for result in results:
                print(result.summary())
        else:
            result = make_pauli_compile_demo(args.output_dir)
            print(result.summary())
            for key, value in result.artifacts.items():
                print(f"{key}: {value}")
        return 0

    if args.command == "production-pauli-execute":
        result = run_production_pauli_execution(args.config, max_components=args.max_components, shots_per_group=args.shots)
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "production-qiskit-execute":
        result = run_production_qiskit_execution(
            args.config,
            backend=args.backend,
            max_components=args.max_components,
            shots=args.shots,
            hardware_backend_name=args.hardware_backend_name,
        )
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "endvqs-stateprep-demo":
        plan, artifacts = make_stateprep_demo(args.output_dir)
        print(plan.summary())
        for key, value in artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "production-endvqs-execute":
        result = run_production_endvqs_execution(
            args.config,
            stateprep_config_path=args.stateprep_config,
            backend=args.backend,
            max_components=args.max_components,
            shots=args.shots,
        )
        print("END/VQS execution results:", len(result["results"]))
        for item in result["results"]:
            print(item.summary())
        for key, value in result["artifacts"].items():
            print(f"{key}: {value}")
        return 0

    if args.command == "derivative-demo":
        result = run_derivative_demo(args.output_dir)
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "production-derivatives":
        result = run_production_derivative_estimators(
            args.config,
            stateprep_config_path=args.stateprep_config,
            backend=args.backend,
            max_components=args.max_components,
            shots=args.shots,
        )
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "derivative-mitigation-demo":
        result = run_derivative_mitigation_demo(args.output_dir)
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "production-mitigated-derivatives":
        result = run_production_mitigated_derivatives(
            args.config,
            stateprep_config_path=args.stateprep_config,
            backend=args.backend,
            max_components=args.max_components,
            shots=args.shots,
            total_allocation_shots=args.total_allocation_shots,
        )
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "stable-run":
        result = run_stable_workflow(
            args.config,
            backend=args.backend,
            max_components=args.max_components,
            shots=args.shots,
        )
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "stable-smoke-test":
        result = run_stable_smoke_test(args.output_dir)
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "qec-demo":
        result = run_qec_demo(args.output_dir)
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "production-qec-estimate":
        result = run_production_qec_estimator(
            args.config,
            code_name=args.code,
            max_components=args.max_components,
            shots=args.shots,
            physical_error_rate=args.physical_error_rate,
        )
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "qec-decoder-demo":
        result = run_qec_decoder_demo(args.output_dir)
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "production-qec-decode":
        result = run_production_qec_decoder(
            args.config,
            code_name=args.code,
            max_components=args.max_components,
            shots=args.shots,
            physical_error_rate=args.physical_error_rate,
        )
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "ft-qec-demo":
        result = run_ft_qec_demo(args.output_dir)
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "production-ft-qec":
        result = run_production_ft_qec(
            args.config,
            code_name=args.code,
            max_components=args.max_components,
            shots=args.shots,
            rounds=args.rounds,
            physical_error_rate=args.physical_error_rate,
            measurement_error_rate=args.measurement_error_rate,
        )
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "qec-hardware-demo":
        result = run_qec_hardware_demo(
            args.output_dir,
            backend_name=args.backend_name,
            code_name=args.code,
            rounds=args.rounds,
            shots=args.shots,
        )
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "production-qec-hardware-dry-run":
        result = run_production_qec_hardware_dry_run(
            args.config,
            backend_name=args.backend_name,
            code_name=args.code,
            max_components=args.max_components,
            shots=args.shots,
            rounds=args.rounds,
            physical_error_rate=args.physical_error_rate,
            measurement_error_rate=args.measurement_error_rate,
        )
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "qec-hardware-sync-demo":
        result = run_qec_hardware_sync_demo(
            args.output_dir,
            backend_name=args.backend_name,
            rounds=args.rounds,
            shots=args.shots,
        )
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "production-qec-hardware-sync":
        result = run_production_qec_hardware_sync(
            args.config,
            backend_name=args.backend_name,
            code_name=args.code,
            max_components=args.max_components,
            shots=args.shots,
            rounds=args.rounds,
            job_ids_file=args.job_ids_file,
            counts_file=args.counts_file,
            physical_error_rate=args.physical_error_rate,
            measurement_error_rate=args.measurement_error_rate,
        )
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "runtime-fetch-demo":
        result = run_runtime_fetch_demo(
            args.output_dir,
            backend_name=args.backend_name,
            rounds=args.rounds,
            shots=args.shots,
        )
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "production-runtime-sync":
        result = run_production_runtime_sync(
            args.config,
            backend_name=args.backend_name,
            code_name=args.code,
            max_components=args.max_components,
            shots=args.shots,
            rounds=args.rounds,
            job_ids_file=args.job_ids_file,
            enable_runtime_fetch=args.enable_runtime_fetch,
            force_refresh=args.force_refresh,
            physical_error_rate=args.physical_error_rate,
            measurement_error_rate=args.measurement_error_rate,
        )
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "hardware-analysis-demo":
        result = run_hardware_analysis_demo(
            args.output_dir,
            backend_name=args.backend_name,
            rounds=args.rounds,
            shots=args.shots,
        )
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "production-hardware-analysis":
        result = run_production_hardware_analysis(
            args.config,
            backend_name=args.backend_name,
            code_name=args.code,
            max_components=args.max_components,
            shots=args.shots,
            rounds=args.rounds,
            job_ids_file=args.job_ids_file,
            enable_runtime_fetch=args.enable_runtime_fetch,
            force_refresh=args.force_refresh,
            calibration_file=args.calibration_file,
            physical_error_rate=args.physical_error_rate,
            measurement_error_rate=args.measurement_error_rate,
        )
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "final-export-demo":
        result = run_final_export_demo(args.output_dir)
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "production-final-export":
        result = run_production_final_export(
            args.config,
            backend_name=args.backend_name,
            code_name=args.code,
            max_components=args.max_components,
            shots=args.shots,
            rounds=args.rounds,
            job_ids_file=args.job_ids_file,
            enable_runtime_fetch=args.enable_runtime_fetch,
            force_refresh=args.force_refresh,
            calibration_file=args.calibration_file,
            physical_error_rate=args.physical_error_rate,
            measurement_error_rate=args.measurement_error_rate,
        )
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "release-demo":
        result = run_release_demo(args.output_dir)
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "production-release-run":
        result = run_production_release(
            args.config,
            backend_name=args.backend_name,
            code_name=args.code,
            max_components=args.max_components,
            shots=args.shots,
            rounds=args.rounds,
            job_ids_file=args.job_ids_file,
            enable_runtime_fetch=args.enable_runtime_fetch,
            force_refresh=args.force_refresh,
            calibration_file=args.calibration_file,
            physical_error_rate=args.physical_error_rate,
            measurement_error_rate=args.measurement_error_rate,
        )
        print(result.summary())
        for key, value in result.artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "release-minimal-package":
        archive, manifest = run_minimal_package_demo(args.output_dir)
        print(f"minimal_clean_package: {archive}")
        print(f"manifest: {manifest}")
        return 0

    if args.command == "public-release-info":
        artifacts = run_public_release_info(args.output_dir)
        for key, value in artifacts.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "public-release-validate":
        result = run_public_release_validate(args.output_dir)
        for key, value in result.items():
            print(f"{key}: {value}")
        return 0

    parser.print_help()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
