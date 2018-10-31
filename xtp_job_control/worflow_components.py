from .xml_editor import (edit_xml_job_file, edit_xml_options, read_available_jobs)
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
        return Results(self.state.copy())


@schedule_hint()
def call_xtp_cmd(cmd: str, workdir: str, expected_output: List=None):
    """
    Run a bash `cmd` in the `cwd` folder and search for a list of `expected_output`
    files.
    """
    with Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True, cwd=workdir) as p:
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
    if expected_file:
        path = workdir / Path(expected_file)
        if not path.exists():
            msg = "the file: {} does not exists!".format(path.as_posix())
            raise RuntimeError(msg)
        else:
            return path
    else:
        return None


@schedule_hint()
def edit_options(options: Dict, names_xml_files: List,  path_optionfiles: str) -> Dict:
    """
    Edit a list of XML files `names_xml_files` that are located in the
    `path_optionfiles` using a set of user-defined `options`.
    """
    sections_to_edit = {name: options[name] for name in names_xml_files}
    return edit_xml_options(sections_to_edit, path_optionfiles)


@schedule_hint()
def merge_promised_dict(*list_dictionaries: List) -> Dict:
    """
    Merge a list of dictionaries into a single dictionary
    """
    return {k: v for d in list_dictionaries for k, v in d.items()}


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
def split_xqmultipole_calculations(config: dict) -> dict:
    """
    SPlit the jobs specified in xqmultipole in independent runs then
    gather the results
    """
    available_jobs = read_available_jobs(config['xqmultipole_jobs'])

    # Make a different folder for each job
    scratch_dir = config['scratch_dir']
    tmp_dir = scratch_dir / Path('xqmultipole_jobs')
    tmp_dir.mkdir()

    # Copy job dependencies to a new folder
    results = defaultdict(dict)
    for job in available_jobs:
        idx = "job_" + job.find('id').text
        name = "xqmultipole_{}".format(idx)
        workdir = tmp_dir / name
        workdir.mkdir()
        results[idx]['workdir'] = workdir
        for f in ['state', 'xqmultipole_jobs', 'mps_tab', 'xqmultipole']:
            path_file = workdir / f
            shutil.copy(config[f], path_file)
            results[idx][f] = path_file

    return {'xqmultipole_jobs_dirs': {k: v for k, v in results.items()}}
