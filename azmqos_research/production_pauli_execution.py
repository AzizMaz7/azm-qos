from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import csv, hashlib, itertools, json, math, time
from .production import ProductionProjectSpec, load_production_spec, select_components_from_registry, _read_component_registry
from .pauli_compiler import PauliComponent, PauliTerm, CommutingGroup, PauliCompilationResult, pauli_component_from_dict, compile_pauli_component, expectation_from_counts_for_pauli, can_share_single_qubit_measurement_basis
from .experiment_db import ExperimentDatabase, BackendMetadataRecord, new_run_record, artifact_from_path, export_run_table_csv, export_dashboard_json, make_run_database_report
from .dashboard import build_dashboard_package

@dataclass
class GroupedMeasurementResult:
    component_name: str
    group_id: str
    measurement_basis: str
    shots: int
    counts: dict[str, int]
    term_expectations: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)
    def summary(self) -> str:
        return f"GroupedMeasurementResult\n  component: {self.component_name}\n  group_id: {self.group_id}\n  basis: {self.measurement_basis}\n  shots: {self.shots}\n  term_expectations: {self.term_expectations}"

@dataclass
class ComponentEstimateResult:
    component_name: str
    quantity: str
    family: str | None
    indices: list[int]
    estimate: complex
    n_terms: int
    n_groups: int
    shots_per_group: int
    grouped_results: list[GroupedMeasurementResult]
    metadata: dict[str, Any] = field(default_factory=dict)
    @property
    def estimate_real(self) -> float: return float(self.estimate.real)
    @property
    def estimate_imag(self) -> float: return float(self.estimate.imag)
    def summary(self) -> str:
        return ("ComponentEstimateResult\n"
                f"  component: {self.component_name}\n  quantity: {self.quantity}\n  family: {self.family}\n"
                f"  indices: {self.indices}\n  estimate: {self.estimate.real:+.10f}{self.estimate.imag:+.10f}j\n"
                f"  n_terms: {self.n_terms}\n  n_groups: {self.n_groups}\n  shots_per_group: {self.shots_per_group}")

@dataclass
class ProductionPauliExecutionResult:
    spec: ProductionProjectSpec
    components: list[PauliComponent]
    compilation_results: list[PauliCompilationResult]
    component_estimates: list[ComponentEstimateResult]
    output_dir: str
    artifacts: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    def summary(self) -> str:
        by_quantity = {}
        for item in self.component_estimates:
            by_quantity[item.quantity] = by_quantity.get(item.quantity, 0) + 1
        return ("ProductionPauliExecutionResult\n"
                f"  project: {self.spec.project_name}\n  components: {len(self.components)}\n"
                f"  compiled: {len(self.compilation_results)}\n  estimates: {len(self.component_estimates)}\n"
                f"  by_quantity: {by_quantity}\n  artifacts: {len(self.artifacts)}\n  warnings: {self.warnings}")

def _json_default(obj):
    if isinstance(obj, complex): return [obj.real, obj.imag]
    return str(obj)

def _stable_unit_interval(text: str) -> float:
    digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
    return int(digest[:14], 16) / float(16**14 - 1)

def qubit_expectations_for_basis(component_name: str, basis: str) -> list[float]:
    values = []
    for idx, ch in enumerate(basis):
        if ch == 'I': values.append(1.0)
        else: values.append(-0.85 + 1.70 * _stable_unit_interval(f"{component_name}|{basis}|{idx}|{ch}"))
    return values

def exact_group_expectation_for_pauli(component_name: str, measurement_basis: str, pauli: str) -> float:
    value = 1.0
    for e, p in zip(qubit_expectations_for_basis(component_name, measurement_basis), pauli):
        if p != 'I': value *= e
    return float(value)

def _bitstring_probability(bitstring: str, qubit_expectations: list[float]) -> float:
    prob = 1.0
    for bit, exp_z in zip(bitstring, qubit_expectations):
        p0 = 0.5 * (1.0 + exp_z)
        prob *= p0 if bit == '0' else (1.0 - p0)
    return float(prob)

