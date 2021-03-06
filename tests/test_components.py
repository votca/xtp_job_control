from pathlib import Path
from xtp_job_control.input import validate_input
from xtp_job_control.results import Results
from xtp_job_control.runner import run
from xtp_job_control.xml_editor import read_available_jobs
from xtp_job_control.workflows.workflow_components import create_xml_job_file
from xtp_job_control.workflows.xtp_workflow import (
    initial_config, recursively_create_path, to_posix)
from noodles import gather_dict
import os
import pytest
import sys
import tempfile


def test_results():
    """
    Test the results object
    """
    d = {"foo": 1}
    rs = Results(d)

    output = run(gather_dict(**rs.state))

    assert output["foo"] == 1


def test_xml_job_creation():
    """
    Check that a job file is created correctly
    """
    tmp_path = tempfile.gettempdir()
    jobs = read_available_jobs("tests/test_files/eqm.jobs")

    file_path = create_xml_job_file(jobs[0], Path(tmp_path))

    assert file_path.exists()


def test_posix():
    file_path = "tests/test_files/votca/xml"
    p = Path(file_path)
    xs = list(p.rglob("*.xml"))
    d = to_posix({x.name: x for x in xs})

    assert all(isinstance(x, str) for x in to_posix(xs))
    assert all(os.path.exists(x) for x in d.values())