from ..results import (Options, Results)
from .workflow_components import (
    call_xtp_cmd, create_promise_command,
    edit_jobs_file, edit_options, rename_map_file, run_parallel_jobs,
    split_eqm_calculations, split_iqm_calculations, split_xqmultipole_calculations,
    wait_till_done)
from ..xml_editor import edit_xml_file
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


def edit_calculator_options(options: Options, sections: list) -> dict:
    """
    Edit the options of a calculator using the values provided by the user
    """
    return edit_options(
        options.votca_calculators_options, sections, options.path_optionfiles)


def edit_system_options(results: Results, options: Options) -> dict:
    """
    Adjust the links inside the system.xml file.
    """
    mp_files = to_posix(options.mp_files.absolute())
    system_options = {
        'system': {
            'molecules': {"replace_regex_recursively":
                          ('MP_FILES', mp_files)}}
    }

    return edit_options(
        system_options, ['system'], options.scratch_dir)


def run_analyze(results: Results, options: Options, analyze: str) -> Dict:
    """
    call eanalyze tool.
    """
    if analyze == 'eanalyze':
        wait_till_done(results['jobs_eqm'])
        expected_output = {
            'sitecorr': "eanalyze.sitecorr*out", 'sitehist': "eanalyze.sitehist*out"}
    else:
        wait_till_done(results['jobs_iqm'])
        expected_output = {
            'ispatial': "ianalyze.ispatial_*.out"
        }
    path_analyze = options.path_optionfiles / "{}.xml".format(analyze)
    cmd_eanalyze = create_promise_command(
        "xtp_run -e {} -o {} -f {}", analyze, path_analyze, results['job_state']['state'])

    return call_xtp_cmd(
        cmd_eanalyze, options.scratch_dir / analyze, expected_output=expected_output)


def run_config_xqmultipole(results: Results, options: Options) -> dict:
    """
    Config the optionfiles to run the xqmultipole jobs
    """
    results['job_opts_xqmultipole'] = edit_calculator_options(options, ['jobwriter', 'xqmultipole'])

    # command for jobwriter runner
    cmd_setup_xqmultipole = create_promise_command(
        "xtp_run -e jobwriter -o {} -f {} -s 0",
        results['job_opts_xqmultipole']['jobwriter'], results['job_state']['state'])

    # schedule command
    results['job_setup_xqmultipole'] = call_xtp_cmd(
        cmd_setup_xqmultipole, options.scratch_dir / "xqmultipole", expected_output={
            'mps_tab': 'jobwriter.mps.background.tab',
            'xqmultipole_jobs': 'jobwriter.mps.monomer.xml'})

    # change path of the MP_FILES
    mp_files = to_posix(options.mp_files.absolute())
    results['job_setup_xqmultipole']['mps_tab'] = rename_map_file(
        results['job_setup_xqmultipole']['mps_tab'], "MP_FILES", mp_files)

    # Run only the jobs specified by the user
    return edit_jobs_file(
        results['job_setup_xqmultipole']['xqmultipole_jobs'],
        options.xqmultipole_jobs)


def run_dftgwbse(results: Results, options: Options) -> dict:
    """
    Running dft + gwbse, output can be found in dftgwbse.log
    """
    logger.info("Running dft + gwbse, output can be found in dftgwbse.log")

    # Add molecule, basis, functional, etc. to the calculator options
    options.votca_calculators_options["dftgwbse"]["molecule"] = options.molecule
    options.votca_calculators_options["dftgwbse"]["mode"] = options.mode

    # edit calculators options
    opts = edit_calculator_options(options, ['dftgwbse', 'mbgft', 'xtpdft'])

    cmd_dftgwbse = create_promise_command(
        "xtp_tools -e dftgwbse -o {} > dftgwbse.log", opts['dftgwbse'])

    return call_xtp_cmd(
        cmd_dftgwbse, options.scratch_dir / "dft_gwbse", expected_output={})


def run_dump(results: Results, options: Options) -> dict:
    """
    output MD and QM mappings into extract.trajectory_md.pdb and extract.trajectory_qm.pdb files
    """
    cmd_dump = create_promise_command(
        "xtp_dump -e trajectory2pdb -f {}", results['job_state']['state'])

    return call_xtp_cmd(cmd_dump, options.scratch_dir / "dump", expected_output={
        'md_trajectory': 'extract.trajectory_md.pdb',
        'qm_trajectory': 'extract.trajectory_qm.pdb'})