def deterministic_counts_for_basis(component_name: str, basis: str, shots: int) -> dict[str, int]:
    n = len(basis)
    bitstrings = [''.join(bits) for bits in itertools.product('01', repeat=n)]
    qubit_exps = qubit_expectations_for_basis(component_name, basis)
    raw = {b: _bitstring_probability(b, qubit_exps) * shots for b in bitstrings}
    counts = {b: int(math.floor(v)) for b, v in raw.items()}
    remainder = shots - sum(counts.values())
    order = sorted(bitstrings, key=lambda b: (raw[b] - math.floor(raw[b]), b), reverse=True)
    for b in order[:remainder]: counts[b] += 1
    return counts

def execute_commuting_group(component: PauliComponent, group: CommutingGroup, shots: int) -> GroupedMeasurementResult:
    counts = deterministic_counts_for_basis(component.name, group.measurement_basis, shots)
    term_expectations = {term.normalized_string(): expectation_from_counts_for_pauli(counts, term.normalized_string()) for term in group.terms}
    return GroupedMeasurementResult(component.name, group.group_id, group.measurement_basis, shots, counts, term_expectations,
                                   metadata={'qubit_expectations': qubit_expectations_for_basis(component.name, group.measurement_basis)})

def reconstruct_component_estimate(component: PauliComponent, grouped_results: list[GroupedMeasurementResult], shots_per_group: int) -> ComponentEstimateResult:
    total = 0.0 + 0.0j
    group_by_basis = {g.measurement_basis: g for g in grouped_results}
    for term in component.terms:
        pauli = term.normalized_string()
        chosen = None
        for basis, result in group_by_basis.items():
            if can_share_single_qubit_measurement_basis(pauli, basis):
                chosen = result; break
        if chosen is None: raise KeyError(f'No grouped result can measure term {pauli}.')
        total += term.coefficient * chosen.term_expectations.get(pauli, expectation_from_counts_for_pauli(chosen.counts, pauli))
    family = component.metadata.get('component_family') if component.metadata else None
    return ComponentEstimateResult(component.name, component.quantity, family, list(component.indices), total, len(component.terms), len(grouped_results), shots_per_group, grouped_results, metadata={'source':'grouped_pauli_measurement_simulation'})

def execute_component_pauli_measurements(component: PauliComponent, shots_per_group: int = 1024) -> tuple[PauliCompilationResult, ComponentEstimateResult]:
    compilation = compile_pauli_component(component, product_basis_only=True)
    grouped = [execute_commuting_group(component, group, shots_per_group) for group in compilation.groups]
    return compilation, reconstruct_component_estimate(component, grouped, shots_per_group)

def load_selected_pauli_components(spec: ProductionProjectSpec, max_components: int | None = None) -> list[PauliComponent]:
    if not spec.component_registry_path: return []
    registry = _read_component_registry(spec.component_registry_path)
    selected = select_components_from_registry(registry, spec.observable_selection)
    if max_components is not None: selected = selected[:max_components]
    return [pauli_component_from_dict(data) for data in selected]

