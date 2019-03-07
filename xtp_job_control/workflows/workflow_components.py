from ..xml_editor import (
    add_absolute_path_to_options, create_job_file, edit_xml_file,
    edit_xml_job_file, edit_xml_options, read_available_jobs)
from collections import defaultdict
from functools import wraps
from noodles import schedule
from noodles.interface import PromisedObject
from pathlib import Path
from subprocess import (PIPE, Popen)
from typing import (Callable, Dict, List)
import logging
import os
import re
import shutil

# Starting logger
logger = logging.getLogger(__name__)


@schedule
def call_xtp_cmd(
        cmd: str, workdir: str, expected_output: dict = None):
    """
    Run a bash `cmd` in the `workdir` folder and search for a list of `expected_output`
    files.
    """
    if not workdir.exists():
        workdir.mkdir()
    return run_command(cmd, workdir, expected_output)


def run_command(cmd: str, workdir: str, expected_output: dict = None):
    """
    Run a bash command using subprocess
    """
    with Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True, cwd=workdir.as_posix()) as p:
        rs = p.communicate()

    logger.info("RUNNING COMMAND: {}".format(cmd))
    logger.info("COMMAND OUTPUT: {}".format(rs[0].decode()))
    logger.error("COMMAND ERROR: {}".format(rs[1].decode()))

    if expected_output is None:
        return None
    else:
        return {key: retrieve_ouput(workdir, file_name) for key, file_name
                in expected_output.items()}


def retrieve_ouput(workdir: str, expected_file: str) -> str:
    """
    Search for `expected_file` files in the `workdir`.
    """
    path = workdir / expected_file
    if path.exists():
        return path.as_posix()
    else:
        return list(p.as_posix() for p in workdir.rglob(expected_file))


def wait_dependencies(fun: Callable):
    """
    Add an implicit dependency from `job` to the caller of this function
    """
    @wraps(fun)
    def wrapper(*args, **kwargs):
        dependencies = kwargs.get('dependencies')
        if dependencies is not None:
            for d in dependencies:
                assert isinstance(d, PromisedObject)
        return fun(*args)

    return wrapper


@schedule
def edit_options(options: Dict, names_xml_files: List,  path_optionfiles: str) -> Dict:
    """
    Edit a list of XML files `names_xml_files` that are located in the
    `path_optionfiles` using a set of user-defined `options`.
    """
    # Replace relative path with absolute ones in the calculators options

    sections_to_edit = {name: options[name] for name in names_xml_files}
    return edit_xml_options(sections_to_edit, path_optionfiles)


@schedule
def edit_path_options(path_xml: str, path_optionfiles: Path) -> str:
    """
    replace relative path by absolute ones at `path_xml`
    """
    return add_absolute_path_to_options(path_xml, path_optionfiles)


@schedule
def create_promise_command(
        string: str, *args) -> str:
    """Use a `string` as template command and fill in the options using
    possible promised `args`
    """
    return string.format(*args)


@schedule
def edit_jobs_file(path: str, jobs_to_run: List):
    """
    Run only the jobs listed in jobs_to_run
    """
    return {path: edit_xml_job_file(path, jobs_to_run)}


@schedule
def run_parallel_jobs(dict_jobs: dict, dict_input: dict) -> dict:
    """
    Run a set of jobs defined in `dict_jobs` using the options specified
    in dict_input.
    """
    state = dict_input['state']
    # Name of the job to run
    name = dict_input['name']

    cmd_options = dict_input['cmd_options']
    # Add command to run
    results = dict_jobs.copy()
    for key, job_info in dict_jobs.items():
        input_xml = job_info[name]
        cmd_parallel = "xtp_parallel -e {} -f {} -o {} ".format(name, state, input_xml)
        # Call subprocess
        output = run_command(
            cmd_parallel + cmd_options, job_info['workdir'],
            expected_output=dict_input['expected_output'])

        # Also store the path to the workdir
        results[key]['job_workdir'] = job_info['workdir']

        for k, val in output.items():
            results[key][k] = val

    # Pack the state in the ouput
    results.update({'state': dict_input['scratch_dir'] / 'state.sql'})

    return results


