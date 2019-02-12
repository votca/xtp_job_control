from ..results import (Options, Results)
from ..runner import run
from .xtp_workflow import (create_promise_command, edit_calculator_options, write_output)
from .workflow_components import call_xtp_cmd


def kmc_workflow(options: dict) -> object:
    """
    Run Votca kmc calculation
    """
    # create results object
    results = Results({})

    # Run KMC multiple
    results['job_kmcmultiple'] = run_kmcmultiple(results)

    # # Run KMC lifetime
    # kmclifetime_file = path_optionfiles / "kmclifetime.xml"
    # args2 = create_promise_command(
    #     "xtp_run - e kmclifetime -o {} -f {}", kmclifetime_file, options["state_file"])

    # results["job_kmlifetime"] = call_xtp_cmd(args2, workdir / "kmclifetime", expected_output={})

    output = run(results)
    write_output(output, options)


def run_kmcmultiple(results: dict, options: Options) -> dict:
    """
    Run a kmcmultiple job
    """

    results['job_opts_kmcmultiple'] = edit_calculator_options(
        results, ['kmcmultiple'])

    args1 = create_promise_command(
        "xtp_run - e kmcmultiple -o {} -f {}", results['job_opts_kmcmultiple']['kmcmultiple'],
        results["options"]["state_file"])

    return call_xtp_cmd(args1, options.scratch_dir / "kmcmultiple", expected_output={})
