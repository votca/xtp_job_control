from ..results import (Options, Results)
from ..runner import run
from .xtp_workflow import (create_promise_command, edit_calculator_options, write_output)
from .workflow_components import (call_xtp_cmd, wait_till_done)


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
    write_output(output, options)


def run_kmcmultiple(results: dict, options: Options) -> dict:
    """
    Run a kmcmultiple job
    """

    results['job_opts_kmcmultiple'] = edit_calculator_options(
        results, options, ['kmcmultiple'])

    args = create_promise_command(
        "xtp_run -e kmcmultiple -o {} -f {}", results['job_opts_kmcmultiple']['kmcmultiple'],
        options.state_file)

    return call_xtp_cmd(args, options.scratch_dir / "kmcmultiple", expected_output={
        "timedependence": "timedependence.csv",
        "trajectory": "trajectory.csv"
    })


def run_kmclifetime(results: dict, options: Options) -> dict:
    """
    Run a kmclifetime job
    """
    # Add dependency to kmcmultiple
    wait_till_done(results['job_kmcmultiple'])

    options.votca_calculators_options["kmclifetime"]["lifetimefile"] = options.lifetimes_file
    results['job_opts_kmclifetime'] = edit_calculator_options(
        results, options, ['kmclifetime'])

    args = create_promise_command(
        "xtp_run -e kmclifetime -o {} -f {}", results['job_opts_kmclifetime']['kmclifetime'],
        options.state_file)

    return call_xtp_cmd(args, options.scratch_dir / "kmclifetime", expected_output={
        "lifetimes": "*csv"})
