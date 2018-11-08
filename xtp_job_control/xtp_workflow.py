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
import yaml

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

    # Step state
    # runs the mapping from MD coordinates to segments and creates .sql file
    # you can explore the created .sql file with e.g. sqlitebrowser
    path_state = workdir / "state.sql"
    args = create_promise_command(
        "xtp_map -t {} -c {} -s {} -f {}",
        options['topology'], options['trajectory'], options['system'], path_state)

    # calls something like:
    # xtp_map -t MD_FILES/topol.tpr -c MD_FILES/conf.gro -s system.xml -f state.sql
    results['job_state'] = call_xtp_cmd(args, workdir, expected_output={'state': 'state.sql'})

    # step dump
    # output MD and QM mappings into extract.trajectory_md.pdb and
    # extract.trajectory_qm.pdb files
    results['job_dump'] = run_dump(results)

    # step neighborlist
    # Change options neighborlist
    results['job_opts_neighborlist'] = edit_options(
        changeoptions, ['neighborlist'], path_optionfiles)
    results['job_neighborlist'] = run_neighborlist(results)

    # # step einternal
    # read in reorganization energies stored in system.xml to state.sql
    results['job_einternal'] = run_einternal(results)

    # step config xqmultipole
    # setup jobfile xqmultipole
    results['job_opts_xq'] = edit_options(changeoptions, ['jobwriter'], path_optionfiles)
    results = run_config_xqmultipole(results)

    # step  run xqmultipole
    # Run the xqmultipole jobs
    results['job_xqmultipole_opts'] = edit_options(
        changeoptions, ['xqmultipole'], path_optionfiles)

    # Run xqmultipole jobs in parallel
    results['jobs_xqmultipole'] = distribute_xqmultipole_jobs(options, results)

    # step eanalyze
    # #running eanalyze
    results['job_eanalyze'] = run_eanalyze(results)

    # step eqm
    # Run eqm
    results = edit_eqm_options(results)
    results = run_eqm(results)

    # # step 11
    # # Run iqm

    # RUN the workflow
    output = run(gather_dict(**results.state))
    write_output(output)

    print("check output file: results.yml")


def run_einternal(results: dict) -> dict:
    """
    read in reorganisation energies stored in system.xml to state.sql
    """
    einternal_file = results['options']['path_optionfiles'] / 'einternal.xml'
    cmd_einternal = create_promise_command(
        "xtp_run -e einternal -o {} -f {}", einternal_file, results['job_state']['state'])
    return call_xtp_cmd(
        cmd_einternal, results['options']['scratch_dir'],
        expected_output={'einternal': einternal_file})


def run_dump(results: dict) -> dict:
    """
    output MD and QM mappings into extract.trajectory_md.pdb and extract.trajectory_qm.pdb files
    """
    cmd_dump = create_promise_command(
        "xtp_dump -e trajectory2pdb -f {}", results['job_state']['state'])

    workdir = results['options']['scratch_dir']
    return call_xtp_cmd(cmd_dump, workdir / "dump", expected_output={
        'md_trajectory': 'extract.trajectory_md.pdb',
        'qm_trajectory': 'extract.trajectory_qm.pdb'})


def run_neighborlist(results: dict) -> dict:
    """
    run neighborlist calculator
    """
    cmd_neighborlist = create_promise_command(
        "xtp_run -e neighborlist -o {} -f {}",
        results['job_opts_neighborlist']['neighborlist'], results['job_state']['state'])

    return call_xtp_cmd(
        cmd_neighborlist, results['options']['scratch_dir'], expected_output={
            'neighborlist': "OPTIONFILES/neighborlist.xml"})


def run_eanalyze(results: dict) -> Dict:
    """
    
    """
    workdir = results['options']['scratch_dir']
    eanalyze_file = results['options']['path_optionfiles'] / "eanalyze.xml"
    cmd_eanalyze = create_promise_command(
        "xtp_run -e eanalyze -o {} -f {}", eanalyze_file, results['job_state']['state'])
    return call_xtp_cmd(cmd_eanalyze, workdir / 'eanalyze', expected_output={
        'sitecorr': "eanalyze.sitecorr*out",
        'sitehist': "eanalyze.sitehist*out"})


def edit_eqm_options(results: dict) -> Dict:
    """
    Edit the eqm options files using the arguments specified in `changeoptions` and the
    files located at `path_optionfiles`.
    """
    changeoptions = results['options']['changeoptions']
    path_optionfiles = results['options']['path_optionfiles']
    results['job_opts_eqm'] = edit_options(changeoptions, ['eqm'], path_optionfiles)
    results['job_opts_xtpdft'] = edit_options(changeoptions, ['xtpdft'], path_optionfiles)
    results['job_opts_mbgft'] = edit_options(changeoptions, ['mbgft'], path_optionfiles)
    results['job_opts_esp2multipole'] = edit_options(
        changeoptions, ['esp2multipole'], path_optionfiles)

    return results


def run_eqm(results: dict) -> dict:
    """
    Run the eqm jobs.
    """
    cmd_eqm = create_promise_command(
        "xtp_parallel -e eqm -o {} -f {} -s 0 -j write", results['job_opts_eqm']['eqm'],
        results['job_state']['state'])
    results['job_set_eqm'] = call_xtp_cmd(
        cmd_eqm, results['options']['scratch_dir'],
        expected_output={"eqm": "eqm.jobs"})

    return results


def run_config_xqmultipole(results: dict) -> dict:
    """
    Config the optionfiles to run the xqmultipole jobs
    """
    workdir = results['options']['scratch_dir']

    cmd_setup_xqmultipole = create_promise_command(
        "xtp_run -e jobwriter -o {} -f {} -s 0",
        results['job_opts_xq']['jobwriter'], results['job_state']['state'])

    results['job_setup_xqmultipole'] = call_xtp_cmd(
        cmd_setup_xqmultipole, workdir / "xqmultipole", expected_output={
            'mps_tab': 'jobwriter.mps.background.tab',
            'xqmultipole_jobs': 'jobwriter.mps.monomer.xml'})

    # step 6
    # Allow only the first 3 jobs to run
    results['job_select_jobs'] = edit_jobs_file(
        results['job_setup_xqmultipole']['xqmultipole_jobs'],
        results['options']['xqmultipole_jobs'])

    return results


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
    cmd = """xtp_parallel -e xqmultipole -f {} -o {} -s 0 -t 1 -c 1000 -j run > xqmultipole.log"""

    return run_parallel_jobs(cmd, dict_jobs, lift(split_input))


def distribute_eqm_jobs(results: dict) -> dict:
    """
    Run the eqm job in separated folders
    """
    pass
    # dict_jobs = split_jobs()


def write_output(output: dict, file_name: str="results.yml") -> None:
    """
    """
    with open(file_name, 'w') as f:
        yaml.dump(to_posix(output), f, default_flow_style=False)


def to_posix(d):
    """
    convert the Path object to string
    """
    if isinstance(d, dict):
        for k, v in d.items():
            d[k] = to_posix(v)
    elif isinstance(d, list):
        return [to_posix(x) for x in d]

    elif isinstance(d, Path):
        return d.as_posix()

    return d


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
    copy_tree(path_votcashare / 'xtp/packages', optionfiles.as_posix())

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
