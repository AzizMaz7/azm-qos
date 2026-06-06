from .terms import (
    ENDVQSTermRegistry,
    default_endvqs_registry,
    create_custom_registry,
)
from .builders import (
    ENDVQSParameterPoint,
    default_endvqs_state_preparation,
    build_m_matrix_workloads,
    build_v_vector_workloads,
    build_all_endvqs_workloads,
)
from .assemblers import (
    assemble_m_matrix,
    assemble_v_vector,
    assembled_results_summary,
)
from .benchmarks import run_endvqs_benchmark
from .reports import make_endvqs_report
from .plugin import ENDVQSWorkloadPlugin

__all__ = [
    "ENDVQSTermRegistry",
    "default_endvqs_registry",
    "create_custom_registry",
    "ENDVQSParameterPoint",
    "default_endvqs_state_preparation",
    "build_m_matrix_workloads",
    "build_v_vector_workloads",
    "build_all_endvqs_workloads",
    "assemble_m_matrix",
    "assemble_v_vector",
    "assembled_results_summary",
    "run_endvqs_benchmark",
    "make_endvqs_report",
    "ENDVQSWorkloadPlugin",
]


# v1.1 real-term registry exports
from .components import (
    ENDVQSComponent,
    ENDVQSComponentRegistry,
    default_component_registry_from_proxy_terms,
    component_registry_to_term_registry,
)
from .registry_io import (
    save_term_registry_json,
    load_term_registry_json,
    save_component_registry_json,
    load_component_registry_json,
    save_term_registry_csv,
    load_term_registry_csv,
)
from .validation import (
    RegistryValidationResult,
    validate_term_registry,
    compare_m_entry_term_signatures,
    m_symmetry_diagnostics,
)
