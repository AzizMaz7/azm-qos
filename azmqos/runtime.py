from .manager import RuntimeManager
from .config import RuntimeConfig

class ShotRuntime:
    """Compatibility wrapper from earlier versions."""
    def __init__(self, seed=None):
        self.seed = seed

    def run(self, workload, shots=4096, repeats=1):
        manager = RuntimeManager()
        config = RuntimeConfig(shots=shots, repeats=repeats, seed=self.seed)
        return manager.run(workload, backend_name="shot_simulator", config=config)

RuntimeResult = object
