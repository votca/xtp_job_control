from noodles import run_logging
from noodles.display import NCDisplay


def run(job, n_processes=1, cache='cache.json'):
    """
    Run locally using several threads.
    """
    with NCDisplay() as display:
            return run_logging(
                job, n_processes, display)