def run_einternal(results: Results, options: Options) -> dict:
    """
    read in reorganisation energies stored in system.xml to state.sql
    """
    einternal_file = options.path_optionfiles / 'einternal.xml'
    cmd_einternal = create_promise_command(
        "xtp_run -e einternal -o {} -f {}", einternal_file, results['job_state']['state'])
    return call_xtp_cmd(
        cmd_einternal, options.scratch_dir,
        expected_output={'einternal': einternal_file})


def run_eqm(results: Results, options: Options) -> dict:
    """
    Run the eqm jobs.
    """
    # set user-defined values
    results['job_opts_eqm'] = edit_calculator_options(
        options, ['eqm', 'xtpdft', 'mbgft', 'esp2multipole'])

    cmd_eqm_write = create_promise_command(
        "xtp_parallel -e eqm -o {} -f {} -s 0 -j write", results['job_opts_eqm']['eqm'],
        results['job_state']['state'])
    results['job_setup_eqm'] = call_xtp_cmd(
        cmd_eqm_write, options.scratch_dir,
        expected_output={"eqm_jobs": "eqm.jobs"})

    # Select the number of jobs to run based on the input provided by the user
    results['job_select_eqm_jobs'] = edit_jobs_file(
        results['job_setup_eqm']['eqm_jobs'],
        options.eqm_jobs)

    return distribute_eqm_jobs(results, options)


def run_gencube(results: Results, options: Options) -> dict:
    """
    Compute partial charges
    """
    opts = edit_calculator_options(options, ['gencube'])

    args = create_promise_command(
        "xtp_tools -e gencube -o {}", opts['gencube'])

    return call_xtp_cmd(args, options.scratch_dir / 'gencube', expected_output={})


def run_iqm(results: Results, options: Options) -> dict:
    """
    Run the eqm jobs.
    """
    # Copy option files
    src = ["mbgft.xml", "xtpdft.xml"]
    dst = ["mbgft_pair.xml", "xtpdft_pair.xml"]
    copy_option_files(options.path_optionfiles, src, dst)

    results['job_opts_iqm'] = edit_calculator_options(
        options, ['iqm', 'xtpdft_pair', 'mbgft_pair'])

    # replace optionfiles with its absolute path
    sections_to_edit = {
            '': {
                'replace_regex_recursively':
                ('OPTIONFILES', to_posix(options.path_optionfiles))}
        }

    edited_iqm_file = schedule(edit_xml_file)(
        results['job_opts_iqm']['iqm'], 'iqm', sections_to_edit)

    # write into state
    cmd_iqm_write = create_promise_command(
        "xtp_parallel -e iqm -o {} -f {} -s 0 -j write", edited_iqm_file,
        results['job_neighborlist']['state']
    )

    results['job_setup_iqm'] = call_xtp_cmd(
        cmd_iqm_write, options.scratch_dir / 'iqm', expected_output={
            'iqm_jobs': "iqm.jobs"}
    )

    # Select the number of jobs to run based on the input provided by the user
    results['job_select_iqm_jobs'] = edit_jobs_file(
        results['job_setup_iqm']['iqm_jobs'],
        options.iqm_jobs)

    return distribute_iqm_jobs(results, options)


def run_kmcmultiple(results: Results, options: Options) -> dict:
    """
    Run a kmcmultiple job
    """

    results['job_opts_kmcmultiple'] = edit_calculator_options(options, ['kmcmultiple'])

    args = create_promise_command(
        "xtp_run -e kmcmultiple -o {} -f {}", results['job_opts_kmcmultiple']['kmcmultiple'],
        options.state_file)

    return call_xtp_cmd(args, options.scratch_dir / "kmcmultiple", expected_output={
        "timedependence": "timedependence.csv",
        "trajectory": "trajectory.csv"
    })


def run_kmclifetime(results: Results, options: Options) -> dict:
    """
    Run a kmclifetime job
    """
    # Add dependency to kmcmultiple
    wait_till_done(results['job_kmcmultiple'])

    options.votca_calculators_options["kmclifetime"]["lifetimefile"] = options.lifetimes_file
    results['job_opts_kmclifetime'] = edit_calculator_options(options, ['kmclifetime'])

    args = create_promise_command(
        "xtp_run -e kmclifetime -o {} -f {}", results['job_opts_kmclifetime']['kmclifetime'],
        options.state_file)

    return call_xtp_cmd(args, options.scratch_dir / "kmclifetime", expected_output={
        "lifetimes": "*csv"})


