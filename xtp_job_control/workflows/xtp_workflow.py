from .workflow_components import (
    call_xtp_cmd, create_promise_command,
    edit_jobs_file, edit_options, rename_map_file, run_parallel_jobs,
    split_eqm_calculations, split_iqm_calculations, split_xqmultipole_calculations)
from ..xml_editor import (edit_xml_file)
from distutils.dir_util import copy_tree
from pathlib import Path
from noodles import (lift, schedule)
from typing import (Callable, Dict)
import datetime
import logging
import os
import shutil
import tempfile
import yaml

# Starting logger
logger = logging.getLogger(__name__)


def recursively_create_path(dict_input):
    """
    Convert all the entries of the dict_input that are file into Path objects.
    """
    for key, val in dict_input.items():
        if isinstance(val, str):
            if os.path.isdir(val) or os.path.isfile(val):
                dict_input[key] = Path(val)
        if isinstance(val, dict):
            dict_input[key] = recursively_create_path(val)

    return dict_input


def edit_calculator_options(results: dict, sections: list) -> dict:
    """
    Edit the options of a calculator using the values provided by the user
    """
    options = results['options']
    path_optionfiles = options['path_optionfiles']
    votca_calculators_options = options['votca_calculators_options']

    return edit_options(
        votca_calculators_options, sections, path_optionfiles)


def edit_system_options(results: dict) -> dict:
    """
    Adjust the links inside the system.xml file.
    """
    mp_files = to_posix(results['options']['mp_files'].absolute())
    system_options = {
        'system': {
            'molecules': {"replace_regex_recursively":
                          ('MP_FILES', mp_files)}}
    }

    return edit_options(
        system_options, ['system'], results['options']['scratch_dir'])


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
    results['job_opts_neighborlist'] = edit_calculator_options(
        results, ['neighborlist'])

    cmd_neighborlist = create_promise_command(
        "xtp_run -e neighborlist -o {} -f {}",
        results['job_opts_neighborlist']['neighborlist'],
        results['job_state']['state'])

    return call_xtp_cmd(
        cmd_neighborlist, results['options']['scratch_dir'], expected_output={
            'neighborlist': "OPTIONFILES/neighborlist.xml",
            'state': 'state.sql'})


def run_analyze(results: dict, analyze_file: Path) -> Dict:
    """
    call eanalyze tool.
    """
    workdir = results['options']['scratch_dir']
    cmd_eanalyze = create_promise_command(
        "xtp_run -e eanalyze -o {} -f {}", analyze_file, results['job_state']['state'])
    return call_xtp_cmd(cmd_eanalyze, workdir / 'eanalyze', expected_output={
        'sitecorr': "eanalyze.sitecorr*out",
        'sitehist': "eanalyze.sitehist*out"})


def run_eqm(results: dict) -> dict:
    """
    Run the eqm jobs.
    """
    # set user-defined values
    results['job_opts_eqm'] = edit_calculator_options(
        results, ['eqm', 'xtpdft', 'mbgft', 'esp2multipole'])

    cmd_eqm_write = create_promise_command(
        "xtp_parallel -e eqm -o {} -f {} -s 0 -j write", results['job_opts_eqm']['eqm'],
        results['job_state']['state'])
    results['job_setup_eqm'] = call_xtp_cmd(
        cmd_eqm_write, results['options']['scratch_dir'],
        expected_output={"eqm_jobs": "eqm.jobs"})

    # Select the number of jobs to run based on the input provided by the user
    results['job_select_eqm_jobs'] = edit_jobs_file(
        results['job_setup_eqm']['eqm_jobs'],
        results['options']['eqm_jobs'])

    return distribute_eqm_jobs(results)


def run_iqm(results: dict) -> dict:
    """
    Run the eqm jobs.
    """
    # Copy option files
    optionfiles = results['options']['path_optionfiles']
    src = ["mbgft.xml", "xtpdft.xml"]
    dst = ["mbgft_pair.xml", "xtpdft_pair.xml"]
    copy_option_files(optionfiles, src, dst)

    results['job_opts_iqm'] = edit_calculator_options(
        results, ['iqm', 'xtpdft_pair', 'mbgft_pair'])

    # replace optionfiles with its absolute path
    path_optionfiles = results['options']['path_optionfiles']
    sections_to_edit = {
            '': {
                'replace_regex_recursively':
                ('OPTIONFILES', to_posix(path_optionfiles))}
        }

    edited_iqm_file = schedule(edit_xml_file)(
        results['job_opts_iqm']['iqm'], 'iqm', sections_to_edit)

    # write into state
    cmd_iqm_write = create_promise_command(
        "xtp_parallel -e iqm -o {} -f {} -s 0 -j write", edited_iqm_file,
        results['job_neighborlist']['state']
    )

    results['job_setup_iqm'] = call_xtp_cmd(
        cmd_iqm_write, results['options']['scratch_dir'] / 'iqm', expected_output={
            'iqm_jobs': "iqm.jobs"}
    )

    # Select the number of jobs to run based on the input provided by the user
    results['job_select_iqm_jobs'] = edit_jobs_file(
        results['job_setup_iqm']['iqm_jobs'],
        results['options']['iqm_jobs'])

    return distribute_iqm_jobs(results)


def run_qmmm(results: dict) -> dict:
    """
    QM/MM calculation
    """
    # results['job_opts_qmmm'] = edit_calculator_options(
    #     results, ['qmmm'])
    pass