@schedule
def split_xqmultipole_calculations(input_dict: dict) -> dict:
    """
    Split the jobs specified in xqmultipole into independent jobs.
    """
    results = split_calculations(input_dict, 'xqmultipole_jobs')

    for idx, config in results.items():
        workdir = config['workdir']

        # Replace path to MP_FILES
        mp_files = input_dict['mp_files'].absolute().as_posix()

        # replace references inside xqmultipole.xml and job.xml
        options = {
            'xqmultipole':
            {'multipoles': input_dict['system'],
             'control': {'job_file': config['job'].name,
                         'emp_file': input_dict['mps_tab']}},
            'job': {'input': {
                'replace_regex': ('MP_FILES', mp_files)}}
        }
        edited_files = edit_xml_options(options, workdir)
        results[idx]['xqmultipole'] = edited_files['xqmultipole']
        results[idx]['job'] = edited_files['job']

    return {k: v for k, v in results.items()}


@schedule
def split_eqm_calculations(input_dict: dict) -> dict:
    """
    Split the jobs specified in eqm.jobs into independent jobs.
    """
    results = split_calculations(input_dict, 'eqm_jobs')
    # path_optionfiles = input_dict['path_optionfiles']

    for idx, config in results.items():
        workdir = config['workdir']
        sections = {'job_file': config['job'].as_posix()}

        path_file = workdir / 'eqm.xml'
        results[idx]['eqm'] = edit_xml_file(path_file.as_posix(), 'eqm', sections)
    return {k: v for k, v in results.items()}


@schedule
def split_iqm_calculations(input_dict: dict) -> dict:
    """
    Split the jobs specified in iqm.jobs into independent jobs.
    """
    results = split_calculations(input_dict, 'iqm_jobs')

    for idx, config in results.items():
        workdir = config['workdir']
        options = {
            'iqm': {
                'job_file': config['job'].name,
            }
        }
        # Make a symbolic link to the or_files
        os.symlink(input_dict['scratch_dir'] / "OR_FILES", workdir / "OR_FILES")

        edited_files = edit_xml_options(options, workdir)
        results[idx]['iqm'] = edited_files['iqm']

    return {k: v for k, v in results.items()}


@schedule
def split_qmmm_calculations(input_dict: dict) -> dict:
    """ """
    pass


def split_calculations(input_dict: dict, jobs_name: str) -> dict:
    """
    Split the jobs specified in a xml file in independent jobs that
    run independently.
    """
    tmp_dir = create_workdir(input_dict['scratch_dir'], jobs_name)

    # Copy job dependencies to a new folder
    results = defaultdict(dict)
    for job in read_available_jobs(input_dict[jobs_name]):
        # identifier
        idx = job.find('id').text

        name = "{}_{}".format('job', idx)
        workdir = create_workdir(tmp_dir, name)
        results[idx]['workdir'] = workdir

        # Job files
        results[idx]['job'] = create_xml_job_file(job, workdir)

        # Move input option file to workdir
        name = input_dict['name']
        shutil.copy(input_dict[name], workdir.as_posix())

    return results


def create_workdir(tmp_dir: Path, name: str):
    """
    Create temporal workdir
    """
    # create workdir for each job
    workdir = tmp_dir / name
    workdir.mkdir()

    return workdir


def create_xml_job_file(job: object, workdir: Path) -> Path:
    """
    Create an xml file containing a single job
    """
    job_file = workdir / 'job.xml'
    create_job_file(job, job_file.as_posix())

    return job_file


@schedule
def rename_map_file(path_file: Path, expression: str, new_val: str):
    """
    Replace the regex `expression` with `new_val` in the `file_path`.
    """
    regex = re.compile("MP_FILES")

    with open(path_file, 'r+') as f:
        xs = f.read()

    # overwrite the file
    with open(path_file, 'w') as f:
        f.write(re.sub(regex, new_val, xs))

    return path_file


@schedule
def move_results_to_workdir(jobs: dict, names: list,  workdir: Path) -> dict:
    """
    Move all the resulting or_files to the same central location
    """
    def collect_new_files(job, name):
        new_files = []
        for path in (Path(x) for x in job[name]):
            relative = path.relative_to(job['job_workdir'])
            folder_dest = workdir / relative.parent
            os.makedirs(folder_dest.as_posix(), exist_ok=True)
            dst = folder_dest / path.name
            shutil.move(path.as_posix(), dst.as_posix())
            new_files.append(dst / path.name)

        return new_files

    for k, job in jobs.items():
        for name in names:
            if isinstance(job, dict):
                jobs[k][name] = collect_new_files(job, name)

    return jobs
