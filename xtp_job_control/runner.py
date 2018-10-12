from noodles import (run_logging, run_single)
from noodles.run.threading.sqlite3 import run_parallel
from noodles.display import NCDisplay
from typing import Any


def run(wf: object, runner: str='parallel', n_processes: int=1, cache: str='cache.db') -> Any:
    """
    Run a workflow `wf` using `runner` and `n_processes` number of threads/process
    """
    runner = runner.lower()

    if runner == 'display':
        with NCDisplay() as display:
            return run_logging(wf, n_processes, display)
    elif runner == 'serial':
        return run_single(wf)
    else:
        return run_parallel(wf, n_threads=n_processes, db_file=cache, always_cache=True)
