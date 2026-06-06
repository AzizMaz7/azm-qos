import numpy as np

def normalize_state(state):
    state = np.asarray(state, dtype=complex).reshape(-1)
    norm = np.vdot(state, state)
    if np.isclose(norm, 0.0):
        raise ValueError("Cannot normalize zero vector.")
    return state / np.sqrt(norm)

def zero_state(n_qubits: int):
    state = np.zeros(2 ** n_qubits, dtype=complex)
    state[0] = 1.0
    return state

def product_ry_state(thetas):
    state = np.array([1.0 + 0.0j])
    for theta in thetas:
        c, s = np.cos(theta / 2), np.sin(theta / 2)
        state = np.kron(state, np.array([c, s], dtype=complex))
    return normalize_state(state)

def bell_state():
    state = np.zeros(4, dtype=complex)
    state[0] = state[3] = 1 / np.sqrt(2)
    return state

def ghz_state(n_qubits: int):
    state = np.zeros(2 ** n_qubits, dtype=complex)
    state[0] = state[-1] = 1 / np.sqrt(2)
    return state
