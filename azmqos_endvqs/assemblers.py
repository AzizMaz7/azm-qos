from __future__ import annotations
import numpy as np

def _result_value(result):
    return float(np.real(result.estimate_mean))

def assemble_m_matrix(results, dimension: int | None = None):
    """Assemble an M matrix from END/VQS M-entry JobResult objects."""
    pairs = []
    for result in results:
        meta = getattr(result, "metadata", {})
        # JobResult metadata from backend; workload metadata is not preserved directly.
        # We store workload name as fallback: endvqs_M_i_j
        name = result.workload_name
        if name.startswith("endvqs_M_"):
            _, _, i, j = name.split("_")
            pairs.append((int(i), int(j), _result_value(result)))
    if not pairs:
        raise ValueError("No M-matrix results found. Expected workload names like endvqs_M_i_j.")

    dim = dimension or (max(max(i, j) for i, j, _ in pairs) + 1)
    M = np.zeros((dim, dim), dtype=float)
    for i, j, value in pairs:
        M[i, j] = value
    return M

def assemble_v_vector(results, dimension: int | None = None):
    """Assemble a V vector from END/VQS V-entry JobResult objects."""
    entries = []
    for result in results:
        name = result.workload_name
        if name.startswith("endvqs_V_"):
            _, _, i = name.split("_")
            entries.append((int(i), _result_value(result)))
    if not entries:
        raise ValueError("No V-vector results found. Expected workload names like endvqs_V_i.")

    dim = dimension or (max(i for i, _ in entries) + 1)
    V = np.zeros(dim, dtype=float)
    for i, value in entries:
        V[i] = value
    return V

def assembled_results_summary(M=None, V=None):
    lines = ["END/VQS assembled results"]
    if M is not None:
        lines.append("M matrix:")
        lines.append(str(np.asarray(M)))
    if V is not None:
        lines.append("V vector:")
        lines.append(str(np.asarray(V)))
    return "\n".join(lines)
