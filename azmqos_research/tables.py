from __future__ import annotations
from pathlib import Path
import csv
import numpy as np

def export_m_matrix_csv(M, path):
    path = Path(path)
    M = np.asarray(M)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["i", "j", "value"])
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                writer.writerow([i, j, float(M[i, j])])
    return path

def export_v_vector_csv(V, path):
    path = Path(path)
    V = np.asarray(V).reshape(-1)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["i", "value"])
        for i, value in enumerate(V):
            writer.writerow([i, float(value)])
    return path

def export_benchmark_table_csv(benchmark_result, path):
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["error_probability", "n_trials", "n_logical_failures", "logical_failure_rate", "decoder_name"])
        for point in benchmark_result.points:
            writer.writerow([
                point.error_probability,
                point.n_trials,
                point.n_logical_failures,
                point.logical_failure_rate,
                point.decoder_name,
            ])
    return path
