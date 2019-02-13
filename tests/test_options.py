from xtp_job_control.results import Options


def test_options():
    """
    Test that the option object is constructed properly
    """
    d = {'a': 1, 'b': {'c': 2}}

    opts = Options(d)

    d['w'] = 42
    opts.w = 42

    assert all((d['a'] == opts.a, d['b']['c'] == opts.b['c'], d['w'] == opts.w))
