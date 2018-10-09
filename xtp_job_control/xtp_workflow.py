from .runner import run
from noodles import schedule
from os.path import join
from subprocess import (PIPE, Popen)
from typing import (Dict, List)
import logging
import fnmatch
import os
import shutil
import tempfile


# Starting logger
logger = logging.getLogger(__name__)


def xtp_workflow(options: Dict):
    """
    Workflow to run a complete xtp ssimulation using `options`.
    """
    # Setup environment to run xtp
    options = initial_config(options)

    workdir = options['workdir']

    # Step1
    # runs the mapping from MD coordinates to segments and creates .sql file
    # you can explore the created .sql file with e.g. sqlitebrowser
    state = "state.sql"
    cmd_map = "xtp_map -t {} -c {} -s {} -f {}".format(
        options['tpr'], options['gro'], options['system'], state)

    job_map = call_xtp_cmd(cmd_map, workdir, expected_output={'state': state})

    # step2
    # output MD and QM mappings into extract.trajectory_md.pdb and
    # extract.trajectory_qm.pdb files

    cmd_dump = create_promise_command(
        "xtp_dump -e trajectory2pdb -f {}", job_map, ['state'])

    job_dump = call_xtp_cmd(cmd_dump, workdir, expected_output={
        'md_trajectory': 'extract.trajectory_md.pdb',
        'qm_trajectory': 'extract.trajectory_qm.pdb'})

    output = run(job_dump)
    print(output)


@schedule
def call_xtp_cmd(cmd: str, workdir: str, expected_output: List=None):
    """
    Run a bash `cmd` in the `cwd` folder and search for a list of `expected_output`
    files.
    """
    with Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True, cwd=workdir) as p:
        rs = p.communicate()

    logger.info("running command: {}".format(cmd))

    if expected_output is None:
        return None
    else:
        logger.info("command output: {}".format(rs[0]))
        logger.error("command error: {}".format(rs[1]))
        return {key: retrieve_ouput(workdir, file_name) for key, file_name
                in expected_output.items()}


@schedule
def create_promise_command(template: str, dict_files: Dict, identifiers: List) -> str:
    """
    Use a `template` together with the previous result `dict_files`
    to create a new command line str, using different file `identifiers`.
    """
    return template.format(*[dict_files[f] for f in identifiers])


def retrieve_ouput(workdir: str, expected_file: str) -> str:
    """
    Search for `expected_file` files in the `workdir`.
    """
    rs = fnmatch.filter(os.listdir(workdir), expected_file)
    if len(rs) == 0:
        msg = "the command failed producing no output files"
        raise RuntimeError(msg)
    else:
        return rs[0]


def initial_config(options: Dict) -> Dict:
    """
    setup to call xtp tools.
    """
    config_logger(options['workdir'])
    scratch_dir = tempfile.mkdtemp(prefix='xtp_')

    # Option files
    optionfiles = join(scratch_dir, 'OPTIONFILES')
    os.mkdir(optionfiles)
    neighborlist = create_neighborlist(options['votcashare'], optionfiles)

    # merge with user provided options
    dict_config = {
        'scratch_dir': scratch_dir, 'optionfiles': options, 'neighborlist': neighborlist}
    options.update(dict_config)

    return options


def create_neighborlist(votcashare_path: str, optionfiles: str) -> str:
    """
    create a list of neighbors anf return xml file
    """
    neighborlist = join(votcashare_path, 'xtp/xml/neighborlist.xml')
    shutil.copy(neighborlist, optionfiles)

    return neighborlist


def config_logger(workdir: str):
    """
    Setup the logging infrasctucture.
    """
    file_log = join(workdir, 'xtp.log')
    logging.basicConfig(filename=file_log, level=logging.DEBUG,
                        format='%(levelname)s:%(message)s  %(asctime)s\n',
                        datefmt='%m/%d/%Y %I:%M:%S %p')
