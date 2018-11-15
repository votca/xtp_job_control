from .xml_editor import (
    create_job_file, edit_xml_job_file, edit_xml_options, read_available_jobs)
from collections import defaultdict
from noodles import (schedule, schedule_hint, has_scheduled_methods)
from noodles.interface import PromisedObject
from pathlib import Path
from subprocess import (PIPE, Popen)
from typing import (Dict, List)
import logging
import re
import shutil

# Starting logger
logger = logging.getLogger(__name__)


@has_scheduled_methods
class Results(dict):
    """
    Encapsulate the results of a workflow by storing the
    results or promised objects in a dictionary.
    """
    def __init__(self, init):
        self.state = init

    def __getitem__(self, val):
        if isinstance(val, PromisedObject):
            return schedule(self.state[val])
        else:
            return self.state[val]

    def __setitem__(self, key, val):
        self.state[key] = val

    def __deepcopy__(self, _):
        return Results(self.state.copy())


@schedule_hint()
def call_xtp_cmd(cmd: str, workdir: str, expected_output: dict=None):
    """
    Run a bash `cmd` in the `cwd` folder and search for a list of `expected_output`
    files.
    """
    if not workdir.exists():
        workdir.mkdir()
    return run_command(cmd, workdir, expected_output)


def run_command(cmd: str, workdir: str, expected_output: dict=None):
    """
    Run a bash command using subprocess
    """
    with Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True, cwd=workdir.as_posix()) as p:
        rs = p.communicate()

    logger.info("RUNNING COMMAND: {}".format(cmd))
    logger.info("COMMAND OUTPUT: {}".format(rs[0]))
    logger.error("COMMAND ERROR: {}".format(rs[1]))

    if expected_output is None:
        return None
    else:
        return {key: retrieve_ouput(workdir, file_name) for key, file_name
                in expected_output.items()}


def retrieve_ouput(workdir: str, expected_file: str) -> str:
    """
    Search for `expected_file` files in the `workdir`.
    """
    path = workdir / Path(expected_file)
    if path.exists():
        return path
    else:
        return list(workdir.rglob(expected_file))


@schedule_hint()
def edit_options(options: Dict, names_xml_files: List,  path_optionfiles: str) -> Dict:
    """
    Edit a list of XML files `names_xml_files` that are located in the
    `path_optionfiles` using a set of user-defined `options`.
    """
    sections_to_edit = {name: options[name] for name in names_xml_files}
    return edit_xml_options(sections_to_edit, path_optionfiles)


@schedule_hint()
def create_promise_command(string: str, *args) -> str:
    """Use a `string` as template command and fill in the options using
    possible promised `args`
    """
    return string.format(*args)


@schedule_hint()
def edit_jobs_file(path: Path, jobs_to_run: List):
    """
    Run only the jobs listed in jobs_to_run
    """
    return {path.stem: edit_xml_job_file(path, jobs_to_run)}


@schedule_hint()
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
        input_xml = job_info[name].as_posix()
        cmd_parallel = "xtp_parallel -e {} -f {} -o {} ".format(name, state, input_xml)
        # Call subprocess
        output = run_command(
            cmd_parallel + cmd_options, job_info['workdir'],
            expected_output=dict_input['expected_output'])
        for k, val in output.items():
            results[key][k] = val

    return results


@schedule_hint()
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
            {'multipoles': input_dict['system'].as_posix(),
             'control': {'job_file': config['job'].name,
                         'emp_file': input_dict['mps_tab'].as_posix()}},
            'job': {'input': {
                'replace_regex': ('MP_FILES', mp_files)}}
        }
        edited_files = edit_xml_options(options, workdir)
        results[idx]['xqmultipole'] = edited_files['xqmultipole']
        results[idx]['job'] = edited_files['job']

    return {k: v for k, v in results.items()}


@schedule_hint()
def split_eqm_calculations(input_dict: dict) -> dict:
    """
    Split the jobs specified in eqm.jobs into independent jobs.
    """
    results = split_calculations(input_dict, 'eqm_jobs')
    path_optionfiles = input_dict['path_optionfiles'].as_posix()

    for idx, config in results.items():
        workdir = config['workdir']
        options = {
            'eqm': {
                'job_file': config['job'].name,
                '': {'replace_regex_recursively':
                     ('OPTIONFILES', path_optionfiles)}
            }
        }
        edited_files = edit_xml_options(options, workdir)
        results[idx]['eqm'] = edited_files['eqm']

    return {k: v for k, v in results.items()}


@schedule_hint()
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
        edited_files = edit_xml_options(options, workdir)
        results[idx]['iqm'] = edited_files['iqm']

    return {k: v for k, v in results.items()}


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
    create_job_file(job, job_file)

    return job_file


@schedule_hint()
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


def as_posix(path: Path) -> str:
    """
    Call the `as_posix` method from a `Path` object using
    function notation
    """
    return getattr(path, 'as_posix')()
