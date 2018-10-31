from .xml_editor import (edit_xml_job_file, edit_xml_options, read_available_jobs)
from collections import defaultdict
from noodles import (schedule, schedule_hint)
from subprocess import (PIPE, Popen)
from typing import (Dict, List)
import logging
import fnmatch
import os
import shutil

# Starting logger
logger = logging.getLogger(__name__)


class Results(dict):

    def __init__(self, init):
        self.state = init

    def __getitem__(self, val):
        return schedule(self.sate[val])



@schedule_hint()
def call_xtp_cmd(cmd: str, workdir: str, expected_output: List=None):
    """
    Run a bash `cmd` in the `cwd` folder and search for a list of `expected_output`
    files.
    """
    with Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True, cwd=workdir) as p:
        rs = p.communicate()

    logger.info("running command: {}".format(cmd))
    logger.info("command output: {}".format(rs[0]))
    logger.error("command error: {}".format(rs[1]))

    if expected_output is None:
        return None
    else:
        return {key: retrieve_ouput(workdir, file_name) for key, file_name
                in expected_output.items()}


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
def create_promise_command(template: str, dict_files: Dict, identifiers: List) -> str:
    """
    Use a `template` together with the previous result `dict_files`
    to create a new command line str, using different file `identifiers`.
    """
    for i in identifiers:
        return template.format(*[dict_files[f] for f in identifiers])


def retrieve_ouput(workdir: str, expected_file: str) -> str:
    """
    Search for `expected_file` files in the `workdir`.
    """
    if expected_file:
        rs = fnmatch.filter(os.listdir(workdir), expected_file)
        if len(rs) == 0:
            msg = "the command failed producing no output files"
            raise RuntimeError(msg)
        else:
            return os.path.join(workdir, rs[0])
    else:
        return None


@schedule_hint()
def edit_jobs_file(dict_results: Dict, file_name: str, jobs_to_run: List):
    """
    Run only the jobs listed in jobs_to_run
    """
    path = dict_results[file_name]
    return {file_name: edit_xml_job_file(path, jobs_to_run)}


@schedule_hint()
def split_xqmultipole_calculations(config: dict) -> dict:
    """
    SPlit the jobs specified in xqmultipole in independent runs then
    gather the results
    """
    available_jobs = read_available_jobs(config['xqmultipole_jobs'])

    # Make a different folder for each job
    scratch_dir = config['scratch_dir']
    tmp_dir = os.path.join(scratch_dir, 'xqmultipole_jobs')
    os.mkdir(tmp_dir)

    # Copy job dependencies to a new folder
    results = defaultdict(dict)
    for job in available_jobs:
        idx = "job_" + job.find('id').text
        name = "xqmultipole_{}".format(idx)
        workdir = os.path.join(tmp_dir, name)
        os.mkdir(workdir)
        results[idx]['workdir'] = workdir
        for f in ['state', 'xqmultipole_jobs', 'mps_tab', 'xqmultipole']:
            path_file = os.path.join(workdir, f)
            shutil.copy(config[f], path_file)
            results[idx][f] = path_file

    return {'xqmultipole_jobs_dirs': {k: v for k, v in results.items()}}