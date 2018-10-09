from noodles import schedule
from subprocess import (PIPE, Popen)
from typing import Dict
from .runner import run


def xtp_workflow(options: Dict):
    """
    Workflow to run a complete xtp xssimulation
    """
    print(options)

    # Step1
    # runs the mapping from MD coordinates to segments and creates .sql file
    state = "state.sql"
    cmd = "xtp_map -t {} -c {} -s {} -f {}".format(
        options['tpr'], options['gro'], options['system'], state)

    print("command: {}".format(cmd))
    job = call_xtp_cmd(cmd)

    run(job)


@schedule
def call_xtp_cmd(cmd, cwd=None, expected_output=None):
    """
    Run a bash command
    """
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True, cwd=cwd)
    rs = p.communicate()
    err = rs[1]
    if err:
        return None
        print("Submission Errors: {}".format(err))
    else:
        return "done!"
