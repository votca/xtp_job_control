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
    results['job_kmcmultiple'] = run_kmcmultiple(results, options, state=options.state)

    # Run KMC lifetime
    results['job_kmclifetime'] = run_kmclifetime(results, options, state=options.state)

    output = run(results)
    name_output = "results_kmc"
    write_output(output, options, name_output)

    print("check output file: ", name_output)
