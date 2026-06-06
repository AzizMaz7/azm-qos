from __future__ import annotations
from pathlib import Path
import numpy as np

def matplotlib_available() -> bool:
    try:
        import matplotlib.pyplot as plt  # noqa: F401
        return True
    except Exception:
        return False

def _write_placeholder(path, title, payload):
    path = Path(path)
    path.write_text(title + "\n" + "=" * len(title) + "\n\n" + str(payload), encoding="utf-8")
    return path

def plot_m_matrix(M, path, title="END/VQS M matrix"):
    path = Path(path)
    M = np.asarray(M)
    if not matplotlib_available():
        return _write_placeholder(path.with_suffix(".txt"), title, M)

    import matplotlib.pyplot as plt
    fig = plt.figure()
    ax = fig.add_subplot(111)
    im = ax.imshow(M)
    ax.set_title(title)
    ax.set_xlabel("j")
    ax.set_ylabel("i")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path

def plot_v_vector(V, path, title="END/VQS V vector"):
    path = Path(path)
    V = np.asarray(V).reshape(-1)
    if not matplotlib_available():
        return _write_placeholder(path.with_suffix(".txt"), title, V)

    import matplotlib.pyplot as plt
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.bar(range(len(V)), V)
    ax.set_title(title)
    ax.set_xlabel("index")
    ax.set_ylabel("value")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path

def plot_matching_failure_rates(benchmark_result, path, title="Matching decoder failure rate"):
    path = Path(path)
    x = [p.error_probability for p in benchmark_result.points]
    y = [p.logical_failure_rate for p in benchmark_result.points]
    if not matplotlib_available():
        return _write_placeholder(path.with_suffix(".txt"), title, {"x": x, "y": y})

    import matplotlib.pyplot as plt
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(x, y, marker="o")
    ax.set_title(title)
    ax.set_xlabel("detector error probability")
    ax.set_ylabel("logical failure rate")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path
