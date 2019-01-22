from xtp_job_control.runner import run
from xtp_job_control.worflow_components import Results
from noodles import gather_dict


def test_results():
    """
    Test the results object
    """
    d = {"foo": 1}
    rs = Results(d)

    output = run(gather_dict(**rs.state))

    assert output["foo"] == 1
