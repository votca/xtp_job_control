from .runner import run
from .input import validate_input
from distutils.dir_util import copy_tree
from os.path import join
from typing import Dict
import datetime
import logging
import os
import tempfile

# Starting logger
logger = logging.getLogger(__name__)


def xtp_workflow(options: Dict):
    """
    Workflow to run a complete xtp ssimulation using `options`.
    """
    # validate_input
    input_dict = validate_input(options['input_file'])

    # Merge inputs
    options.update(input_dict)

    # Setup environment to run xtp
    options = initial_config(options)

    # Create graph of dependencies
    create_workflow_simulation(options)

    # return run(wf)


def create_workflow_simulation(options: Dict) -> object:
    """
    Use the `options` to create a workflow
    """
    change_options_files(options['changeoptions'], options['path_optionfiles'])


def change_options_files(changeoptions: Dict, path_optionfiles: str) -> None:
    """
    Change the temporal optionfiles with the input provided by the user.
    """
    

    
    # # Step1
    # # runs the mapping from MD coordinates to segments and creates .sql file
    # # you can explore the created .sql file with e.g. sqlitebrowser
    # state = "state.sql"
    # cmd_map = "xtp_map -t {} -c {} -s {} -f {}".format(
    #     options['tpr'], options['gro'], options['system'], state)

    # job_map = call_xtp_cmd(cmd_map, workdir, expected_output={'state': state})

    # # step2
    # # output MD and QM mappings into extract.trajectory_md.pdb and
    # # extract.trajectory_qm.pdb files

    # cmd_dump = create_promise_command(
    #     "xtp_dump -e trajectory2pdb -f {}", job_map, ['state'])

    # job_dump = call_xtp_cmd(cmd_dump, workdir, expected_output={
    #     'md_trajectory': 'extract.trajectory_md.pdb',
    #     'qm_trajectory': 'extract.trajectory_qm.pdb'})

    # # step3
    # # Change options
    
    # output = run(job_dump)
    # print(output)


def initial_config(options: Dict) -> Dict:
    """
    setup to call xtp tools.
    """
    config_logger(options['workdir'])
    ts = datetime.datetime.now().timestamp()
    prefix = 'xtp_' + str(ts)
    scratch_dir = tempfile.mkdtemp(prefix=prefix)

    # Option files
    optionfiles = join(scratch_dir, 'OPTIONFILES')
    os.mkdir(optionfiles)

    # Copy option files to temp file
    path_votcashare = options['path_votcashare']
    copy_tree(join(path_votcashare, 'xtp/xml'), optionfiles)

    dict_config = {
        'scratch_dir': scratch_dir, 'path_optionfiles': optionfiles}
    options.update(dict_config)

    return options


def config_logger(workdir: str):
    """
    Setup the logging infrasctucture.
    """
    file_log = join(workdir, 'xtp.log')
    logging.basicConfig(filename=file_log, level=logging.DEBUG,
                        format='%(levelname)s:%(message)s  %(asctime)s\n',
                        datefmt='%m/%d/%Y %I:%M:%S %p')
