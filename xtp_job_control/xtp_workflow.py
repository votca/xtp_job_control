from __future__ import (absolute_import, print_function)
from subprocess import (PIPE, Popen)
# from toil.job import Job
import os


def xtp_workflow(job, options, dict_ids):
    """
    Workflow to run a complete xtp xssimulation
    """
    job.log("Dictionary: {}".format(dict_ids))

    Step1
    runs the mapping from MD coordinates to segments and creates .sql file
    state = "state.sql"
    cmd = "xtp_map -t {} -c {} -s {} -f {}".format(
        dict_ids['tpr'], dict_ids['gro'], dict_ids['system'], state)

    job.log("command: {}".format(cmd))
    call_xtp_cmd(job, cmd)



def send_files_to_storage(toil, options, input_files):
    """
    Import `input_files` into the Storage, using a Toil handler see:
    https://toil.readthedocs.io/en/latest/developingWorkflows/toilAPIJobstore.html#toil.jobStores.abstractJobStore.AbstractJobStore.importFile

    :returns: Dictionary of file_name: fileID pairs
    """
    def create_url(relative_path):
        return 'file://' + os.path.abspath(relative_path)

    dict_ids = {}
    for key in input_files:
        file_path = getattr(options, key)
        url = create_url(file_path)
        toil.importFile(url, sharedFileName="1333333")
        dict_ids[key] = url

    return dict_ids
    # return {key: toil.importFile(create_url(getattr(options, key))) for key in input_files}


def call_xtp_cmd(job, cmd, expected_output=None):
    """
    Run a bash command
    """
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
    rs = p.communicate()
    err = rs[1]
    job.log("output: {}".format(err))
    if err:
        return None
        print("Submission Errors: {}".format(err))
    else:
        return "done!"
