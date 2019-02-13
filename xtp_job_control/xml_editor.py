from os.path import join
from pathlib import Path
from typing import (Any, Dict, List)
import re
import xml.etree.ElementTree as ET


def edit_xml_options(sections: dict, path_optionfiles: Path) -> Dict:
    """
    Go through the `options` file: sections dictionary
    and  edit the corresponding XML file by replacing
    `sections` in the XML file.
    """
    def call_xml_editor(xml_file, sections):
        path_file = path_optionfiles / '{}.xml'.format(xml_file)
        edited_file = edit_xml_file(path_file.as_posix(), xml_file, sections)
        return add_absolute_path_to_options(edited_file, path_optionfiles)

    return {xml_file: call_xml_editor(xml_file, section)
            for xml_file, section in sections.items()}


def edit_xml_file(path: str, xml_file: str, sections: Dict) -> str:
    """
    Parse the `path` XML file and replace the nodes
    given in `sections` in the XML tree. Finally write
    the XML tree to the same file
    """
    # Parse XML Tree
    tree = ET.parse(path)
    root = tree.getroot()
    # Iterate over the sections to change
    for key, val in sections.items():
        try:
            update_node(join(xml_file, key), root, val)
        except AttributeError:
            update_node(key, root, val)

    # write to the path_file the updated xml
    tree.write(path, short_empty_elements=False)

    return path


def update_node(path: str, root: object, val: Any):
    """Update node recursively"""
    node = root.find(path)
    if not isinstance(val, dict):
        node.text = str(val)
    else:
        for key, x in val.items():
            # Remove or update Leave
            if key.lower() == 'delete_entry':
                leave = root.find(join(path, x))
                node.remove(leave)
            elif key.lower() == 'replace_regex':
                regex, new_val = x
                node.text = re.sub(regex, new_val, node.text)
            elif key.lower() == 'replace_regex_recursively':
                regex, new_val = x
                regex = re.compile(regex)
                replace_regex_recursively(root, regex, new_val)
            else:
                update_node(join(path, key), root, x)


def replace_regex_recursively(tree: object, regex: object, path_file: str) -> None:
    """
    replace a regex in all the xml tree recursively.
    """
    for elem in tree.iter():
        if elem.text is not None:
            elem.text = re.sub(regex, path_file, elem.text)


def edit_xml_job_file(path_file: str, jobs_to_run: List):
    """
    Read XML Containing a set of job and change status
    """
    # Parse XML Tree
    tree = ET.parse(path_file)
    root = tree.getroot()

    for job in root.findall('job'):
        ids = job.find('id')
        i = int(ids.text)
        status = job.find('status')
        if jobs_to_run is None:
            status.text = "AVAILABLE"
        elif i not in jobs_to_run:
            status.text = "COMPLETE"
        else:
            status.text = "AVAILABLE"

    tree.write(path_file)

    return path_file


def read_available_jobs(path_file: str, state: str = "AVAILABLE") -> List:
    """
    Search for jobs with `state`
    """
    tree = ET.parse(path_file)
    root = tree.getroot()

    rs = []
    for j in root.findall('job'):
        status = j.find('status')
        if status.text == state:
            rs.append(j)
    return rs


def create_job_file(job: object, job_file: str):
    """
    Create a xml file containing the information necessary to run a job.
    """
    root = ET.Element("jobs")
    root.text = '\n\t'
    root.insert(0, job)

    tree = ET.ElementTree(root)
    tree.write(job_file)


def add_absolute_path_to_options(path_xml: str, path_optionfiles: Path) -> None:
    """
    Replace the relative paths to the optionfiles inside a `path_xml` file with the
    correspoding absolute values.
    """
    names = [x.name for x in path_optionfiles.glob("*xml")]
    tree = ET.parse(path_xml)
    root = tree.getroot()

    for section in root.iter():
        for elem in section.iter():
            val = elem.text
            if (val is not None) and (".xml" in val) and (val in names):
                path = path_optionfiles / Path(elem.text).name
                elem.text = path.as_posix()

    tree.write(path_xml, short_empty_elements=False)

    return path_xml
