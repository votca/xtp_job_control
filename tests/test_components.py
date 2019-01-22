from xtp_job_control.runner import run
from xtp_job_control.worflow_components import (Results, create_workdir, create_xml_job_file)
from xtp_job_control.xml_editor import read_available_jobs
from noodles import gather_dict


def test_results():
    """
    Test the results object
    """
    d = {"foo": 1}
    rs = Results(d)

    output = run(gather_dict(**rs.state))

    assert output["foo"] == 1


def test_xml_job_creation(tmp_path):
    """
    Check that a job file is created correctly
    """
    workdir = create_workdir(tmp_path, "random")

    jobs = read_available_jobs("tests/test_files/eqm.jobs")

    file_path = create_xml_job_file(jobs[0], workdir)

    assert file_path.exists()
