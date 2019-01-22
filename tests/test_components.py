from xtp_job_control.input import validate_input
from xtp_job_control.runner import run
from xtp_job_control.worflow_components import (Results, create_xml_job_file)
from xtp_job_control.xml_editor import read_available_jobs
from xtp_job_control.xtp_workflow import (initial_config, recursively_create_path)
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

    jobs = read_available_jobs("tests/test_files/eqm.jobs")

    file_path = create_xml_job_file(jobs[0], tmp_path)

    assert file_path.exists()


def test_initial_config(tmp_path):
    """
    Check that the files are copy to a temporal workdir
    """
    test_file = "tests/Methane/input_methane.yml"
    input_dict = recursively_create_path(validate_input(test_file))
    input_dict['workdir'] = tmp_path

    # Initialize data in workdir
    new_options = initial_config(input_dict)
    optionfiles = new_options['path_optionfiles']
    elements = list(optionfiles.glob("*.xml"))

    assert optionfiles.exists() and (len(elements) != 0)