def run_neighborlist(results: Results, options: Options) -> dict:
    """
    run neighborlist calculator
    """
    results['job_opts_neighborlist'] = edit_calculator_options(options, ['neighborlist'])

    cmd_neighborlist = create_promise_command(
        "xtp_run -e neighborlist -o {} -f {}",
        results['job_opts_neighborlist']['neighborlist'],
        results['job_state']['state'])

    return call_xtp_cmd(
        cmd_neighborlist, options.scratch_dir, expected_output={
            'neighborlist': "OPTIONFILES/neighborlist.xml",
            'state': 'state.sql'})


def run_partialcharges(results: Results, options: Options) -> dict:
    """
    Compute partial charges
    """
    opts = edit_calculator_options(options, ['esp2multipole', 'partialcharges'])

    logger.info("Running CHELPG fit")

    args = create_promise_command(
        "xtp_tools -e partialcharges -o {}", opts['partialcharges'])

    return call_xtp_cmd(args, options.scratch_dir / 'partialcharges', expected_output={})


def run_qmmm(results: Results, options: Options) -> dict:
    """
    QM/MM calculation
    """
    # results['job_opts_qmmm'] = edit_calculator_options(
    #     results, ['qmmm'])
    pass


def distribute_job(dict_input: dict, split_function: Callable) -> dict:
    """
    Using the jobs and parameters defined in `dict_input` create
    a set of independent jobs.
    """
    dict_jobs = split_function(lift(dict_input))
    return run_parallel_jobs(dict_jobs, lift(dict_input))


def distribute_xqmultipole_jobs(results: Results, options: Options) -> dict:
    """
    Run the xqmultipole_jobs independently
    """
    dict_input = {
        'name': 'xqmultipole',
        'scratch_dir': options.scratch_dir,
        'mp_files': options.mp_files,
        'xqmultipole_jobs': results['job_setup_xqmultipole']['xqmultipole_jobs'],
        'xqmultipole': results['job_opts_xqmultipole']['xqmultipole'],
        'system': results['job_system']['system'],
        'state': results['job_state']['state'],
        'mps_tab': results['job_setup_xqmultipole']['mps_tab'],
        'cmd_options': "-s 0 -t 1 -c 1000 -j run > xqmultipole.log",
        'expected_output': {'tab': 'job.tab'}

    }
    return distribute_job(dict_input, split_xqmultipole_calculations)


def distribute_eqm_jobs(results: Results, options: Options) -> dict:
    """
    Run the eqm job in separated folders
    """
    dict_input = {
        'name': 'eqm',
        'scratch_dir': options.scratch_dir,
        'eqm_jobs': results['job_setup_eqm']['eqm_jobs'],
        'state': results['job_state']['state'],
        'eqm': results['job_opts_eqm']['eqm'],
        'path_optionfiles': options.path_optionfiles,
        'cmd_options': "-s 0 -j run -c 1 -t 1",
        'expected_output': {
            'tab': 'job.tab', 'orb': 'system.orb'}
    }
    return distribute_job(dict_input, split_eqm_calculations)


def distribute_iqm_jobs(results: Results, options: Options) -> dict:
    """
    Run the iqm jobs independently
    """
    dict_input = {
        'name': 'iqm',
        'scratch_dir': options.scratch_dir,
        'iqm_jobs': results['job_setup_iqm']['iqm_jobs'],
        'state': results['job_neighborlist']['state'],
        'iqm': results['job_opts_iqm']['iqm'],
        'path_optionfiles': options.path_optionfiles,
        'cmd_options': "-s 0 -j run -c 1 -t 1",
        'expected_output': {
            'tab': 'job.tab'
        }
    }

    dict_read = dict_input.copy()
    dict_read['cmd_options'] = " -j read"
    dict_read['expected_output'] = None

    return distribute_job(dict_input, split_iqm_calculations)


def write_output(output: dict, options: Options, file_name: str = "results.yml") -> None:
    """
    Write the `output` dictionary in YAML format.
    """
    # Transform the options to a plain dictionary
    output['options'] = dict(options)
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


def initial_config(options: Options) -> Dict:
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
