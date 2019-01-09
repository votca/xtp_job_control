from xtp_job_control.runner import run
from xtp_job_control.worflow_components import (call_xtp_cmd, create_promise_command)


def test_runner(tmp_path):
    """
    Test the workflow runner
    """
    job1 = call_xtp_cmd("touch test.out", workdir=tmp_path, expected_output={"file": "test.out"})
    cmd1 = create_promise_command(
        "head /dev/urandom | tr -dc A-Za-z0-9 | head -c 50 > {}",
        job1["file"])
    job2 = call_xtp_cmd(cmd1, workdir=tmp_path, expected_output={"results": "test.out"})

    rs = run(job2)
    print(rs)

    with open(rs["results"], 'r') as f:
        xs = f.read()

    assert len(xs) == 50
