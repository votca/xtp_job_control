from noodles import (gather_dict, run_logging, run_single, serial)
from noodles.run.threading.sqlite3 import run_parallel as run_provenance
from noodles.display import NCDisplay
from noodles.serial import Registry
from noodles.serial.numpy import arrays_to_hdf5
from typing import Any
from .results import Results


def run(wf: object, runner: str = 'parallel', n_processes: int = 1,
        cache: str = 'cache.db', ) -> Any:
    """
    Run a workflow `wf` using `runner` and `n_processes` number of threads/process
    """
    runner = runner.lower()

    if isinstance(wf, Results):
        wf = gather_dict(**wf.state)

    if runner == 'display':
        with NCDisplay() as display:
            return run_logging(wf, n_processes, display)
    elif runner == 'serial':
        return run_single(wf)
    else:
        return run_provenance(
            wf, n_threads=n_processes, db_file=cache, registry=registry, echo_log=False,
            always_cache=False)


def registry():
    """
    This function pass to the noodles infrascture all the information
    related to the Structure of the Package object that is schedule.
    This *Registry* class contains hints that help Noodles to encode
    and decode this Package object.
    """
    return Registry(
        parent=serial.base() + arrays_to_hdf5())
