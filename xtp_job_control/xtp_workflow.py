from __future__ import (absolute_import, print_function)
from subprocess import (PIPE, Popen)
# from toil.job import Job
import os


def xtp_workflow(job, options, dict_ids):
    """
    Workflow to run a complete xtp xssimulation
    """
    job.log("options: {}".format(options))
    setup_environment(job, options)
    job.log("Dictionary: {}".format(dict_ids))
    # Setup the environment to run the simulation
    # setup(job)
    # STep1
    # runs the mapping from MD coordinates to segments and creates .sql file
    # cmd = "xtp_map -t {}/topol.tpr -c {}/conf.gro -s system.xml -f state.sql "
    # xtp_map -t 


def setup_environment(job, options):
    """
    Create temporal folder and copy the setting to the temporal folder.
    """
    pass


def send_files_to_storage(toil, options, input_files):
    """
    Import `input_files` into the Storage, using a Toil handler see:
    https://toil.readthedocs.io/en/latest/developingWorkflows/toilAPIJobstore.html#toil.jobStores.abstractJobStore.AbstractJobStore.importFile

    :returns: Dictionary of file_name: fileID pairs
    """
    def create_url(relative_path):
        return 'file://' + os.path.abspath(relative_path)

    return {key: toil.importFile(create_url(getattr(options, key))) for key in input_files}


def call_xtp_cmd(cmd, expected_output=""):
    """
    Run a bash command
    """
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
    rs = p.communicate()
    err = rs[1]
    if err:
        return None
        print("Submission Errors: {}".format(err))
    else:
        return "done!"
