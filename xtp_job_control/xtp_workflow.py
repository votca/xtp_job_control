from .runner import run
from .input import validate_input
from .worflow_components import (
    call_xtp_cmd, create_promise_command, edit_jobs_file, edit_options,
    merge_promised_dict)
from distutils.dir_util import copy_tree
from noodles import gather
from os.path import join
from typing import Dict
import datetime
import logging
import os
import shutil
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


def create_workflow_simulation(options: Dict) -> object:
    """
    Use the `options` to create a workflow
    """
    workdir = options['scratch_dir']
    path_optionfiles = options['path_optionfiles']
    changeoptions = options['changeoptions']

    # create results object
    results = options.copy()
    path_state = join(workdir, "state.sql")

    # Step1
    # runs the mapping from MD coordinates to segments and creates .sql file
    # you can explore the created .sql file with e.g. sqlitebrowser
    results['state'] = path_state
    args = create_promise_command(
        "xtp_map -t {} -c {} -s {} -f {}", results, ['topology', 'trajectory', 'system', 'state'])

    # calls something like:
    # xtp_map -t MD_FILES/topol.tpr -c MD_FILES/conf.gro -s system.xml -f state.sql
    job_map = call_xtp_cmd(args, workdir, expected_output={'state': 'state.sql'})

    # step2
    # output MD and QM mappings into extract.trajectory_md.pdb and
    # extract.trajectory_qm.pdb files
    results = merge_promised_dict(results, job_map)
    cmd_dump = create_promise_command(
        "xtp_dump -e trajectory2pdb -f {}", results, ['state'])

    job_dump = call_xtp_cmd(cmd_dump, workdir, expected_output={
        'md_trajectory': 'extract.trajectory_md.pdb',
        'qm_trajectory': 'extract.trajectory_qm.pdb'})

    # step3
    # Change options neighborlist
    job_change_opts = edit_options(changeoptions, ['neighborlist'], path_optionfiles)
    results = merge_promised_dict(results, job_dump, job_change_opts)
    cmd_neighborlist = create_promise_command(
        "xtp_run -e neighborlist -o {} -f {}", results, ['neighborlist', 'state'])
    job_neighborlist = call_xtp_cmd(cmd_neighborlist, workdir)

    # step 4
    # read in reorganization energies stored in system.xml to state.sql
    einternal_file = join(path_optionfiles, 'einternal.xml')
    results = merge_promised_dict(results, {'einternal': einternal_file})
    cmd_einternal = create_promise_command(
        "xtp_run -e einternal -o {} -f {}", results, ['einternal', 'state'])
    job_einternal = call_xtp_cmd(cmd_einternal, workdir)

    # step 5
    # setup jobfile xqmultipole
    job_opts_xq = edit_options(changeoptions, ['jobwriter'], path_optionfiles)
    results = merge_promised_dict(results, job_opts_xq)
    cmd_setup_xqmultipole = create_promise_command(
        "xtp_run -e jobwriter -o {} -f {} -s 0", results, ['jobwriter', 'state'])
    job_setup_xqmultipole = call_xtp_cmd(
        cmd_setup_xqmultipole, workdir, expected_output={
            'mps.tab': 'jobwriter.mps.background.tab',
            'xqmultipole.jobs': 'jobwriter.mps.monomer.xml'})
    results = merge_promised_dict(results, job_setup_xqmultipole)

    # step 6
    # Allow only the first 3 jobs to run
    xqmultipole_jobs = options['xqmultipole_jobs']

    job_select_jobs = edit_jobs_file(results, 'xqmultipole.jobs', xqmultipole_jobs)
    results = merge_promised_dict(results, job_select_jobs)

    # step 7
    # Run the xqmultipole jobs
    job_change_opts = edit_options(changeoptions, ['xqmultipole'], path_optionfiles)

    # step 8
    # Split jobs into independent calculations
    # jobs_xqmultipole = split_xqmultipole_calculations(results)

    # RUN the workflow
    output = run(gather(
        job_map, job_dump, job_neighborlist, job_einternal, job_setup_xqmultipole,
        job_select_jobs))
    print(output)


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
    shutil.copy(join(path_votcashare, 'ctp/xml/xqmultipole.xml'), optionfiles)

    # Copy input provided by the user to tempfolder
    d = options.copy()
    for key, val in d.items():
        if isinstance(val, str) and os.path.isfile(val):
            shutil.copy(val, scratch_dir)
            options[key] = join(scratch_dir, os.path.basename(val))

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
