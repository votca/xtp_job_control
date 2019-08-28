from ..results import Results
from ..runner import run
from .xtp_workflow import run_dftgwbse
import logging
import shutil

logger = logging.getLogger(__name__)


def dftgwbse_workflow(options: dict) -> object:

    # create results object
    results = Results({})

    # Run DFT + GWBSE
    results['dftgwbse'] = run_dftgwbse(results, options)
    output = run(results)

    for x in ("log", "out"):
        shutil.copy(output['dftgwbse'][x], options["workdir"])

    print("DFT GWBSE finished!!")
