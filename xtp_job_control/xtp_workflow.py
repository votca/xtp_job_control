from .runner import run
from .input import validate_input
from .worflow_components import (
    Results, as_posix, call_xtp_cmd, create_promise_command,
    edit_jobs_file, edit_options, rename_map_file, run_parallel_jobs,
    split_eqm_calculations, split_iqm_calculations, split_xqmultipole_calculations)
from .xml_editor import (edit_xml_file)
from distutils.dir_util import copy_tree
from pathlib import Path
from noodles import (gather_dict, lift, schedule)
from typing import (Callable, Dict)
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
    input_dict = recursively_create_path(validate_input(options['input_file']))

    # Merge inputs
    options.update(input_dict)

    # Setup environment to run xtp
    options = initial_config(options)

    # Create graph of dependencies
    create_workflow_simulation(options)


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


def create_workflow_simulation(options: Dict) -> object:
    """
    Use the `options` to create a workflow
    """
    workdir = options['scratch_dir']
    path_optionfiles = options['path_optionfiles']
    change_options = options['change_options']

    # create results object
    results = Results({'options': options.copy()})

    # Adjust links in the system.xml file
    results['job_system'] = edit_system_options(results)

    # Step state
    # runs the mapping from MD coordinates to segments and creates .sql file
    # you can explore the created .sql file with e.g. sqlitebrowser
    path_state = workdir / "state.sql"
    args = create_promise_command(
        "xtp_map -t {} -c {} -s {} -f {}",
        options['topology'], options['trajectory'],
        results['job_system']['system'], path_state)

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
        change_options, ['neighborlist'], path_optionfiles)
    results['job_neighborlist'] = run_neighborlist(results)

    # # step einternal
    # read in reorganization energies stored in system.xml to state.sql
    results['job_einternal'] = run_einternal(results)

    # step config xqmultipole
    results['job_opts_xqmultipole'] = edit_options(
        change_options, ['jobwriter', 'xqmultipole'], path_optionfiles)
    results['job_select_xqmultipole_jobs'] = run_config_xqmultipole(results)

    # Run xqmultipole jobs in parallel
    results['jobs_xqmultipole'] = distribute_xqmultipole_jobs(results)

    # step eanalyze
    eanalyze_file = path_optionfiles / "eanalyze.xml"
    results['job_eanalyze'] = run_analyze(results, eanalyze_file)

    # step eqm
    results['job_opts_eqm'] = edit_options(
        change_options, ['eqm', 'xtpdft', 'mbgft', 'esp2multipole'], path_optionfiles)
    results['jobs_eqm'] = run_eqm(results)

    # step iqm
    results['job_opts_iqm'] = edit_options(
        change_options, ['iqm', 'xtpdft_pair', 'mbgft_pair'], path_optionfiles)
    results['jobs_iqm'] = run_iqm(results)

    # step ianalyze
    ianalyze_file = path_optionfiles / "ianalyze.xml"
    results['job_ianalyze'] = run_analyze(results, ianalyze_file)

    # RUN the workflow
    output = run(gather_dict(**results.state))
    write_output(output)

    print("check output file: results.yml")


def edit_system_options(results: dict) -> dict:
    """
    Adjust the links inside the system.xml file.
    """
    mp_files = results['options']['mp_files'].absolute().as_posix()
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
    # replace optionfiles with its absolute path
    path_optionfiles = results['options']['path_optionfiles']
    sections_to_edit = {
            '': {
                'replace_regex_recursively':
                ('OPTIONFILES', as_posix(path_optionfiles))}
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


def run_config_xqmultipole(results: dict) -> dict:
    """
    Config the optionfiles to run the xqmultipole jobs
    """
    workdir = results['options']['scratch_dir']

    cmd_setup_xqmultipole = create_promise_command(
        "xtp_run -e jobwriter -o {} -f {} -s 0",
        results['job_opts_xqmultipole']['jobwriter'], results['job_state']['state'])

    results['job_setup_xqmultipole'] = call_xtp_cmd(
        cmd_setup_xqmultipole, workdir / "xqmultipole", expected_output={
            'mps_tab': 'jobwriter.mps.background.tab',
            'xqmultipole_jobs': 'jobwriter.mps.monomer.xml'})

    # change path of the MP_FILES
    mp_files = results['options']['mp_files'].absolute().as_posix()
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


def write_output(output: dict, file_name: str="results.yml") -> None:
    """
    Write the `output` dictionary in YAML format.
    """
    with open(file_name, 'w') as f:
        yaml.dump(to_posix(output), f, default_flow_style=False)


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
    posix_optionfiles = str(optionfiles.as_posix())

    # Copy option files to temp file
    path_votcashare = options['path_votcashare']
    copy_tree(path_votcashare / 'xtp/xml', posix_optionfiles)
    shutil.copy(path_votcashare / 'ctp/xml/xqmultipole.xml', posix_optionfiles)
    copy_tree(path_votcashare / 'xtp/packages', posix_optionfiles)

    if 'copy_option_files' in options:
        src = options['copy_option_files']['src']
        dst = options['copy_option_files']['dst']
        for s, d in zip(src, dst):
            shutil.copyfile(
                as_posix(optionfiles / s),
                as_posix(optionfiles / d))

    # Copy input provided by the user to tempfolder
    d = options.copy()
    for key, path in d.items():
        if isinstance(path, Path) and 'votca' not in path.name.lower():
            abs_path = scratch_dir / path.name
            if path.is_file():
                shutil.copy(path.as_posix(), scratch_dir)
                options[key] = abs_path
            elif path.is_dir() and not abs_path.exists():
                shutil.copytree(path.as_posix(), abs_path.as_posix())
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
