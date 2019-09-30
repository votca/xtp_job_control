from ..results import Results
from ..runner import run
from .xtp_workflow import run_dftgwbse
from pathlib import Path
import logging
import os
import shutil

logger = logging.getLogger(__name__)


def dftgwbse_workflow(options: dict):
    """
    Call the DFT GW-BSE workflows
    """
    # create results object
    results = Results({})

    # create a new folder to store the results
    mol_name = options.molecule.stem
    workdir = Path(options.workdir) / mol_name
    os.makedirs(workdir.as_posix(), exist_ok=True)

    # Run DFT + GWBSE
    results['dftgwbse'] = run_dftgwbse(results, options)
    output = run(results)

    for x in ("log", "out"):
        shutil.copy(output['dftgwbse'][x], workdir)

    print("DFT GWBSE finished!!")
