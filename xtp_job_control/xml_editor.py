import xml.etree.ElementTree as ET
from os.path import join
from typing import (Dict, List)


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


def edit_xml_file(path_file: str, xml_file: str, sections: Dict) -> dict:
    """
    Parse the `path_file` XML file and replace the nodes
    given in `sections` in the XML tree. Finally write
    the XML tree to the same file
    """
    def update_node(path, val):
        """Update node recursively"""
        if not isinstance(val, dict):
            node = root.find(path)
            node.text = str(val)
        else:
            for key, x in val.items():
                # Remove or update Leave
                if key.lower() == 'delete_entry':
                    node = root.find(path)
                    leave = root.find(join(path, x))
                    node.remove(leave)
                else:
                    update_node(join(path, key), x)

    # Parse XML Tree
    tree = ET.parse(path_file)
    root = tree.getroot()
    # Iterate over the sections to change
    for key, val in sections.items():
        update_node(join(xml_file, key), val)

    tree.write(path_file)

    return path_file


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
