import re
import xml.etree.ElementTree as ET
from os.path import join
from typing import (Any, Dict, List)


def edit_xml_options(options: Dict, path: str) -> Dict:
    """
    Go through the `options` file: sections dictionary
    and  edit the corresponding XML file by replacing
    `sections` in the XML file.
    """
    def call_xml_editor(xml_file, sections):
        path_file = path / '{}.xml'.format(xml_file)
        return edit_xml_file(path_file, xml_file, sections)

    return {xml_file: call_xml_editor(xml_file, section)
            for xml_file, section in options.items()}


def edit_xml_file(path: str, xml_file: str, sections: Dict) -> dict:
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


def read_available_jobs(path_file: str, state: str="AVAILABLE") -> List:
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
