import xml.etree.ElementTree as ET
from os.path import join
from typing import Dict


def edit_xml_options(options: Dict, path: str) -> Dict:
    """
    Go through the `options` file: sections dictionary
    and  edit the corresponding XML file by replacing
    `sections` in the XML file.
    """
    def call_xml_editor(xml_file, sections):
        path_file = join(path, '{}.xml'.format(xml_file))
        return edit_xml_file(path_file, xml_file, sections)

    return {xml_file: call_xml_editor(xml_file, section)
            for xml_file, section in options.items()}


def edit_xml_file(path_file: str, xml_file: str, sections: Dict) -> dict:
    """
    Parse the `path_file` XML file and replace the nodes
    given in `sections` in the XML tree. Finally write
    the XML tree to the same file
    """
    # Parse XML Tree
    tree = ET.parse(path_file)
    root = tree.getroot()

    # Iterate over the sections to change
    for key, val in sections.items():
        xpath = join(xml_file, key)
        node = root.find(xpath)
        node.text = str(val)

    tree.write(path_file)

    return path_file
