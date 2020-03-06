"""Test the input validation."""

from xtp_job_control.input import validate_input
from typing import Dict
import yaml


def test_input_validation(tmp_path):
    """Test the input validation."""
    test_file = (tmp_path / "test.yml").as_posix()

    d = {
        "workflow": "dftgwbse",
        "path_votcashare": "tests/test_files",
        "molecule": "tests/DFT_GWBSE/dftgwbse_CH4/methane.xyz",
        "functional": "XC_HYB_GGA_XC_PBEH"
    }

    # check valid input
    dump_yaml(test_file, d)
    validate_input(test_file)

    # check invalid input
    try:
        d['system'] = "non-existing/file.xml"
        dump_yaml(test_file, d)
        validate_input(test_file)
    except RuntimeError:
        # expected error
        pass


def dump_yaml(test_file: str, d: Dict) -> None:
    with open(test_file, 'w')as f:
        f.write(yaml.dump(d))
