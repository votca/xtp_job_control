from ..results import (Options, Results)
from .workflow_components import (
    call_xtp_cmd, create_promise_command,
    edit_jobs_file, edit_options, move_results_to_workdir,
    rename_map_file, run_parallel_jobs, split_eqm_calculations, split_iqm_calculations,
    split_qmmm_calculations, split_xqmultipole_calculations)
from ..xml_editor import edit_xml_file
from distutils.dir_util import copy_tree
from pathlib import Path
from noodles import (lift, schedule)
from noodles.interface import PromisedObject
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
    Add options provided by the user to the respective calculator configuration.
    """
    mp_files = to_posix(options.mp_files.absolute())
    system_options = {
        'system': {
            'molecules': {"replace_regex_recursively":
                          ('MP_FILES', mp_files)}}
    }

    return edit_options(
        system_options, ['system'], options.scratch_dir)


def run_eanalyze(results: Results, options: Options, state: PromisedObject) -> Dict:
    """
    call eanalyze tool.
    """
    expected_output = {
        'sitecorr': "eanalyze.sitecorr*out", 'sitehist': "eanalyze.sitehist*out"}

    path_analyze = options.path_optionfiles / "eanalyze.xml"
    cmd_eanalyze = create_promise_command(
        "xtp_run -e eanalyze -o {} -f {}", path_analyze, state)

    return call_xtp_cmd(
        cmd_eanalyze, options.scratch_dir / 'eanalyze', expected_output=expected_output)


def run_ianalyze(results: Results, options: Options, state: PromisedObject) -> Dict:
    """
    call eanalyze tool.
    """
    expected_output = {
            'ispatial': "ianalyze.ispatial_*.out"}
    path_analyze = options.path_optionfiles / "ianalyze.xml"
    cmd_eanalyze = create_promise_command(
        "xtp_run -e ianalyze -o {} -f {}", path_analyze, state)

    return call_xtp_cmd(
        cmd_eanalyze, options.scratch_dir / 'ianalyze', expected_output=expected_output)


def run_dftgwbse(results: Results, options: Options) -> dict:
    """
    Running dft + gwbse, output can be found in dftgwbse.log
    """
    logger.info("Running dft + gwbse, output can be found in dftgwbse.log")

    # Add molecule, basis, functional, etc. to the calculator options
    options.votca_calculators_options["dftgwbse"]["molecule"] = options.molecule
    options.votca_calculators_options["dftgwbse"]["mode"] = options.mode

    # mbgft
    options.votca_calculators_options["mbgft"]["dftbasis"] = options.dftbasis
    options.votca_calculators_options["mbgft"]["gwbasis"] = options.gwbasis
    options.votca_calculators_options["mbgft"]["vxc"] = {"functional": options.functional}

    # edit calculators options
    opts = edit_calculator_options(options, ['dftgwbse', 'mbgft', 'xtpdft'])

    cmd_dftgwbse = create_promise_command(
        "xtp_tools -e dftgwbse -o {} > dftgwbse.log", opts['dftgwbse'])

    return call_xtp_cmd(
        cmd_dftgwbse, options.scratch_dir / "dft_gwbse", expected_output={
            "log": "dftgwbse.log", "out": "dftgwbse.out.xml",
            "system_dft": "system_dft.orb", "system": "system.orb"})


def run_dump(results: Results, options: Options, state: PromisedObject) -> dict:
    """
    output MD and QM mappings into extract.trajectory_md.pdb and extract.trajectory_qm.pdb files
    """
    cmd_dump = create_promise_command(
        "xtp_dump -e trajectory2pdb -f {}", state)

    return call_xtp_cmd(cmd_dump, options.scratch_dir / "dump", expected_output={
        'md_trajectory': 'extract.trajectory_md.pdb',
        'qm_trajectory': 'extract.trajectory_qm.pdb'})


def run_einternal(results: Results, options: Options, state: PromisedObject) -> dict:
    """
    read in reorganisation energies stored in system.xml to state.sql
    """
    einternal_file = options.path_optionfiles / 'einternal.xml'
    cmd_einternal = create_promise_command(
        "xtp_run -e einternal -o {} -f {}", einternal_file, state)
    return call_xtp_cmd(
        cmd_einternal, options.scratch_dir,
        expected_output={'einternal': einternal_file})


def run_eqm(results: Results, options: Options, state: PromisedObject) -> dict:
    """
    Run the eqm jobs.
    """
    # set user-defined values
    results['job_opts_eqm'] = edit_calculator_options(
        options, ['eqm', 'xtpdft', 'mbgft', 'esp2multipole'])

    cmd_eqm_write = create_promise_command(
        "xtp_parallel -e eqm -o {} -f {} -s 0 -j write", results['job_opts_eqm']['eqm'],
        state)
    results['job_setup_eqm'] = call_xtp_cmd(
        cmd_eqm_write, options.scratch_dir,
        expected_output={"eqm_jobs": "eqm.jobs"})

    # Select the number of jobs to run based on the input provided by the user
    results['job_select_eqm_jobs'] = edit_jobs_file(
        results['job_setup_eqm']['eqm_jobs'],
        options.eqm_jobs)

    jobs_eqm = distribute_eqm_jobs(results, options, state)

    # Finally move all the OR_FILES to the same folder in the scratch_dir
    names = ('molecule_orb', 'dft_orb', 'mps_file')

    return move_results_to_workdir(jobs_eqm, names, options.scratch_dir)


def run_gencube(results: Results, options: Options) -> dict:
    """
    Compute partial charges
    """
    opts = edit_calculator_options(options, ['gencube'])

    args = create_promise_command(
        "xtp_tools -e gencube -o {}", opts['gencube'])

    return call_xtp_cmd(args, options.scratch_dir / 'gencube', expected_output={})


def run_iqm(results: Results, options: Options, state: PromisedObject) -> dict:
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
        state)

    results['job_setup_iqm'] = call_xtp_cmd(
        cmd_iqm_write, options.scratch_dir / 'iqm', expected_output={
            'iqm_jobs': "iqm.jobs"}
    )

    # Select the number of jobs to run based on the input provided by the user
    results['job_select_iqm_jobs'] = edit_jobs_file(
        results['job_setup_iqm']['iqm_jobs'],
        options.iqm_jobs)

    return distribute_iqm_jobs(results, options, state)


def run_kmcmultiple(results: Results, options: Options, state) -> dict:
    """
    Run a kmcmultiple job
    """

    results['job_opts_kmcmultiple'] = edit_calculator_options(options, ['kmcmultiple'])

    args = create_promise_command(
        "xtp_run -e kmcmultiple -o {} -f {}", results['job_opts_kmcmultiple']['kmcmultiple'],
        state)

    return call_xtp_cmd(args, options.scratch_dir / "kmcmultiple", expected_output={
        "timedependence": "timedependence.csv",
        "trajectory": "trajectory.csv"
    })


def run_kmclifetime(results: Results, options: Options, state) -> dict:
    """
    Run a kmclifetime job
    """
    # Add dependency to kmcmultiple
    # wait_till_done(results['job_kmcmultiple'])

    options.votca_calculators_options["kmclifetime"]["lifetimefile"] = options.lifetimes_file
    results['job_opts_kmclifetime'] = edit_calculator_options(options, ['kmclifetime'])

    args = create_promise_command(
        "xtp_run -e kmclifetime -o {} -f {}", results['job_opts_kmclifetime']['kmclifetime'],
        state)

    return call_xtp_cmd(args, options.scratch_dir / "kmclifetime", expected_output={
        "lifetimes": "*csv"})


def run_neighborlist(results: Results, options: Options, state: PromisedObject) -> dict:
    """
    run neighborlist calculator
    """
    results['job_opts_neighborlist'] = edit_calculator_options(options, ['neighborlist'])

    cmd_neighborlist = create_promise_command(
        "xtp_run -e neighborlist -o {} -f {}",
        results['job_opts_neighborlist']['neighborlist'],
        state)

    return call_xtp_cmd(
        cmd_neighborlist, options.scratch_dir, expected_output={
            'neighborlist': "OPTIONFILES/neighborlist.xml",
            'state': 'state.sql'})


def run_partialcharges(results: Results, options: Options, promise: PromisedObject = None) -> dict:
    """
    Compute partial charges
    """
    opts = edit_calculator_options(options, ['esp2multipole', 'partialcharges'])

    if promise is not None:
        path_partialcharges = options.path_optionfiles / "partialcharges.xml"
        sections_to_edit = {"partialcharges": {"input": promise}}
        opts['partialcharges'] = schedule(edit_xml_file)(
             path_partialcharges, 'options', lift(sections_to_edit))

    logger.info("Running CHELPG fit")
    args = create_promise_command(
        "xtp_tools -e partialcharges -o {}", opts['partialcharges'])

    return call_xtp_cmd(args, options.scratch_dir / 'partialcharges', expected_output={})


def run_qmmm(results: Results, options: Options, state: PromisedObject) -> dict:
    """
    QM/MM calculation
    """
    # Copy option files
    src = ["mbgft.xml", "xtpdft.xml"]
    dst = ["mbgft_qmmm.xml", "xtpdft_qmmm.xml"]
    copy_option_files(options.path_optionfiles, src, dst)

    # Edit options files
    results['job_opts_qmmm'] = edit_calculator_options(
        options, ['qmmm', 'mbgft_qmmm', 'xtpdft_qmmm'])

    return distribute_qmmm_jobs(results, options, state)


def run_xqmultipole(results: Results, options: Options, state: PromisedObject) -> dict:
    """
    Config the optionfiles to run the xqmultipole jobs then run the xqmultipole job
    """
    results['job_opts_xqmultipole'] = edit_calculator_options(
        options, ['jobwriter', 'xqmultipole'])

    # command for jobwriter runner
    cmd_setup_xqmultipole = create_promise_command(
        "xtp_run -e jobwriter -o {} -f {} -s 0",
        results['job_opts_xqmultipole']['jobwriter'], state)

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
    results['job_select_xqmultipole_jobs'] = edit_jobs_file(
        results['job_setup_xqmultipole']['xqmultipole_jobs'],
        options.xqmultipole_jobs)

    return distribute_xqmultipole_jobs(results, options, state)


def distribute_job(dict_input: dict, split_function: Callable) -> dict:
    """
    Using the jobs and parameters defined in `dict_input` create
    a set of independent jobs.
    """
    dict_jobs = split_function(lift(dict_input))
    return run_parallel_jobs(dict_jobs, lift(dict_input))


def distribute_xqmultipole_jobs(results: Results, options: Options, state: PromisedObject) -> dict:
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
        'state': state,
        'mps_tab': results['job_setup_xqmultipole']['mps_tab'],
        'cmd_options': "-s 0 -t 1 -c 1000 -j run > xqmultipole.log",
        'expected_output': {'tab': 'job.tab'}

    }
    return distribute_job(dict_input, split_xqmultipole_calculations)


def distribute_eqm_jobs(results: Results, options: Options, state: PromisedObject) -> dict:
    """
    Run the eqm job in separated folders
    """
    dict_input = {
        'name': 'eqm',
        'scratch_dir': options.scratch_dir,
        'eqm_jobs': results['job_setup_eqm']['eqm_jobs'],
        'state': state,
        'eqm': results['job_opts_eqm']['eqm'],
        'path_optionfiles': options.path_optionfiles,
        'cmd_options': "-s 0 -j run -c 1 -t 1",
        'expected_output': {
            'tab': 'job.tab',
            'dft_orb': "OR_FILES/xtp_eqm/frame_0/molecule_*/*.orb",
            'molecule_orb': 'OR_FILES/molecules/frame_0/*.orb',
            'mps_file': 'MP_FILES/frame_0/*/*.mps'}
    }
    return distribute_job(dict_input, split_eqm_calculations)


def distribute_iqm_jobs(results: Results, options: Options, state: PromisedObject) -> dict:
    """
    Run the iqm jobs independently
    """
    dict_input = {
        'name': 'iqm',
        'scratch_dir': options.scratch_dir,
        'iqm_jobs': results['job_setup_iqm']['iqm_jobs'],
        'state': state,
        'iqm': results['job_opts_iqm']['iqm'],
        'jobs_eqm': results['jobs_eqm'],
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


def distribute_qmmm_jobs(results: Results, options: Options, state: PromisedObject) -> dict:
    """
    """
    dict_input = {
        'name': 'qmmm',
        'scratch_dir': options.scratch_dir,
        'qmmm_jobs': results['job_setup_qmmm']['qmmm_jobs'],
        'state': state,
        'qmmm': results['job_opts_qmmm']['qmmm'],
        'path_optionfiles': options.path_optionfiles,
        'cmd_options': ""
    }

    return distribute_job(dict_input, split_qmmm_calculations)


def write_output(output: dict, options: Options, file_name: str = "results") -> None:
    """
    Write the `output` dictionary in YAML format.
    """
    # Transform the options to a plain dictionary
    output['options'] = dict(options)
    file_name += "_" + output['options']['scratch_dir'].name + ".yml"
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
    ts = datetime.datetime.now().isoformat()
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
