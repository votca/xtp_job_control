from os.path import join
from xtp_job_control.input import validate_input
from typing import Dict
import yaml


def test_input_validation(tmp_path):
    """
    Test the input validation
    """
    test_file = tmp_path / "test.yml"
    root = "tests/Methane"

    d = {
        "workflow": "simulation",
        "path_votcashare": "tests/test_files",
        "system": join(root, "system.xml"),
        "topology": "tests/Methane/MD_FILES/topol.tpr",
        "trajectory":  "tests/Methane/MD_FILES/conf.gro",
        "mp_files": "tests/Methane/MP_FILES",
        "qc_files": "tests/Methane/QC_FILES"
    }

    # check valid input
    dump_yaml(test_file, d)
    validate_input(test_file.as_posix())

    # check invalid input
    try:
        d['system'] = "non-existing/file.xml"
        dump_yaml(test_file, d)
        validate_input(test_file)
    except RuntimeError:
        # expected error
        pass


def dump_yaml(test_file: str, d: Dict) -> None:
    with open(test_file.as_posix(), 'w')as f:
        f.write(yaml.dump(d))
