import numpy as np
from .manager import RuntimeManager
from .config import RuntimeConfig

def shot_scaling_experiment(workload, n_min=6, n_max=14, repeats=50, seed=123):
    manager = RuntimeManager()
    rows = []
    for n in range(n_min, n_max + 1):
        shots = 2 ** n
        result = manager.run(workload, "shot_simulator", RuntimeConfig(shots=shots, repeats=repeats, seed=seed))
        mae = result.mean_absolute_error
        rows.append({
            "workload": workload.name,
            "domain": workload.domain,
            "n": n,
            "shots": shots,
            "estimate_real": float(np.real(result.estimate_mean)),
            "mae": mae,
            "log2_mae": float(np.log2(mae)) if mae and mae > 0 else float("-inf"),
        })
    return rows
