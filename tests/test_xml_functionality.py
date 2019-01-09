from xtp_job_control.xml_editor import (
    edit_xml_job_file, edit_xml_options, read_available_jobs)
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET


def copy_to_tmp(origin: Path, dest: Path) -> Path:
    """
    Copy `origin` to temp `dest`
    """
    shutil.copy(origin.as_posix(), dest.as_posix())

    return dest / origin.name


def read_xml_val(path_file: Path, prop_path: str) -> str:
    """
    read the `prop_path` from xml `path_file`
    """
    tree = ET.parse(path_file.as_posix())
    root = tree.getroot()
    node = root.find(prop_path)

    return node.text


def test_xml_job_file(tmp_path):
    """ Test that the XML job file is tested correctly"""

    file_path = copy_to_tmp(Path("tests/test_files/eqm.jobs"), tmp_path)
    rs = edit_xml_job_file(file_path, [1, 2, 3])

    assert len(read_available_jobs(rs)) == 3


def test_xml_options(tmp_path):
    """
    Test that xml options are edited properly
    """
    sections_to_edit = {
        "neighborlist": {
            "constant": 0.6}
    }
    path_file = copy_to_tmp(Path("tests/test_files/neighborlist.xml"), tmp_path)
    edit_xml_options(sections_to_edit, tmp_path)

    assert read_xml_val(path_file, "neighborlist/constant") == "0.6"
