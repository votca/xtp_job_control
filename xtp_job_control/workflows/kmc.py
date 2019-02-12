from ..results import Results
from ..runner import run
from .xtp_workflow import (run_kmclifetime, run_kmcmultiple, write_output)


def kmc_workflow(options: dict) -> object:
    """
    Run Votca kmc calculation
    """
    # create results object
    results = Results({})

    # Run KMC multiple
    results['job_kmcmultiple'] = run_kmcmultiple(results, options)

    # Run KMC lifetime
    results['job_kmclifetime'] = run_kmclifetime(results, options)

    output = run(results)
    path_output = "results_kmc.yml"
    write_output(output, options, path_output)

    print("check output file: ", path_output)