def export_grouped_counts_json(estimates: list[ComponentEstimateResult], path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    payload = []
    for est in estimates:
        payload.append({'component_name': est.component_name, 'quantity': est.quantity, 'family': est.family, 'indices': est.indices, 'estimate': [est.estimate.real, est.estimate.imag], 'groups': [asdict(g) for g in est.grouped_results]})
    path.write_text(json.dumps(payload, indent=2, default=_json_default), encoding='utf-8')
    return path

def export_component_estimates_csv(estimates: list[ComponentEstimateResult], path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['component_name','quantity','family','indices','estimate_real','estimate_imag','n_terms','n_groups','shots_per_group'])
        for item in estimates:
            w.writerow([item.component_name,item.quantity,item.family,json.dumps(item.indices),item.estimate.real,item.estimate.imag,item.n_terms,item.n_groups,item.shots_per_group])
    return path

def export_grouped_counts_csv(estimates: list[ComponentEstimateResult], path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['component_name','group_id','measurement_basis','shots','counts_json','term_expectations_json'])
        for est in estimates:
            for group in est.grouped_results:
                w.writerow([est.component_name, group.group_id, group.measurement_basis, group.shots, json.dumps(group.counts), json.dumps(group.term_expectations)])
    return path

def export_mv_estimate_tables(estimates: list[ComponentEstimateResult], output_dir):
    output_dir = Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    paths = {'M_estimates_csv': output_dir/'M_estimates.csv', 'V_estimates_csv': output_dir/'V_estimates.csv'}
    for quantity, path in [('M', paths['M_estimates_csv']), ('V', paths['V_estimates_csv'])]:
        with Path(path).open('w', newline='', encoding='utf-8') as f:
            w = csv.writer(f); w.writerow(['component_name','family','indices','estimate_real','estimate_imag','n_terms','n_groups'])
            for item in estimates:
                if item.quantity == quantity:
                    w.writerow([item.component_name,item.family,json.dumps(item.indices),item.estimate.real,item.estimate.imag,item.n_terms,item.n_groups])
    return {k: str(v) for k, v in paths.items()}

def plot_component_estimates(estimates: list[ComponentEstimateResult], path):
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except Exception:
        txt = path.with_suffix('.txt'); txt.write_text('\n'.join(item.summary() for item in estimates), encoding='utf-8'); return txt
    labels = [x.component_name for x in estimates]; values = [x.estimate.real for x in estimates]; x = list(range(len(labels)))
    fig = plt.figure(); ax = fig.add_subplot(111); ax.bar(x, values)
    ax.set_xlabel('component'); ax.set_ylabel('estimate real part'); ax.set_title('END/VQS component estimates from grouped Pauli measurements')
    if len(labels) <= 10: ax.set_xticks(x); ax.set_xticklabels(labels, rotation=45, ha='right')
    fig.tight_layout(); fig.savefig(path, dpi=250); plt.close(fig); return path

def attach_pauli_estimates_to_database(spec: ProductionProjectSpec, estimates: list[ComponentEstimateResult], database_path, artifact_paths: dict[str, str] | None = None):
    db = ExperimentDatabase(database_path); artifact_paths = artifact_paths or {}; records=[]
    for item in estimates:
        artifacts = [artifact_from_path(path, name=name, artifact_type='pauli_execution_artifact') for name, path in artifact_paths.items()]
        record = new_run_record(name=f'pauli_{item.component_name}', run_type='production_pauli_execution', status='completed', tags=['production','pauli',item.family or 'unknown',item.quantity],
            parameters={'component_name':item.component_name,'quantity':item.quantity,'indices':item.indices,'n_terms':item.n_terms,'n_groups':item.n_groups,'shots_per_group':item.shots_per_group},
            metrics={'estimate_real':item.estimate.real,'estimate_imag':item.estimate.imag,'n_terms':float(item.n_terms),'n_groups':float(item.n_groups),'shots_per_group':float(item.shots_per_group)},
            backend=BackendMetadataRecord(backend_name='local_grouped_pauli_simulator', job_status='LOCAL_COMPLETED', timestamp_unix=time.time()), artifacts=artifacts,
            notes='Component estimate reconstructed from grouped Pauli measurement counts.')
        db.append(record); records.append(record)
    return db, records

def make_mv_estimate_report(estimates: list[ComponentEstimateResult], output_path):
    output_path = Path(output_path)
    lines = ['# AZM-QOS v3.5 END/VQS M/V Estimate Report','', '## Summary','', f'- Total components: **{len(estimates)}**', f'- M components: **{sum(1 for x in estimates if x.quantity == "M")}**', f'- V components: **{sum(1 for x in estimates if x.quantity == "V")}**', '', '## Component estimates','']
    for item in estimates: lines += ['```text', item.summary(), '```', '']
    lines += ['## Scientific note','', 'These estimates are reconstructed from local deterministic grouped Pauli measurement counts. Replace the simulator with real grouped circuit execution for final simulator/hardware production.', '']
    output_path.write_text('\n'.join(lines), encoding='utf-8'); return output_path

def make_production_pauli_execution_report(result: ProductionPauliExecutionResult, output_path):
    output_path = Path(output_path)
    lines = ['# AZM-QOS v3.5 Production Pauli Execution Report','', '## Summary','', '```text', result.summary(), '```', '', '## Component estimates','']
    for item in result.component_estimates: lines += ['```text', item.summary(), '```', '']
    if result.warnings:
        lines += ['## Warnings',''] + [f'- {w}' for w in result.warnings] + ['']
    lines += ['## Artifacts',''] + [f'- **{k}**: `{v}`' for k, v in result.artifacts.items()] + ['', '## Safety note','', 'v3.5 performs local grouped Pauli measurement simulation only. No IBM hardware jobs are submitted.', '']
    output_path.write_text('\n'.join(lines), encoding='utf-8'); return output_path

def run_production_pauli_execution(spec_or_path, max_components: int | None = None, shots_per_group: int | None = None) -> ProductionPauliExecutionResult:
    spec = load_production_spec(spec_or_path) if isinstance(spec_or_path, (str, Path)) else spec_or_path
    output_dir = Path(spec.output_dir); pauli_dir = output_dir/'pauli_execution'; pauli_dir.mkdir(parents=True, exist_ok=True)
    shots = int(shots_per_group or spec.execution_policy.shots); warnings=[]
    components = load_selected_pauli_components(spec, max_components=max_components)
    if not components: warnings.append('No Pauli components selected. Check component_registry_path and observable selection.')
    compilations=[]; estimates=[]
    for component in components:
        comp, est = execute_component_pauli_measurements(component, shots_per_group=shots)
        compilations.append(comp); estimates.append(est)
    artifacts = {}
    artifacts['grouped_counts_json'] = str(export_grouped_counts_json(estimates, pauli_dir/'grouped_counts.json'))
    artifacts['grouped_counts_csv'] = str(export_grouped_counts_csv(estimates, pauli_dir/'grouped_counts.csv'))
    artifacts['component_estimates_csv'] = str(export_component_estimates_csv(estimates, pauli_dir/'component_estimates.csv'))
    artifacts.update(export_mv_estimate_tables(estimates, pauli_dir))
    artifacts['component_estimates_figure'] = str(plot_component_estimates(estimates, pauli_dir/'component_estimates.png'))
    artifacts['mv_estimate_report'] = str(make_mv_estimate_report(estimates, pauli_dir/'mv_estimate_report.md'))
    db, records = attach_pauli_estimates_to_database(spec, estimates, output_dir/'database'/'production_pauli_execution_runs.jsonl', artifact_paths={'component_estimates_csv':artifacts['component_estimates_csv'], 'grouped_counts_json':artifacts['grouped_counts_json'], 'M_estimates_csv':artifacts['M_estimates_csv'], 'V_estimates_csv':artifacts['V_estimates_csv']})
    artifacts['pauli_execution_database_jsonl'] = str(db.path)
    artifacts['pauli_execution_run_table_csv'] = str(export_run_table_csv(records, output_dir/'database'/'pauli_execution_run_table.csv'))
    artifacts['pauli_execution_dashboard_json'] = str(export_dashboard_json(records, output_dir/'database'/'pauli_execution_dashboard.json'))
    artifacts['pauli_execution_database_report'] = str(make_run_database_report(records, output_dir/'database'/'pauli_execution_database_report.md'))
    dashboard = build_dashboard_package(output_dir/'dashboard_pauli_execution', database_path=db.path)
    artifacts['dashboard_manifest'] = dashboard.artifacts.get('manifest','')
    artifacts['dashboard_html'] = dashboard.artifacts.get('dashboard_html','')
    artifacts['artifact_browser_html'] = dashboard.artifacts.get('artifact_browser_html','')
    result = ProductionPauliExecutionResult(spec, components, compilations, estimates, str(output_dir), artifacts, warnings)
    artifacts['production_pauli_execution_report'] = str(make_production_pauli_execution_report(result, pauli_dir/'production_pauli_execution_report.md'))
    manifest_path = pauli_dir/'production_pauli_execution_manifest.json'
    manifest_path.write_text(json.dumps({'package':'AZM-QOS v3.5 production Pauli execution','summary':result.summary(),'warnings':warnings,'artifacts':artifacts,'component_estimates':[{'component_name':x.component_name,'quantity':x.quantity,'family':x.family,'indices':x.indices,'estimate':[x.estimate.real,x.estimate.imag],'n_terms':x.n_terms,'n_groups':x.n_groups} for x in estimates]}, indent=2, default=_json_default), encoding='utf-8')
    artifacts['production_pauli_execution_manifest'] = str(manifest_path)
    return ProductionPauliExecutionResult(spec, components, compilations, estimates, str(output_dir), artifacts, warnings)
