from .xml_editor import (
    create_job_file, edit_xml_job_file, edit_xml_options, read_available_jobs)
from collections import defaultdict
from noodles import (schedule, schedule_hint, has_scheduled_methods)
from noodles.interface import PromisedObject
from pathlib import Path
from subprocess import (PIPE, Popen)
from typing import (Dict, List)
import logging
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
        print("calling deep")
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
def split_eqm_calculations(input_dict: dict) -> dict:
    """
    Split the jobs specified in xqmultipole in independent jobs then
    gather the results
    """
    pass



@schedule_hint()
def split_xqmultipole_calculations(input_dict: dict) -> dict:
    """
    Split the jobs specified in xqmultipole in independent jobs then
    gather the results
    """
    available_jobs = read_available_jobs(input_dict['xqmultipole_jobs'])

    # Make a different folder for each job
    tmp_dir = input_dict['scratch_dir'] / 'xqmultipole_jobs'
    tmp_dir.mkdir()

    # Copy job dependencies to a new folder
    results = defaultdict(dict)
    for job in available_jobs:
        idx = job.find('id').text
        # create workdir for each job
        workdir = tmp_dir / "xqmultipole_job_{}".format(idx)
        workdir.mkdir()
        results[idx]['workdir'] = workdir

        # Job files
        job_idx = "job_{}".format(idx)
        job_file = workdir / (job_idx + '.xml')
        create_job_file(job, job_file)
        results[idx][job_idx] = job_file

        # MP files
        shutil.copytree(input_dict['mp_files'], workdir / 'MP_FILES')

        # replace references inside xqmultipole.xml
        xqmultipole = input_dict['xqmultipole']
        shutil.copy(xqmultipole, workdir.as_posix())
        options = {'xqmultipole':
                   {'multipoles': input_dict['system'].as_posix(),
                    'control': {'job_file': job_file.name,
                                'emp_file': input_dict['mps_tab'].as_posix()}}}
        results[idx]['xqmultipole'] = edit_xml_options(options, workdir)['xqmultipole']

    return {k: v for k, v in results.items()}





@schedule_hint()
def run_parallel_jobs(cmd: str, dict_jobs: dict, dict_input: dict) -> dict:
    """
    Run a set of jobs defined in `dict_jobs`.
    """
    state = dict_input['state']
    results = dict_jobs.copy()
    for key, job_info in dict_jobs.items():
        cmd_parallel = cmd.format(state, job_info['xqmultipole'].as_posix())

        # Call subprocess
        output = run_command(cmd_parallel, job_info['workdir'], expected_output={
            'tab': 'job_{}.tab'.format(key)})
        results['tab'] = output['tab']

    return results
