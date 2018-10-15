import xml.etree.ElementTree as ET
from os.path import join
from typing import Dict


def edit_options(options: Dict, path: str) -> None:
    """
    Go through the `options` file: sections dictionary
    and  edit the corresponding XML file by replacing
    `sections` in the XML file.
    """
    for xml_file, sections in options.items():
        path_file = join(path, '{}.xml'.format(xml_file))
        edit_xml_file(path_file, xml_file, sections)


def edit_xml_file(path_file: str, xml_file: str, sections: Dict) -> None:
    """
    Parse the `path_file` XML file and replace the nodes
    given in `sections` in the XML tree. Finally write
    the XML tree to the same file
    """
    # Parse XML Tree
    tree = ET.parse(path_file)
    root = tree.getroot()

    print("path_file: ", path_file)
    for key, val in sections.items():
        xpath = join(xml_file, key)
        node = root.find(xpath)
        node.text = str(val)

    tree.write(path_file)
