from ..results import Results
from ..runner import run
from .xtp_workflow import (run_dftgwbse, run_partialcharges, write_output)
import logging

logger = logging.getLogger(__name__)


def dftgwbse_workflow(options: dict) -> object:

    # create results object
    results = Results({})

    # Run DFT + GWBSE
    results['dftgwbse'] = run_dftgwbse(results, options)

    # # Compute partial charges
    # results['partialcharges'] = run_partialcharges(results, options)

    output = run(results)
    write_output(output, options)


