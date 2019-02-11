from ..results import Results
from ..runner import run
from .xtp_workflow import (create_promise_command, write_output)
from .workflow_components import call_xtp_cmd
from noodles import gather_dict


def kmc_workflow(options: dict) -> object:
    """
    Run Votca kmc calculation
    """
    workdir = options['scratch_dir']
    path_optionfiles = options['path_optionfiles']

    # create results object
    results = Results({'options': options.copy()})

    # Run KMC multiple
    kmcmultiple_file = path_optionfiles / "kmcmultiple.xml"
    args = create_promise_command(
        "xtp_run - e kmcmultiple -o {} -f {}", kmcmultiple_file, options["state_file"])

    results["job_kmcmultiple"] = call_xtp_cmd(args, workdir, expected_output={})

    output = run(results)
    write_output(output)

    # xtp_run -e kmcmultiple -o OPTIONFILES/kmcmultiple.xml -f state.sql
    # xtp_run -e kmclifetime -o OPTIONFILES/kmclifetime.xml -f state.sql 
