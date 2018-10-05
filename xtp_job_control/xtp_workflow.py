from __future__ import (absolute_import, print_function)
from subprocess import (PIPE, Popen)
from toil.job import Job



def xtp_workflow(job, options):
    """
    Workflow to run a complete xtp xssimulation
    """
    job.log("options: {}".format(options))
    setup_environment(job, options)
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
    input_files = ['systemFile', 'tpr', 'gro']
    for f in input_files:
        job.log("key: {} value: {}".format(f, getattr(options, f)))

    fileID = job.fileStore.writeGlobalFile(getattr(options, 'systemFile'))
    job.log("fileID: {}".format(fileID))
    # return {key: job.fileStore.writeGlobalFile(options[key]) for key in input_files}


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