def run_config_xqmultipole(results: dict) -> dict:
    """
    Config the optionfiles to run the xqmultipole jobs
    """
    results['job_opts_xqmultipole'] = edit_calculator_options(
        results, ['jobwriter', 'xqmultipole'])

    workdir = results['options']['scratch_dir']

    cmd_setup_xqmultipole = create_promise_command(
        "xtp_run -e jobwriter -o {} -f {} -s 0",
        results['job_opts_xqmultipole']['jobwriter'], results['job_state']['state'])

    results['job_setup_xqmultipole'] = call_xtp_cmd(
        cmd_setup_xqmultipole, workdir / "xqmultipole", expected_output={
            'mps_tab': 'jobwriter.mps.background.tab',
            'xqmultipole_jobs': 'jobwriter.mps.monomer.xml'})

    # change path of the MP_FILES
    mp_files = to_posix(results['options']['mp_files'].absolute())
    results['job_setup_xqmultipole']['mps_tab'] = rename_map_file(
        results['job_setup_xqmultipole']['mps_tab'], "MP_FILES", mp_files)

    # Run only the jobs specified by the user
    return edit_jobs_file(
        results['job_setup_xqmultipole']['xqmultipole_jobs'],
        results['options']['xqmultipole_jobs'])


def distribute_job(dict_input: dict, split_function: Callable) -> dict:
    """
    Using the jobs and parameters defined in `dict_input` create
    a set of independent jobs.
    """
    dict_jobs = split_function(lift(dict_input))
    return run_parallel_jobs(dict_jobs, lift(dict_input))


def distribute_xqmultipole_jobs(results: dict) -> dict:
    """
    Run the xqmultipole_jobs independently
    """
    dict_input = {
        'name': 'xqmultipole',
        'scratch_dir': results['options']['scratch_dir'],
        'mp_files': results['options']['mp_files'],
        'xqmultipole_jobs': results['job_setup_xqmultipole']['xqmultipole_jobs'],
        'xqmultipole': results['job_opts_xqmultipole']['xqmultipole'],
        'system': results['job_system']['system'],
        'state': results['job_state']['state'],
        'mps_tab': results['job_setup_xqmultipole']['mps_tab'],
        'cmd_options': "-s 0 -t 1 -c 1000 -j run > xqmultipole.log",
        'expected_output': {'tab': 'job.tab'}

    }
    return distribute_job(dict_input, split_xqmultipole_calculations)


def distribute_eqm_jobs(results: dict) -> dict:
    """
    Run the eqm job in separated folders
    """
    dict_input = {
        'name': 'eqm',
        'scratch_dir': results['options']['scratch_dir'],
        'eqm_jobs': results['job_setup_eqm']['eqm_jobs'],
        'state': results['job_state']['state'],
        'eqm': results['job_opts_eqm']['eqm'],
        'path_optionfiles': results['options']['path_optionfiles'],
        'cmd_options': "-s 0 -j run -c 1 -t 1",
        'expected_output': {
            'tab': 'job.tab', 'orb': 'system.orb'}
    }
    return distribute_job(dict_input, split_eqm_calculations)


def distribute_iqm_jobs(results: dict) -> dict:
    """
    Run the iqm jobs independently
    """
    dict_input = {
        'name': 'iqm',
        'scratch_dir': results['options']['scratch_dir'],
        'iqm_jobs': results['job_setup_iqm']['iqm_jobs'],
        'state': results['job_neighborlist']['state'],
        'iqm': results['job_opts_iqm']['iqm'],
        'path_optionfiles': results['options']['path_optionfiles'],
        'cmd_options': "-s 0 -j run -c 1 -t 1",
        'expected_output': {
            'tab': 'job.tab'
        }
    }

    dict_read = dict_input.copy()
    dict_read['cmd_options'] = " -j read"
    dict_read['expected_output'] = None

    return distribute_job(dict_input, split_iqm_calculations)


def write_output(output: dict, file_name: str = "results.yml") -> None:
    """
    Write the `output` dictionary in YAML format.
    """
    with open(file_name, 'w') as f:
        yaml.dump(to_posix(output), f, default_flow_style=False)


def copy_option_files(optionfiles, src, dst):
    for s, d in zip(src, dst):
        shutil.copyfile(
            to_posix(optionfiles / s),
            to_posix(optionfiles / d))


def to_posix(d):
    """
    convert the Path objects to string
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
    scratch_dir = tempfile.gettempdir() / Path('xtp_' + str(ts))
    scratch_dir.mkdir()

    # Option files
    optionfiles = scratch_dir / 'OPTIONFILES'
    optionfiles.mkdir()
    posix_optionfiles = to_posix(optionfiles)

    # Copy option files to temp file
    path_votcashare = options['path_votcashare']
    copy_tree(path_votcashare / 'xtp/xml', posix_optionfiles)
    shutil.copy(path_votcashare / 'ctp/xml/xqmultipole.xml', posix_optionfiles)
    copy_tree(path_votcashare / 'xtp/packages', posix_optionfiles)

    # Copy input provided by the user to tempfolder
    d = options.copy()
    for key, path in d.items():
        if isinstance(path, Path) and 'votca' not in path.name.lower():
            abs_path = scratch_dir / path.name
            if path.is_file():
                shutil.copy(to_posix(path), scratch_dir)
                options[key] = abs_path
            elif path.is_dir() and not abs_path.exists():
                shutil.copytree(to_posix(path), to_posix(abs_path))
                options[key] = abs_path

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