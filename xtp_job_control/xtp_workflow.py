from .runner import run
from .input import validate_input
from .worflow_components import (
    Results, call_xtp_cmd, create_promise_command,
    edit_jobs_file, edit_options, run_parallel_jobs, split_xqmultipole_calculations)
from distutils.dir_util import copy_tree
from pathlib import Path
from noodles import (gather_dict, lift)
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
    results = Results({'options': options.copy()})

    # Step1
    # runs the mapping from MD coordinates to segments and creates .sql file
    # you can explore the created .sql file with e.g. sqlitebrowser
    path_state = workdir / "state.sql"
    args = "xtp_map -t {} -c {} -s {} -f {}".format(
        options['topology'], options['trajectory'], options['system'], path_state)

    # calls something like:
    # xtp_map -t MD_FILES/topol.tpr -c MD_FILES/conf.gro -s system.xml -f state.sql
    results['job_state'] = call_xtp_cmd(args, workdir, expected_output={'state': 'state.sql'})

    # step2
    # output MD and QM mappings into extract.trajectory_md.pdb and
    # extract.trajectory_qm.pdb files
    cmd_dump = create_promise_command(
        "xtp_dump -e trajectory2pdb -f {}", results['job_state']['state'])

    results['job_dump'] = call_xtp_cmd(cmd_dump, workdir, expected_output={
        'md_trajectory': 'extract.trajectory_md.pdb',
        'qm_trajectory': 'extract.trajectory_qm.pdb'})

    # step3
    # Change options neighborlist
    results['job_opts_neighborlist'] = edit_options(
        changeoptions, ['neighborlist'], path_optionfiles)

    cmd_neighborlist = create_promise_command(
        "xtp_run -e neighborlist -o {} -f {}",
        results['job_opts_neighborlist']['neighborlist'], results['job_state']['state'])

    results['job_neighborlist'] = call_xtp_cmd(
        cmd_neighborlist, workdir, expected_output={
            'neighborlist': "OPTIONFILES/neighborlist.xml"})

    # # step 4
    # read in reorganization energies stored in system.xml to state.sql
    einternal_file = path_optionfiles / 'einternal.xml'
    cmd_einternal = create_promise_command(
        "xtp_run -e einternal -o {} -f {}", results['job_state']['state'], einternal_file)
    results['job_einternal'] = call_xtp_cmd(cmd_einternal, workdir, expected_output={
        'einternal': einternal_file})

    # step 5
    # setup jobfile xqmultipole
    results['job_opts_xq'] = edit_options(changeoptions, ['jobwriter'], path_optionfiles)

    cmd_setup_xqmultipole = create_promise_command(
        "xtp_run -e jobwriter -o {} -f {} -s 0",
        results['job_opts_xq']['jobwriter'], results['job_state']['state'])

    results['job_setup_xqmultipole'] = call_xtp_cmd(
        cmd_setup_xqmultipole, workdir, expected_output={
            'mps_tab': 'jobwriter.mps.background.tab',
            'xqmultipole_jobs': 'jobwriter.mps.monomer.xml'})

    # step 6
    # Allow only the first 3 jobs to run
    results['job_select_jobs'] = edit_jobs_file(
        results['job_setup_xqmultipole']['xqmultipole_jobs'], options['xqmultipole_jobs'])

    # step 7
    # Run the xqmultipole jobs
    results['job_xqmultipole_opts'] = edit_options(
        changeoptions, ['xqmultipole'], path_optionfiles)

    # step 8
    # Split jobs into independent calculations
    results['jobs_xqmultipole'] = distribute_xqmultipole_jobs(options, results)

    # step 9
    # #running eanalyze
    eanalyze_file = path_optionfiles / "eanalyze.xml"
    cmd_eanalyze = create_promise_command(
        "xtp_run -e eanalyze -o {} -f {}", eanalyze_file, results['job_state']['state'])
    results['job_eanalyze'] = call_xtp_cmd(cmd_eanalyze, workdir / 'eanalyze', expected_output={
        'sitecorr': "eanalyze.sitecorr*out",
        'sitehist': "eanalyze.sitehist*out"
    })

    # step 10
    # Run eqm


    # RUN the workflow
    output = run(gather_dict(**results.state))

    print(output)


def distribute_xqmultipole_jobs(options: dict, results: dict) -> dict:
    """
    Run the xqmultipole_jobs in separated folders
    """
    split_input = {
        'scratch_dir': options['scratch_dir'],
        'mp_files': options['mp_files'],
        'xqmultipole_jobs': results['job_setup_xqmultipole']['xqmultipole_jobs'],
        'xqmultipole': results['job_xqmultipole_opts']['xqmultipole'],
        'system': options['system'],
        'state': results['job_state']['state'],
        'mps_tab': results['job_setup_xqmultipole']['mps_tab']

    }
    dict_jobs = split_xqmultipole_calculations(lift(split_input))

    return run_parallel_jobs(lift(split_input), dict_jobs)


def initial_config(options: Dict) -> Dict:
    """
    setup to call xtp tools.
    """
    config_logger(options['workdir'])
    ts = datetime.datetime.now().timestamp()
    prefix = 'xtp_' + str(ts)
    scratch_dir = Path(tempfile.mkdtemp(prefix=prefix))

    # Option files
    optionfiles = scratch_dir / 'OPTIONFILES'
    optionfiles.mkdir()

    # Copy option files to temp file
    path_votcashare = Path(options['path_votcashare'])
    copy_tree(path_votcashare / 'xtp/xml', optionfiles.as_posix())
    shutil.copy(path_votcashare / 'ctp/xml/xqmultipole.xml', optionfiles)

    # Copy input provided by the user to tempfolder
    d = options.copy()
    for key, val in d.items():
        if isinstance(val, str) and os.path.isfile(val):
            shutil.copy(val, scratch_dir)
            options[key] = scratch_dir / Path(val).name

    dict_config = {
        'scratch_dir': scratch_dir, 'path_optionfiles': optionfiles}
    options.update(dict_config)

    return options


def config_logger(workdir: str):
    """
    Setup the logging infrasctucture.
    """
    file_log = os.path.join(workdir, 'xtp.log')
    logging.basicConfig(filename=file_log, level=logging.DEBUG,
                        format='%(asctime)s---%(levelname)s\n%(message)s\n',
                        datefmt='[%I:%M:%S]')
    logging.getLogger("noodles").setLevel(logging.WARNING)
    handler = logging.StreamHandler()
    handler.terminator = ""
