from noodles import schedule
from subprocess import (PIPE, Popen)
from typing import (Dict, List)
import logging
import fnmatch
import os

# Starting logger
logger = logging.getLogger(__name__)


@schedule
def call_xtp_cmd(cmd: str, workdir: str, expected_output: List=None):
    """
    Run a bash `cmd` in the `cwd` folder and search for a list of `expected_output`
    files.
    """
    with Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True, cwd=workdir) as p:
        rs = p.communicate()

    logger.info("running command: {}".format(cmd))

    if expected_output is None:
        return None
    else:
        logger.info("command output: {}".format(rs[0]))
        logger.error("command error: {}".format(rs[1]))
        return {key: retrieve_ouput(workdir, file_name) for key, file_name
                in expected_output.items()}


@schedule
def create_promise_command(template: str, dict_files: Dict, identifiers: List) -> str:
    """
    Use a `template` together with the previous result `dict_files`
    to create a new command line str, using different file `identifiers`.
    """
    return template.format(*[dict_files[f] for f in identifiers])


def retrieve_ouput(workdir: str, expected_file: str) -> str:
    """
    Search for `expected_file` files in the `workdir`.
    """
    rs = fnmatch.filter(os.listdir(workdir), expected_file)
    if len(rs) == 0:
        msg = "the command failed producing no output files"
        raise RuntimeError(msg)
    else:
        return rs[0]
